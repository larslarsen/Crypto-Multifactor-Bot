"""EVD-001 operational Evidence Registry repository.

Append-only hypothesis versions, evidence, links, snapshots, and decisions.
Uses migration-0002 tables and ``canonical.content_sha256`` only.
Does not implement ``hypothesis_experiment_link``.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from cryptofactors.evidence.canonical import canonical_json_bytes, content_sha256
from cryptofactors.evidence.models import (
    DecisionAction,
    EvidenceItem,
    EvidenceSnapshot,
    HypothesisDecision,
    HypothesisEvidenceLink,
    HypothesisLifecycle,
    HypothesisVerdict,
    HypothesisVersion,
    _ACTIONS_REQUIRING_SUPERSEDES,
    _NON_PROMOTION_KINDS,
)


class EvidenceRegistryError(RuntimeError):
    """Raised when an Evidence Registry invariant is violated."""


# Supported research/evidence hypotheses seed document schema version.
_SUPPORTED_SEED_REGISTRY_VERSION = 2


def _iso(dt: datetime | None) -> str | None:
    """Fixed-width UTC ISO-8601 with always-present microseconds (…SS.mmmmmmZ).

    Ensures lexical SQLite comparisons match chronological order (REVIEW-0052 #3).
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        raise EvidenceRegistryError("datetime must be timezone-aware")
    utc = dt.astimezone(timezone.utc)
    return (
        f"{utc.year:04d}-{utc.month:02d}-{utc.day:02d}"
        f"T{utc.hour:02d}:{utc.minute:02d}:{utc.second:02d}"
        f".{utc.microsecond:06d}Z"
    )


def _parse_iso(value: str | None) -> datetime | None:
    if value is None:
        return None
    text = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError as exc:
        raise EvidenceRegistryError(f"invalid ISO-8601 datetime: {value!r}") from exc


def _normalize_utc_str(value: str) -> str:
    """Parse any timezone-aware ISO-8601 string and re-emit fixed-width UTC.

    Every persisted comparison timestamp flows through this (REVIEW-0053 #1).
    """
    if not isinstance(value, str) or not value.strip():
        raise EvidenceRegistryError("timestamp must be a non-empty ISO-8601 string")
    parsed = _parse_iso(value)
    if parsed is None:
        raise EvidenceRegistryError(f"invalid ISO-8601 datetime: {value!r}")
    fixed = _iso(parsed)
    if fixed is None:
        raise EvidenceRegistryError(f"invalid ISO-8601 datetime: {value!r}")
    return fixed


def _normalize_utc_dt(value: datetime) -> str:
    """Normalize a timezone-aware datetime to fixed-width UTC string."""
    fixed = _iso(value)
    if fixed is None:
        raise EvidenceRegistryError("datetime must be timezone-aware")
    return fixed


def _evidence_canonical_body(evidence: EvidenceItem) -> dict[str, Any]:
    """Canonical evidence body excluding the digest field."""
    body = evidence.model_dump(mode="json")
    body.pop("content_sha256", None)
    # Normalize timestamps to fixed-width form inside body for stable hashing.
    if body.get("registered_at") is not None:
        body["registered_at"] = _iso(evidence.registered_at)
    if body.get("observed_at") is not None:
        body["observed_at"] = _iso(evidence.observed_at)
    return body


def _stored_evidence_body(row: sqlite3.Row) -> dict[str, Any]:
    """Rebuild the canonical evidence body from a stored row."""
    return {
        "evidence_id": row["evidence_id"],
        "kind": row["kind"],
        "title": row["title"],
        "summary": row["summary"],
        "source_ref": row["source_ref"],
        "artifact_uri": row["artifact_uri"],
        "observed_at": row["observed_at"],
        "registered_at": row["registered_at"],
        "registered_by": row["registered_by"],
        "metadata": json.loads(row["metadata_json"]),
    }


def _load_seed_document(path: Path) -> dict[str, Any]:
    """Load seed document (JSON or YAML). Reject non-object roots."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise EvidenceRegistryError(f"cannot read seed file: {exc}") from exc
    data: Any
    try:
        import yaml  # type: ignore[import-untyped]

        data = yaml.safe_load(text)
    except Exception:
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise EvidenceRegistryError(f"seed file is not valid JSON/YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise EvidenceRegistryError("seed file must contain a top-level object")
    return data


class EvidenceRepository:
    """SQLite repository with append-only evidence and decision operations."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = Path(database_path)

    @staticmethod
    def _map_sqlite_error(exc: sqlite3.Error) -> EvidenceRegistryError:
        if isinstance(exc, sqlite3.IntegrityError):
            return EvidenceRegistryError(f"integrity constraint violated: {exc}")
        return EvidenceRegistryError(f"sqlite error: {exc}")

    @contextmanager
    def _connect(
        self, external: sqlite3.Connection | None = None
    ) -> Iterator[sqlite3.Connection]:
        """Yield a connection. When ``external`` is given, do not commit/close it.

        Connection open, PRAGMA, transactional ops, commit, and rollback-safe SQLite
        failures all map to ``EvidenceRegistryError`` (REVIEW-0054 #1).
        """
        if external is not None:
            yield external
            return
        connection: sqlite3.Connection | None = None
        try:
            try:
                connection = sqlite3.connect(self._database_path)
                connection.row_factory = sqlite3.Row
                connection.execute("PRAGMA foreign_keys = ON")
            except sqlite3.Error as exc:
                raise self._map_sqlite_error(exc) from exc

            assert connection is not None
            try:
                yield connection
                try:
                    connection.commit()
                except sqlite3.Error as exc:
                    connection.rollback()
                    raise self._map_sqlite_error(exc) from exc
            except EvidenceRegistryError:
                # Preserve intentional invariant messages after rollback.
                try:
                    connection.rollback()
                except sqlite3.Error as exc:
                    raise self._map_sqlite_error(exc) from exc
                raise
            except sqlite3.Error as exc:
                try:
                    connection.rollback()
                except sqlite3.Error:
                    pass
                raise self._map_sqlite_error(exc) from exc
            except Exception:
                try:
                    connection.rollback()
                except sqlite3.Error:
                    pass
                raise
        finally:
            if connection is not None:
                try:
                    connection.close()
                except sqlite3.Error as exc:
                    raise self._map_sqlite_error(exc) from exc

    # ------------------------------------------------------------------
    # Hypothesis / evidence registration
    # ------------------------------------------------------------------

    def register_hypothesis(
        self,
        hypothesis: HypothesisVersion,
        *,
        actor: str,
        created_at: str,
        _conn: sqlite3.Connection | None = None,
    ) -> str:
        """Register an immutable hypothesis version. Returns content_sha256."""
        created_at_s = _normalize_utc_str(created_at)
        payload = hypothesis.model_dump(mode="json")
        if payload.get("preregistered_at") is not None and hypothesis.preregistered_at is not None:
            payload["preregistered_at"] = _iso(hypothesis.preregistered_at)
        digest = content_sha256(payload)
        with self._connect(_conn) as connection:
            # Explicit slug collision before any FK/insert path (REVIEW-0052 #6).
            slug_row = connection.execute(
                "SELECT hypothesis_id FROM hypothesis WHERE slug = ?",
                (hypothesis.slug,),
            ).fetchone()
            if slug_row is not None and slug_row["hypothesis_id"] != hypothesis.hypothesis_id:
                raise EvidenceRegistryError(
                    f"slug {hypothesis.slug!r} already used by "
                    f"{slug_row['hypothesis_id']}"
                )

            connection.execute(
                "INSERT OR IGNORE INTO hypothesis(hypothesis_id, slug, created_at, created_by) "
                "VALUES (?, ?, ?, ?)",
                (hypothesis.hypothesis_id, hypothesis.slug, created_at_s, actor),
            )
            row = connection.execute(
                "SELECT slug FROM hypothesis WHERE hypothesis_id = ?",
                (hypothesis.hypothesis_id,),
            ).fetchone()
            if row is not None and row["slug"] != hypothesis.slug:
                raise EvidenceRegistryError(
                    "hypothesis_id already registered with a different slug"
                )

            existing = connection.execute(
                "SELECT content_sha256, details_json FROM hypothesis_version "
                "WHERE hypothesis_id = ? AND version = ?",
                (hypothesis.hypothesis_id, hypothesis.version),
            ).fetchone()
            if existing is not None:
                if existing["content_sha256"] != digest:
                    raise EvidenceRegistryError(
                        "hypothesis version already exists with different content"
                    )
                return digest

            clash = connection.execute(
                "SELECT hypothesis_id, version FROM hypothesis_version "
                "WHERE content_sha256 = ?",
                (digest,),
            ).fetchone()
            if clash is not None:
                raise EvidenceRegistryError(
                    "identical hypothesis content already registered under "
                    f"{clash['hypothesis_id']} v{clash['version']}"
                )
            connection.execute(
                """
                INSERT INTO hypothesis_version(
                    hypothesis_id, version, title, statement, mechanism, expected_sign, phase,
                    primary_metric, advancement_rule, rejection_rule, details_json, content_sha256,
                    preregistered_at, created_at, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    hypothesis.hypothesis_id,
                    hypothesis.version,
                    hypothesis.title,
                    hypothesis.statement,
                    hypothesis.mechanism,
                    hypothesis.expected_sign,
                    hypothesis.phase,
                    hypothesis.primary_metric,
                    hypothesis.advancement_rule,
                    hypothesis.rejection_rule,
                    json.dumps(payload, sort_keys=True, ensure_ascii=False),
                    digest,
                    _iso(hypothesis.preregistered_at),
                    created_at_s,
                    actor,
                ),
            )
        return digest

    def add_evidence(
        self, evidence: EvidenceItem, *, _conn: sqlite3.Connection | None = None
    ) -> str:
        """Register immutable evidence. Derives/verifies content_sha256 (REVIEW-0052 #1)."""
        body = _evidence_canonical_body(evidence)
        digest = content_sha256(body)
        if evidence.content_sha256 != digest:
            raise EvidenceRegistryError(
                "evidence content_sha256 does not match canonical body digest"
            )
        with self._connect(_conn) as connection:
            existing = connection.execute(
                "SELECT evidence_id, content_sha256, metadata_json, kind, title, summary, "
                "source_ref, artifact_uri, observed_at, registered_at, registered_by "
                "FROM evidence_item WHERE evidence_id = ?",
                (evidence.evidence_id,),
            ).fetchone()
            if existing is not None:
                if existing["content_sha256"] != digest:
                    raise EvidenceRegistryError(
                        "evidence ID already exists with different content"
                    )
                # Complete canonical content equality for idempotence (not hash-only).
                if _stored_evidence_body(existing) != body:
                    raise EvidenceRegistryError(
                        "evidence ID exists with matching hash claim but different content"
                    )
                return digest

            clash = connection.execute(
                "SELECT evidence_id FROM evidence_item WHERE content_sha256 = ?",
                (digest,),
            ).fetchone()
            if clash is not None and clash["evidence_id"] != evidence.evidence_id:
                raise EvidenceRegistryError(
                    "identical evidence content already registered under "
                    f"{clash['evidence_id']}"
                )
            connection.execute(
                """
                INSERT INTO evidence_item(
                    evidence_id, kind, title, summary, source_ref, artifact_uri, observed_at,
                    registered_at, registered_by, content_sha256, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    evidence.evidence_id,
                    evidence.kind.value,
                    evidence.title,
                    evidence.summary,
                    evidence.source_ref,
                    evidence.artifact_uri,
                    _iso(evidence.observed_at),
                    _iso(evidence.registered_at),
                    evidence.registered_by,
                    digest,
                    json.dumps(body.get("metadata") or {}, sort_keys=True, ensure_ascii=False),
                ),
            )
        return digest

    def link_evidence(
        self, link: HypothesisEvidenceLink, *, _conn: sqlite3.Connection | None = None
    ) -> None:
        """Link evidence to a hypothesis version (append-only composite PK)."""
        integrity_payload = link.integrity.model_dump(mode="json")
        link_at = _normalize_utc_dt(link.registered_at)
        with self._connect(_conn) as connection:
            hv = connection.execute(
                "SELECT created_at FROM hypothesis_version "
                "WHERE hypothesis_id = ? AND version = ?",
                (link.hypothesis_id, link.hypothesis_version),
            ).fetchone()
            if hv is None:
                raise EvidenceRegistryError(
                    f"unknown hypothesis version {link.hypothesis_id} v{link.hypothesis_version}"
                )
            ev = connection.execute(
                "SELECT registered_at FROM evidence_item WHERE evidence_id = ?",
                (link.evidence_id,),
            ).fetchone()
            if ev is None:
                raise EvidenceRegistryError(f"unknown evidence_id {link.evidence_id}")
            # Link cannot predate hypothesis version or evidence registration.
            if link_at < hv["created_at"]:
                raise EvidenceRegistryError(
                    "link registered_at cannot predate hypothesis version created_at"
                )
            if link_at < ev["registered_at"]:
                raise EvidenceRegistryError(
                    "link registered_at cannot predate evidence registered_at"
                )

            existing = connection.execute(
                "SELECT integrity_json, direction, relevance, rationale, "
                "registered_at, registered_by FROM hypothesis_evidence_link "
                "WHERE hypothesis_id = ? AND hypothesis_version = ? AND evidence_id = ?",
                (link.hypothesis_id, link.hypothesis_version, link.evidence_id),
            ).fetchone()
            if existing is not None:
                if (
                    existing["direction"] != link.direction.value
                    or existing["relevance"] != link.relevance.value
                    or existing["rationale"] != link.rationale
                    or existing["registered_at"] != link_at
                    or existing["registered_by"] != link.registered_by
                    or json.loads(existing["integrity_json"]) != integrity_payload
                ):
                    raise EvidenceRegistryError(
                        "evidence link already exists with different attributes"
                    )
                return
            connection.execute(
                """
                INSERT INTO hypothesis_evidence_link(
                    hypothesis_id, hypothesis_version, evidence_id, direction, relevance,
                    rationale, integrity_json, registered_at, registered_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    link.hypothesis_id,
                    link.hypothesis_version,
                    link.evidence_id,
                    link.direction.value,
                    link.relevance.value,
                    link.rationale,
                    json.dumps(integrity_payload, sort_keys=True, ensure_ascii=False),
                    link_at,
                    link.registered_by,
                ),
            )

    # ------------------------------------------------------------------
    # Snapshots
    # ------------------------------------------------------------------

    def build_snapshot(
        self,
        hypothesis_id: str,
        version: int,
        *,
        as_of: datetime,
        generated_at: datetime | None = None,
        _conn: sqlite3.Connection | None = None,
    ) -> EvidenceSnapshot:
        """Build a deterministic snapshot of linked evidence at ``as_of``.

        Includes only evidence and links with registration time <= as_of.
        No unused ``actor`` argument (REVIEW-0052 #6).
        """
        as_of_s = _normalize_utc_dt(as_of)
        gen_at = generated_at or datetime.now(timezone.utc)
        gen_at_s = _normalize_utc_dt(gen_at)
        if gen_at_s < as_of_s:
            raise EvidenceRegistryError("generated_at cannot predate as_of")

        with self._connect(_conn) as connection:
            hv = connection.execute(
                "SELECT content_sha256, created_at FROM hypothesis_version "
                "WHERE hypothesis_id = ? AND version = ?",
                (hypothesis_id, version),
            ).fetchone()
            if hv is None:
                raise EvidenceRegistryError(
                    f"unknown hypothesis version {hypothesis_id} v{version}"
                )
            if as_of_s < hv["created_at"]:
                raise EvidenceRegistryError(
                    "snapshot as_of cannot predate hypothesis version created_at"
                )
            # Both link and evidence must be registered by as_of (REVIEW-0052 #3).
            rows = connection.execute(
                """
                SELECT
                    l.evidence_id, l.direction, l.relevance, l.rationale,
                    l.integrity_json, l.registered_at, l.registered_by,
                    e.kind, e.title, e.summary, e.source_ref, e.content_sha256,
                    e.observed_at, e.registered_at AS evidence_registered_at
                FROM hypothesis_evidence_link l
                JOIN evidence_item e ON e.evidence_id = l.evidence_id
                WHERE l.hypothesis_id = ? AND l.hypothesis_version = ?
                  AND l.registered_at <= ?
                  AND e.registered_at <= ?
                ORDER BY l.evidence_id ASC
                """,
                (hypothesis_id, version, as_of_s, as_of_s),
            ).fetchall()

            link_records: list[dict[str, Any]] = []
            for r in rows:
                link_records.append(
                    {
                        "evidence_id": r["evidence_id"],
                        "evidence_kind": r["kind"],
                        "evidence_title": r["title"],
                        "evidence_summary": r["summary"],
                        "evidence_source_ref": r["source_ref"],
                        "evidence_content_sha256": r["content_sha256"],
                        "evidence_observed_at": r["observed_at"],
                        "evidence_registered_at": r["evidence_registered_at"],
                        "direction": r["direction"],
                        "relevance": r["relevance"],
                        "rationale": r["rationale"],
                        "integrity": json.loads(r["integrity_json"]),
                        "link_registered_at": r["registered_at"],
                        "link_registered_by": r["registered_by"],
                    }
                )

            body = {
                "hypothesis_id": hypothesis_id,
                "hypothesis_version": version,
                "hypothesis_content_sha256": hv["content_sha256"],
                "as_of": as_of_s,
                "links": link_records,
            }
            digest = content_sha256(body)
            snapshot_id = f"snap_{digest[:32]}"

            existing = connection.execute(
                "SELECT snapshot_id, content_sha256, snapshot_json, as_of, generated_at, artifact_uri "
                "FROM evidence_snapshot WHERE content_sha256 = ?",
                (digest,),
            ).fetchone()
            if existing is not None:
                return EvidenceSnapshot(
                    snapshot_id=existing["snapshot_id"],
                    hypothesis_id=hypothesis_id,
                    hypothesis_version=version,
                    as_of=_parse_iso(existing["as_of"]) or as_of,
                    generated_at=_parse_iso(existing["generated_at"]) or gen_at,
                    content_sha256=existing["content_sha256"],
                    artifact_uri=existing["artifact_uri"],
                    links=tuple(json.loads(existing["snapshot_json"])["links"]),
                )

            id_clash = connection.execute(
                "SELECT content_sha256 FROM evidence_snapshot WHERE snapshot_id = ?",
                (snapshot_id,),
            ).fetchone()
            if id_clash is not None and id_clash["content_sha256"] != digest:
                raise EvidenceRegistryError(f"snapshot_id collision for {snapshot_id}")

            connection.execute(
                """
                INSERT INTO evidence_snapshot(
                    snapshot_id, hypothesis_id, hypothesis_version, as_of, generated_at,
                    content_sha256, artifact_uri, snapshot_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot_id,
                    hypothesis_id,
                    version,
                    as_of_s,
                    gen_at_s,
                    digest,
                    None,
                    json.dumps(body, sort_keys=True, ensure_ascii=False),
                ),
            )
            return EvidenceSnapshot(
                snapshot_id=snapshot_id,
                hypothesis_id=hypothesis_id,
                hypothesis_version=version,
                as_of=as_of,
                generated_at=gen_at,
                content_sha256=digest,
                artifact_uri=None,
                links=tuple(link_records),
            )

    def get_snapshot(
        self, snapshot_id: str, *, _conn: sqlite3.Connection | None = None
    ) -> EvidenceSnapshot:
        with self._connect(_conn) as connection:
            row = connection.execute(
                "SELECT * FROM evidence_snapshot WHERE snapshot_id = ?",
                (snapshot_id,),
            ).fetchone()
            if row is None:
                raise EvidenceRegistryError(f"unknown snapshot_id {snapshot_id}")
            body = json.loads(row["snapshot_json"])
            return EvidenceSnapshot(
                snapshot_id=row["snapshot_id"],
                hypothesis_id=row["hypothesis_id"],
                hypothesis_version=int(row["hypothesis_version"]),
                as_of=_parse_iso(row["as_of"]) or datetime.now(timezone.utc),
                generated_at=_parse_iso(row["generated_at"]) or datetime.now(timezone.utc),
                content_sha256=row["content_sha256"],
                artifact_uri=row["artifact_uri"],
                links=tuple(body.get("links") or ()),
            )

    # ------------------------------------------------------------------
    # Decisions
    # ------------------------------------------------------------------

    def append_decision(
        self, decision: HypothesisDecision, *, _conn: sqlite3.Connection | None = None
    ) -> None:
        """Append a decision event with ownership and supersession rules."""
        action = decision.normalized_action()
        if action not in {a.value for a in DecisionAction}:
            raise EvidenceRegistryError(f"unsupported decision action: {decision.action!r}")
        event_at_s = _normalize_utc_dt(decision.event_at)

        with self._connect(_conn) as connection:
            snap = connection.execute(
                "SELECT snapshot_id, hypothesis_id, hypothesis_version, snapshot_json, "
                "as_of, generated_at "
                "FROM evidence_snapshot WHERE snapshot_id = ?",
                (decision.evidence_snapshot_id,),
            ).fetchone()
            if snap is None:
                raise EvidenceRegistryError(
                    f"unknown evidence_snapshot_id {decision.evidence_snapshot_id}"
                )
            # Snapshot must belong to the decision's exact hypothesis/version.
            if (
                snap["hypothesis_id"] != decision.hypothesis_id
                or int(snap["hypothesis_version"]) != decision.hypothesis_version
            ):
                raise EvidenceRegistryError(
                    "evidence_snapshot_id does not belong to the decision "
                    f"hypothesis/version ({decision.hypothesis_id} "
                    f"v{decision.hypothesis_version})"
                )
            # Decision cannot predate the cited snapshot's as_of or generation.
            if event_at_s < snap["as_of"] or event_at_s < snap["generated_at"]:
                raise EvidenceRegistryError(
                    "decision event_at cannot predate snapshot as_of/generated_at"
                )
            body = json.loads(snap["snapshot_json"])
            links = body.get("links") or []

            if decision.is_promotion_verdict():
                self._assert_promotion_allowed(links)

            if action in _ACTIONS_REQUIRING_SUPERSEDES:
                if not decision.supersedes_decision_id:
                    raise EvidenceRegistryError(
                        f"{action} requires supersedes_decision_id"
                    )
            elif decision.supersedes_decision_id is not None:
                raise EvidenceRegistryError(
                    f"action {action} must not set supersedes_decision_id"
                )

            if decision.supersedes_decision_id is not None:
                prior = connection.execute(
                    "SELECT decision_id, hypothesis_id, hypothesis_version, event_at "
                    "FROM hypothesis_decision_event WHERE decision_id = ?",
                    (decision.supersedes_decision_id,),
                ).fetchone()
                if prior is None:
                    raise EvidenceRegistryError(
                        f"unknown supersedes_decision_id {decision.supersedes_decision_id}"
                    )
                if (
                    prior["hypothesis_id"] != decision.hypothesis_id
                    or int(prior["hypothesis_version"]) != decision.hypothesis_version
                ):
                    raise EvidenceRegistryError(
                        "supersedes_decision_id must reference a prior decision "
                        "for the same hypothesis/version"
                    )
                # CORRECT/REOPEN must occur strictly after the superseded event.
                if event_at_s <= prior["event_at"]:
                    raise EvidenceRegistryError(
                        f"{action} event_at must be strictly after the superseded event"
                    )

            hv = connection.execute(
                "SELECT 1 FROM hypothesis_version WHERE hypothesis_id = ? AND version = ?",
                (decision.hypothesis_id, decision.hypothesis_version),
            ).fetchone()
            if hv is None:
                raise EvidenceRegistryError(
                    f"unknown hypothesis version {decision.hypothesis_id} "
                    f"v{decision.hypothesis_version}"
                )

            existing = connection.execute(
                "SELECT decision_id, hypothesis_id, hypothesis_version, action, lifecycle, "
                "verdict, evidence_snapshot_id, reason, actor, event_at, supersedes_decision_id "
                "FROM hypothesis_decision_event WHERE decision_id = ?",
                (decision.decision_id,),
            ).fetchone()
            if existing is not None:
                # Fully idempotent only when the complete event identity matches.
                if (
                    existing["hypothesis_id"] != decision.hypothesis_id
                    or int(existing["hypothesis_version"]) != decision.hypothesis_version
                    or existing["action"] != action
                    or existing["lifecycle"] != decision.lifecycle.value
                    or existing["verdict"] != decision.verdict.value
                    or existing["evidence_snapshot_id"] != decision.evidence_snapshot_id
                    or existing["reason"] != decision.reason
                    or existing["actor"] != decision.actor
                    or existing["event_at"] != event_at_s
                    or existing["supersedes_decision_id"] != decision.supersedes_decision_id
                ):
                    raise EvidenceRegistryError(
                        f"decision_id already exists with different content: "
                        f"{decision.decision_id}"
                    )
                return

            connection.execute(
                """
                INSERT INTO hypothesis_decision_event(
                    decision_id, hypothesis_id, hypothesis_version, action, lifecycle, verdict,
                    evidence_snapshot_id, reason, actor, event_at, supersedes_decision_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    decision.decision_id,
                    decision.hypothesis_id,
                    decision.hypothesis_version,
                    action,
                    decision.lifecycle.value,
                    decision.verdict.value,
                    decision.evidence_snapshot_id,
                    decision.reason,
                    decision.actor,
                    event_at_s,
                    decision.supersedes_decision_id,
                ),
            )

    @staticmethod
    def _assert_promotion_allowed(links: Sequence[dict[str, Any]]) -> None:
        if not links:
            raise EvidenceRegistryError(
                "promotion verdict requires a non-empty evidence snapshot"
            )
        non_promo = {k.value for k in _NON_PROMOTION_KINDS}
        kinds = {str(link.get("evidence_kind")) for link in links}
        if kinds and kinds.issubset(non_promo):
            raise EvidenceRegistryError(
                "SUPPORTED/REPLICATED cannot cite a snapshot containing only "
                "literature or legacy evidence"
            )
        for link in links:
            integ = link.get("integrity") or {}
            if integ.get("point_in_time") == "FAIL":
                raise EvidenceRegistryError(
                    "SUPPORTED/REPLICATED cannot cite evidence with "
                    "point_in_time integrity FAIL"
                )
            if integ.get("causal_split") == "FAIL":
                raise EvidenceRegistryError(
                    "SUPPORTED/REPLICATED cannot cite evidence with "
                    "causal_split integrity FAIL"
                )

    # ------------------------------------------------------------------
    # List / show
    # ------------------------------------------------------------------

    def list_hypotheses(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT h.hypothesis_id, h.slug, h.created_at, h.created_by,
                       MAX(v.version) AS latest_version
                FROM hypothesis h
                LEFT JOIN hypothesis_version v ON v.hypothesis_id = h.hypothesis_id
                GROUP BY h.hypothesis_id
                ORDER BY h.hypothesis_id ASC
                """
            ).fetchall()
            return [dict(r) for r in rows]

    def show_hypothesis(
        self, hypothesis_id: str, *, _conn: sqlite3.Connection | None = None
    ) -> dict[str, Any]:
        with self._connect(_conn) as connection:
            h = connection.execute(
                "SELECT * FROM hypothesis WHERE hypothesis_id = ?",
                (hypothesis_id,),
            ).fetchone()
            if h is None:
                raise EvidenceRegistryError(f"unknown hypothesis_id {hypothesis_id}")
            versions = connection.execute(
                "SELECT * FROM hypothesis_version WHERE hypothesis_id = ? "
                "ORDER BY version ASC",
                (hypothesis_id,),
            ).fetchall()
            decisions = connection.execute(
                "SELECT * FROM hypothesis_decision_event WHERE hypothesis_id = ? "
                "ORDER BY event_at ASC, decision_id ASC",
                (hypothesis_id,),
            ).fetchall()
            return {
                "hypothesis": dict(h),
                "versions": [dict(v) for v in versions],
                "decisions": [dict(d) for d in decisions],
                "current": self._derive_current_state(list(decisions)),
            }

    def list_evidence(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM evidence_item ORDER BY evidence_id ASC"
            ).fetchall()
            out = []
            for r in rows:
                item = dict(r)
                item["metadata"] = json.loads(r["metadata_json"])
                out.append(item)
            return out

    @staticmethod
    def _derive_current_state(
        decisions: Sequence[sqlite3.Row | dict[str, Any]],
    ) -> dict[str, Any]:
        """Latest lifecycle/verdict by chronological decision order."""
        if not decisions:
            return {
                "lifecycle": HypothesisLifecycle.DRAFT.value,
                "verdict": HypothesisVerdict.UNTESTED.value,
                "latest_decision_id": None,
            }
        # decisions already ordered by event_at, decision_id
        last = decisions[-1]
        return {
            "lifecycle": last["lifecycle"],
            "verdict": last["verdict"],
            "latest_decision_id": last["decision_id"],
        }

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export_current_state(self, fmt: str = "json") -> str | bytes:
        """Full deterministic current-state export (REVIEW-0052 #5)."""
        fmt_n = fmt.strip().lower()
        if fmt_n not in {"json", "markdown", "md"}:
            raise EvidenceRegistryError("format must be 'json' or 'markdown'")

        with self._connect() as connection:
            all_evidence = connection.execute(
                "SELECT * FROM evidence_item ORDER BY evidence_id ASC"
            ).fetchall()
            evidence_list = []
            for e in all_evidence:
                evidence_list.append(
                    {
                        "evidence_id": e["evidence_id"],
                        "kind": e["kind"],
                        "title": e["title"],
                        "summary": e["summary"],
                        "source_ref": e["source_ref"],
                        "artifact_uri": e["artifact_uri"],
                        "observed_at": e["observed_at"],
                        "registered_at": e["registered_at"],
                        "registered_by": e["registered_by"],
                        "content_sha256": e["content_sha256"],
                        "metadata": json.loads(e["metadata_json"]),
                    }
                )

            hypotheses = connection.execute(
                "SELECT * FROM hypothesis ORDER BY hypothesis_id ASC"
            ).fetchall()
            hyp_list: list[dict[str, Any]] = []
            for h in hypotheses:
                hid = h["hypothesis_id"]
                versions = connection.execute(
                    "SELECT * FROM hypothesis_version WHERE hypothesis_id = ? "
                    "ORDER BY version ASC",
                    (hid,),
                ).fetchall()
                decisions = connection.execute(
                    "SELECT * FROM hypothesis_decision_event WHERE hypothesis_id = ? "
                    "ORDER BY event_at ASC, decision_id ASC",
                    (hid,),
                ).fetchall()
                links = connection.execute(
                    "SELECT * FROM hypothesis_evidence_link WHERE hypothesis_id = ? "
                    "ORDER BY hypothesis_version ASC, evidence_id ASC",
                    (hid,),
                ).fetchall()
                snaps = connection.execute(
                    "SELECT snapshot_id, hypothesis_version, as_of, generated_at, "
                    "content_sha256 FROM evidence_snapshot WHERE hypothesis_id = ? "
                    "ORDER BY as_of ASC, snapshot_id ASC",
                    (hid,),
                ).fetchall()
                version_payloads = []
                for v in versions:
                    details = json.loads(v["details_json"])
                    version_payloads.append(
                        {
                            "version": v["version"],
                            "title": v["title"],
                            "statement": v["statement"],
                            "mechanism": v["mechanism"],
                            "expected_sign": v["expected_sign"],
                            "phase": v["phase"],
                            "primary_metric": v["primary_metric"],
                            "advancement_rule": v["advancement_rule"],
                            "rejection_rule": v["rejection_rule"],
                            "content_sha256": v["content_sha256"],
                            "preregistered_at": v["preregistered_at"],
                            "created_at": v["created_at"],
                            "created_by": v["created_by"],
                            "details": details,
                        }
                    )
                hyp_list.append(
                    {
                        "hypothesis_id": hid,
                        "slug": h["slug"],
                        "created_at": h["created_at"],
                        "created_by": h["created_by"],
                        "versions": version_payloads,
                        "links": [
                            {
                                "hypothesis_version": ln["hypothesis_version"],
                                "evidence_id": ln["evidence_id"],
                                "direction": ln["direction"],
                                "relevance": ln["relevance"],
                                "rationale": ln["rationale"],
                                "integrity": json.loads(ln["integrity_json"]),
                                "registered_at": ln["registered_at"],
                                "registered_by": ln["registered_by"],
                            }
                            for ln in links
                        ],
                        "snapshots": [dict(s) for s in snaps],
                        "decisions": [
                            {
                                "decision_id": d["decision_id"],
                                "hypothesis_version": d["hypothesis_version"],
                                "action": d["action"],
                                "lifecycle": d["lifecycle"],
                                "verdict": d["verdict"],
                                "evidence_snapshot_id": d["evidence_snapshot_id"],
                                "reason": d["reason"],
                                "event_at": d["event_at"],
                                "actor": d["actor"],
                                "supersedes_decision_id": d["supersedes_decision_id"],
                            }
                            for d in decisions
                        ],
                        "current": self._derive_current_state(list(decisions)),
                    }
                )

            state = {
                "evidence": evidence_list,
                "hypotheses": hyp_list,
            }

        if fmt_n == "json":
            return canonical_json_bytes(state)

        lines: list[str] = ["# Evidence Registry Current State", ""]
        lines.append("## Evidence items")
        lines.append("")
        if not state["evidence"]:
            lines.append("- (none)")
        for e in state["evidence"]:
            lines.append(
                f"- `{e['evidence_id']}` [{e['kind']}] {e['title']} "
                f"(`{e['content_sha256'][:12]}…`)"
            )
        lines.append("")
        for hyp in state["hypotheses"]:
            cur = hyp["current"]
            lines.append(f"## {hyp['hypothesis_id']} — {hyp['slug']}")
            lines.append("")
            lines.append(
                f"- current: lifecycle=`{cur['lifecycle']}` verdict=`{cur['verdict']}`"
            )
            lines.append(f"- created_at: `{hyp['created_at']}`")
            lines.append(f"- created_by: `{hyp['created_by']}`")
            lines.append("")
            lines.append("### Versions")
            for v in hyp["versions"]:
                lines.append(
                    f"- v{v['version']}: {v['title']} (`{v['content_sha256'][:12]}…`)"
                )
                lines.append(f"  - phase: {v['phase']}")
                lines.append(f"  - primary_metric: {v['primary_metric']}")
            lines.append("")
            lines.append("### Evidence links")
            if not hyp["links"]:
                lines.append("- (none)")
            for ln in hyp["links"]:
                lines.append(
                    f"- v{ln['hypothesis_version']} {ln['evidence_id']} "
                    f"{ln['direction']}/{ln['relevance']}"
                )
            lines.append("")
            lines.append("### Snapshots")
            if not hyp["snapshots"]:
                lines.append("- (none)")
            for s in hyp["snapshots"]:
                lines.append(
                    f"- {s['snapshot_id']} as_of={s['as_of']} "
                    f"(`{s['content_sha256'][:12]}…`)"
                )
            lines.append("")
            lines.append("### Decision history")
            if not hyp["decisions"]:
                lines.append("- (none)")
            for d in hyp["decisions"]:
                lines.append(
                    f"- {d['event_at']} {d['decision_id']}: {d['action']} "
                    f"{d['lifecycle']}/{d['verdict']} snapshot={d['evidence_snapshot_id']}"
                )
            lines.append("")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Seed import (atomic)
    # ------------------------------------------------------------------

    def seed_import(
        self,
        yaml_or_json_path: Path,
        *,
        actor: str,
        created_at: str | None = None,
    ) -> int:
        """Atomically validate then import seed hypotheses (REVIEW-0052 #4 / 0053 #2).

        Lifecycle/verdict become initial append-only decisions on an empty snapshot.
        Provenance fields (e.g. sprint_002_source_basis) enter immutable version content.
        Unknown fields are rejected. Fully idempotent on re-import without rebuilding
        seed decision identity from later registry mutations.
        """
        path = Path(yaml_or_json_path)
        data = _load_seed_document(path)

        top_allowed = {"registry_version", "as_of", "hypotheses"}
        top_unknown = set(data.keys()) - top_allowed
        if top_unknown:
            raise EvidenceRegistryError(
                f"unsupported top-level seed fields: {sorted(top_unknown)}"
            )
        if "registry_version" not in data:
            raise EvidenceRegistryError("seed file must declare registry_version")
        try:
            registry_version = int(data["registry_version"])
        except (TypeError, ValueError) as exc:
            raise EvidenceRegistryError(
                f"invalid registry_version: {data['registry_version']!r}"
            ) from exc
        if registry_version != _SUPPORTED_SEED_REGISTRY_VERSION:
            raise EvidenceRegistryError(
                f"unsupported registry_version {registry_version}; "
                f"expected {_SUPPORTED_SEED_REGISTRY_VERSION}"
            )
        if "hypotheses" not in data:
            raise EvidenceRegistryError("seed file must contain a top-level 'hypotheses' list")
        entries = data["hypotheses"]
        if not isinstance(entries, list):
            raise EvidenceRegistryError("'hypotheses' must be a list")

        allowed = {
            "hypothesis_id",
            "version",
            "slug",
            "title",
            "statement",
            "mechanism",
            "expected_sign",
            "phase",
            "primary_metric",
            "advancement_rule",
            "rejection_rule",
            "known_confounders",
            "required_dataset_types",
            "preregistered_at",
            "sprint_002_source_basis",
            "lifecycle",
            "verdict",
        }
        # Phase 1: validate complete seed before any mutation.
        prepared: list[tuple[HypothesisVersion, HypothesisLifecycle, HypothesisVerdict]] = []
        for raw in entries:
            if not isinstance(raw, dict):
                raise EvidenceRegistryError("each hypothesis entry must be an object")
            unknown = set(raw.keys()) - allowed
            if unknown:
                raise EvidenceRegistryError(
                    f"unsupported seed fields for {raw.get('hypothesis_id')}: "
                    f"{sorted(unknown)}"
                )
            try:
                lifecycle = HypothesisLifecycle(str(raw.get("lifecycle", "REGISTERED")))
                verdict = HypothesisVerdict(str(raw.get("verdict", "UNTESTED")))
            except ValueError as exc:
                raise EvidenceRegistryError(
                    f"invalid lifecycle/verdict for {raw.get('hypothesis_id')}: {exc}"
                ) from exc
            payload = {k: v for k, v in raw.items() if k not in {"lifecycle", "verdict"}}
            if "known_confounders" in payload and isinstance(
                payload["known_confounders"], list
            ):
                payload["known_confounders"] = tuple(payload["known_confounders"])
            if "required_dataset_types" in payload and isinstance(
                payload["required_dataset_types"], list
            ):
                payload["required_dataset_types"] = tuple(payload["required_dataset_types"])
            try:
                hyp = HypothesisVersion.model_validate(payload)
            except ValidationError as exc:
                raise EvidenceRegistryError(
                    f"invalid seed hypothesis {raw.get('hypothesis_id')}: {exc}"
                ) from exc
            prepared.append((hyp, lifecycle, verdict))

        # Deterministic seed clock only: explicit created_at or validated top-level as_of.
        # No wall-clock fallback (REVIEW-0053 #2).
        if created_at is not None:
            ts = _normalize_utc_str(created_at)
        elif data.get("as_of") is not None:
            ts = _normalize_utc_str(str(data["as_of"]))
        else:
            raise EvidenceRegistryError(
                "seed requires explicit created_at argument or top-level as_of timestamp"
            )
        as_of_dt = _parse_iso(ts)
        if as_of_dt is None:
            raise EvidenceRegistryError("seed timestamp is invalid")

        seed_reason = "seed import initial state"
        registered = 0
        # Phase 2: single transaction for all mutations (atomic).
        with self._connect() as connection:
            for hyp, lifecycle, verdict in prepared:
                decision_id = f"dec_seed_{hyp.hypothesis_id}_v{hyp.version}"
                existing_version = connection.execute(
                    "SELECT content_sha256 FROM hypothesis_version "
                    "WHERE hypothesis_id = ? AND version = ?",
                    (hyp.hypothesis_id, hyp.version),
                ).fetchone()
                existing_decision = connection.execute(
                    "SELECT decision_id, hypothesis_id, hypothesis_version, action, "
                    "lifecycle, verdict, evidence_snapshot_id, reason, actor, event_at, "
                    "supersedes_decision_id "
                    "FROM hypothesis_decision_event WHERE decision_id = ?",
                    (decision_id,),
                ).fetchone()
                was_new = existing_version is None

                # Register/verify version identity first (content clash fails closed).
                self.register_hypothesis(
                    hyp, actor=actor, created_at=ts, _conn=connection
                )
                if was_new:
                    registered += 1

                if existing_decision is not None:
                    # True no-op when seed decision + initial snapshot identity match.
                    # Do not rebuild snapshot from later registry mutations (REVIEW-0054 #2).
                    if (
                        existing_decision["hypothesis_id"] != hyp.hypothesis_id
                        or int(existing_decision["hypothesis_version"]) != hyp.version
                        or existing_decision["action"] != DecisionAction.REGISTER.value
                        or existing_decision["lifecycle"] != lifecycle.value
                        or existing_decision["verdict"] != verdict.value
                        or existing_decision["reason"] != seed_reason
                        or existing_decision["actor"] != actor
                        or existing_decision["event_at"] != ts
                        or existing_decision["supersedes_decision_id"] is not None
                    ):
                        raise EvidenceRegistryError(
                            f"seed decision {decision_id} already exists with "
                            "different initial state"
                        )
                    self._assert_seed_initial_snapshot(
                        connection,
                        snapshot_id=str(existing_decision["evidence_snapshot_id"]),
                        hypothesis_id=hyp.hypothesis_id,
                        version=hyp.version,
                        seed_ts=ts,
                        decision_id=decision_id,
                    )
                    continue

                # First-time seed decision: empty snapshot only. Fail closed if linked
                # evidence already exists at the seed clock (not the empty initial state).
                pre_existing = connection.execute(
                    """
                    SELECT COUNT(*) AS n
                    FROM hypothesis_evidence_link l
                    JOIN evidence_item e ON e.evidence_id = l.evidence_id
                    WHERE l.hypothesis_id = ? AND l.hypothesis_version = ?
                      AND l.registered_at <= ?
                      AND e.registered_at <= ?
                    """,
                    (hyp.hypothesis_id, hyp.version, ts, ts),
                ).fetchone()
                if pre_existing is not None and int(pre_existing["n"]) > 0:
                    raise EvidenceRegistryError(
                        f"cannot create seed initial state for {hyp.hypothesis_id} "
                        f"v{hyp.version}: linked evidence already exists at seed as_of"
                    )

                snap = self.build_snapshot(
                    hyp.hypothesis_id,
                    hyp.version,
                    as_of=as_of_dt,
                    generated_at=as_of_dt,
                    _conn=connection,
                )
                if snap.links:
                    raise EvidenceRegistryError(
                        f"seed snapshot for {hyp.hypothesis_id} v{hyp.version} "
                        "is not empty initial state"
                    )
                self.append_decision(
                    HypothesisDecision(
                        decision_id=decision_id,
                        hypothesis_id=hyp.hypothesis_id,
                        hypothesis_version=hyp.version,
                        action=DecisionAction.REGISTER.value,
                        lifecycle=lifecycle,
                        verdict=verdict,
                        evidence_snapshot_id=snap.snapshot_id,
                        reason=seed_reason,
                        actor=actor,
                        event_at=as_of_dt,
                        supersedes_decision_id=None,
                    ),
                    _conn=connection,
                )
        return registered

    @staticmethod
    def _assert_seed_initial_snapshot(
        connection: sqlite3.Connection,
        *,
        snapshot_id: str,
        hypothesis_id: str,
        version: int,
        seed_ts: str,
        decision_id: str,
    ) -> None:
        """Verify an existing seed decision cites the empty initial seed snapshot."""
        snap = connection.execute(
            "SELECT snapshot_id, hypothesis_id, hypothesis_version, as_of, generated_at, "
            "snapshot_json FROM evidence_snapshot WHERE snapshot_id = ?",
            (snapshot_id,),
        ).fetchone()
        if snap is None:
            raise EvidenceRegistryError(
                f"seed decision {decision_id} references missing snapshot {snapshot_id}"
            )
        if (
            snap["hypothesis_id"] != hypothesis_id
            or int(snap["hypothesis_version"]) != version
        ):
            raise EvidenceRegistryError(
                f"seed decision {decision_id} snapshot does not belong to "
                f"{hypothesis_id} v{version}"
            )
        if snap["as_of"] != seed_ts or snap["generated_at"] != seed_ts:
            raise EvidenceRegistryError(
                f"seed decision {decision_id} snapshot timestamps do not match seed clock"
            )
        try:
            body = json.loads(snap["snapshot_json"])
        except json.JSONDecodeError as exc:
            raise EvidenceRegistryError(
                f"seed decision {decision_id} snapshot_json is invalid"
            ) from exc
        if not isinstance(body, dict):
            raise EvidenceRegistryError(
                f"seed decision {decision_id} snapshot body must be an object"
            )
        if body.get("as_of") != seed_ts:
            raise EvidenceRegistryError(
                f"seed decision {decision_id} snapshot body as_of does not match seed clock"
            )
        links = body.get("links") or []
        if links:
            raise EvidenceRegistryError(
                f"seed decision {decision_id} snapshot is not the empty initial seed state"
            )


def seed_import_hypotheses(
    repository: EvidenceRepository,
    yaml_or_json_path: Path,
    *,
    actor: str,
    created_at: str | None = None,
) -> int:
    """Module-level seed entrypoint; delegates to ``EvidenceRepository.seed_import``."""
    return repository.seed_import(
        yaml_or_json_path, actor=actor, created_at=created_at
    )
