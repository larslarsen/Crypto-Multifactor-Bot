from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from cryptofactors.evidence.canonical import content_sha256
from cryptofactors.evidence.models import EvidenceItem, HypothesisDecision, HypothesisVersion


class EvidenceRegistryError(RuntimeError):
    """Raised when an Evidence Registry invariant is violated."""


class EvidenceRepository:
    """Small SQLite repository with append-only evidence and decision operations."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def register_hypothesis(self, hypothesis: HypothesisVersion, *, actor: str, created_at: str) -> None:
        payload = hypothesis.model_dump(mode="json")
        digest = content_sha256(payload)
        with self._connect() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO hypothesis(hypothesis_id, slug, created_at, created_by) VALUES (?, ?, ?, ?)",
                (hypothesis.hypothesis_id, hypothesis.slug, created_at, actor),
            )
            existing = connection.execute(
                "SELECT content_sha256 FROM hypothesis_version WHERE hypothesis_id = ? AND version = ?",
                (hypothesis.hypothesis_id, hypothesis.version),
            ).fetchone()
            if existing is not None:
                if existing["content_sha256"] != digest:
                    raise EvidenceRegistryError("hypothesis version already exists with different content")
                return
            connection.execute(
                """
                INSERT INTO hypothesis_version(
                    hypothesis_id, version, title, statement, mechanism, expected_sign, phase,
                    primary_metric, advancement_rule, rejection_rule, details_json, content_sha256,
                    preregistered_at, created_at, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    hypothesis.hypothesis_id, hypothesis.version, hypothesis.title,
                    hypothesis.statement, hypothesis.mechanism, hypothesis.expected_sign,
                    hypothesis.phase, hypothesis.primary_metric, hypothesis.advancement_rule,
                    hypothesis.rejection_rule, json.dumps(payload, sort_keys=True), digest,
                    hypothesis.preregistered_at.isoformat() if hypothesis.preregistered_at else None,
                    created_at, actor,
                ),
            )

    def add_evidence(self, evidence: EvidenceItem) -> None:
        payload = evidence.model_dump(mode="json")
        with self._connect() as connection:
            existing = connection.execute(
                "SELECT content_sha256 FROM evidence_item WHERE evidence_id = ?",
                (evidence.evidence_id,),
            ).fetchone()
            if existing is not None:
                if existing["content_sha256"] != evidence.content_sha256:
                    raise EvidenceRegistryError("evidence ID already exists with different content")
                return
            connection.execute(
                """
                INSERT INTO evidence_item(
                    evidence_id, kind, title, summary, source_ref, artifact_uri, observed_at,
                    registered_at, registered_by, content_sha256, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    evidence.evidence_id, evidence.kind.value, evidence.title, evidence.summary,
                    evidence.source_ref, evidence.artifact_uri,
                    evidence.observed_at.isoformat() if evidence.observed_at else None,
                    evidence.registered_at.isoformat(), evidence.registered_by,
                    evidence.content_sha256, json.dumps(payload["metadata"], sort_keys=True),
                ),
            )

    def append_decision(self, decision: HypothesisDecision) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO hypothesis_decision_event(
                    decision_id, hypothesis_id, hypothesis_version, action, lifecycle, verdict,
                    evidence_snapshot_id, reason, actor, event_at, supersedes_decision_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    decision.decision_id, decision.hypothesis_id, decision.hypothesis_version,
                    decision.action, decision.lifecycle.value, decision.verdict.value,
                    decision.evidence_snapshot_id, decision.reason, decision.actor,
                    decision.event_at.isoformat(), decision.supersedes_decision_id,
                ),
            )
