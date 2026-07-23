"""Promotion Registry implementation over SQLite control database (PROMO-001)."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Final

from cryptofactors.catalog.runner import apply_migrations
from cryptofactors.promotion.errors import PromotionError
from cryptofactors.promotion.models import (
    PromotionEvent,
    PromotionIdentityPayload,
    PromotionState,
    PromotionTarget,
)
from cryptofactors.promotion.state_machine import validate_transition_and_gates

_US_PER_SECOND: Final[int] = 1_000_000


def _dt_to_iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.isoformat()


def _parse_iso(iso_str: str) -> datetime:
    dt = datetime.fromisoformat(iso_str)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class PromotionRegistry:
    """SQLite control-plane repository for immutable promotion events and state transitions."""

    def __init__(
        self,
        control_database: Path,
        *,
        migrations_dir: Path | None = None,
    ) -> None:
        self.control_database: Path = Path(control_database)
        if migrations_dir is not None:
            apply_migrations(self.control_database, migrations_dir)
        else:
            default_mig = Path("sql/migrations")
            if default_mig.exists():
                apply_migrations(self.control_database, default_mig)

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.control_database))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def register_candidate(
        self,
        payload: PromotionIdentityPayload,
        reason: str = "Initial artifact candidate registration",
    ) -> PromotionEvent:
        """Register a new model artifact in RESEARCH_CANDIDATE state."""
        current = self.get_current_state(payload.model_artifact_id)
        if current is not None:
            raise PromotionError(
                f"Artifact '{payload.model_artifact_id}' already registered with state '{current.value}'",
                context={"model_artifact_id": payload.model_artifact_id, "current_state": current.value},
            )

        return self._append_event(
            payload=payload,
            target_state=PromotionState.RESEARCH_CANDIDATE,
            current_state=None,
            reason=reason,
        )

    def transition_state(
        self,
        payload: PromotionIdentityPayload,
        target_state: PromotionState,
        reason: str,
    ) -> PromotionEvent:
        """Record an append-only promotion state transition after validating gates."""
        current = self.get_current_state(payload.model_artifact_id)
        if current is None:
            raise PromotionError(
                f"Artifact '{payload.model_artifact_id}' not found in registry. Register as candidate first.",
                context={"model_artifact_id": payload.model_artifact_id},
            )

        return self._append_event(
            payload=payload,
            target_state=target_state,
            current_state=current,
            reason=reason,
        )

    def get_current_state(self, model_artifact_id: str) -> PromotionState | None:
        """Return current promotion state for model_artifact_id (latest event)."""
        conn = self._get_connection()
        try:
            row = conn.execute(
                """
                SELECT promotion_state FROM model_promotion_record
                WHERE model_artifact_id = ?
                ORDER BY event_at DESC, rowid DESC
                LIMIT 1
                """,
                (model_artifact_id,),
            ).fetchone()
            if row is None:
                return None
            return PromotionState(row["promotion_state"])
        finally:
            conn.close()

    def get_latest_event(self, model_artifact_id: str) -> PromotionEvent | None:
        """Return latest PromotionEvent for model_artifact_id."""
        conn = self._get_connection()
        try:
            row = conn.execute(
                """
                SELECT * FROM model_promotion_record
                WHERE model_artifact_id = ?
                ORDER BY event_at DESC, rowid DESC
                LIMIT 1
                """,
                (model_artifact_id,),
            ).fetchone()
            if row is None:
                return None
            return self._row_to_event(row)
        finally:
            conn.close()

    def list_history(self, model_artifact_id: str) -> list[PromotionEvent]:
        """Return append-only event history for model_artifact_id ordered by event_at."""
        conn = self._get_connection()
        try:
            rows = conn.execute(
                """
                SELECT * FROM model_promotion_record
                WHERE model_artifact_id = ?
                ORDER BY event_at ASC, rowid ASC
                """,
                (model_artifact_id,),
            ).fetchall()
            return [self._row_to_event(r) for r in rows]
        finally:
            conn.close()

    def get_active_promoted_artifact(
        self,
        model_artifact_id: str,
        stage: PromotionTarget,
    ) -> PromotionEvent:
        """Serving discovery accessor: return active event if approved for target stage, or fail closed."""
        current = self.get_current_state(model_artifact_id)
        if current is None:
            raise PromotionError(
                f"Artifact '{model_artifact_id}' is not registered in Promotion Registry",
                context={"model_artifact_id": model_artifact_id, "stage": stage.value},
            )

        if stage == PromotionTarget.PAPER and current != PromotionState.PAPER_APPROVED:
            raise PromotionError(
                f"Artifact '{model_artifact_id}' is not PAPER_APPROVED (current: {current.value})",
                context={
                    "model_artifact_id": model_artifact_id,
                    "current_state": current.value,
                    "required_stage": stage.value,
                },
            )

        if stage == PromotionTarget.LIVE and current != PromotionState.LIVE_APPROVED:
            raise PromotionError(
                f"Artifact '{model_artifact_id}' is not LIVE_APPROVED (current: {current.value})",
                context={
                    "model_artifact_id": model_artifact_id,
                    "current_state": current.value,
                    "required_stage": stage.value,
                },
            )

        latest = self.get_latest_event(model_artifact_id)
        if latest is None:
            raise PromotionError(
                f"Artifact '{model_artifact_id}' missing event record",
                context={"model_artifact_id": model_artifact_id},
            )
        return latest

    def _append_event(
        self,
        payload: PromotionIdentityPayload,
        target_state: PromotionState,
        current_state: PromotionState | None,
        reason: str,
    ) -> PromotionEvent:
        validate_transition_and_gates(current_state, target_state, payload)

        event_at = datetime.now(timezone.utc)
        promotion_event_id = f"pme_{uuid.uuid4().hex[:16]}"

        conn = self._get_connection()
        try:
            conn.execute(
                """
                INSERT INTO model_promotion_record (
                    promotion_event_id,
                    model_artifact_id,
                    promotion_state,
                    target_stage,
                    experiment_fingerprint,
                    dataset_ids_json,
                    universe_ids_json,
                    code_commit,
                    config_version,
                    feature_version,
                    representation_version,
                    portfolio_version,
                    cost_model_version,
                    risk_policy_version,
                    effective_time,
                    approving_authority,
                    evidence_reference,
                    paper_observation_reference,
                    kill_switch_procedure,
                    event_at,
                    reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    promotion_event_id,
                    payload.model_artifact_id,
                    target_state.value,
                    payload.target_stage.value,
                    payload.experiment_fingerprint,
                    json.dumps(list(payload.dataset_ids)),
                    json.dumps(list(payload.universe_ids)),
                    payload.code_commit,
                    payload.config_version,
                    payload.feature_version,
                    payload.representation_version,
                    payload.portfolio_version,
                    payload.cost_model_version,
                    payload.risk_policy_version,
                    _dt_to_iso(payload.effective_time),
                    payload.approving_authority,
                    payload.evidence_reference,
                    payload.paper_observation_reference,
                    payload.kill_switch_procedure,
                    _dt_to_iso(event_at),
                    reason,
                ),
            )
            conn.commit()
        finally:
            conn.close()

        return PromotionEvent(
            promotion_event_id=promotion_event_id,
            payload=payload,
            promotion_state=target_state,
            event_at=event_at,
            reason=reason,
        )

    def _row_to_event(self, row: sqlite3.Row) -> PromotionEvent:
        payload = PromotionIdentityPayload(
            model_artifact_id=row["model_artifact_id"],
            experiment_fingerprint=row["experiment_fingerprint"],
            dataset_ids=tuple(json.loads(row["dataset_ids_json"])),
            universe_ids=tuple(json.loads(row["universe_ids_json"])),
            code_commit=row["code_commit"],
            config_version=row["config_version"],
            feature_version=row["feature_version"],
            representation_version=row["representation_version"],
            portfolio_version=row["portfolio_version"],
            cost_model_version=row["cost_model_version"],
            risk_policy_version=row["risk_policy_version"],
            target_stage=PromotionTarget(row["target_stage"]),
            effective_time=_parse_iso(row["effective_time"]),
            approving_authority=row["approving_authority"],
            evidence_reference=row["evidence_reference"],
            paper_observation_reference=row["paper_observation_reference"],
            kill_switch_procedure=row["kill_switch_procedure"],
        )
        return PromotionEvent(
            promotion_event_id=row["promotion_event_id"],
            payload=payload,
            promotion_state=PromotionState(row["promotion_state"]),
            event_at=_parse_iso(row["event_at"]),
            reason=row["reason"],
        )
