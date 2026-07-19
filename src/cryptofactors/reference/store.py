"""SQLite-backed REF-001 reference master store.

Transactional writes reject invalid intervals, conflicting active versions,
impossible references, and silent alias collisions. As-of queries require both
decision_time and knowledge_time and enforce both bitemporal windows.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from contextlib import contextmanager
from typing import Any, Iterator

from cryptofactors.ids import fingerprint
from cryptofactors.reference.errors import (
    ReferenceConflictError,
    ReferenceNotFoundError,
    ReferenceResolutionError,
    ReferenceValidationError,
)
from cryptofactors.reference.models import (
    AliasRecord,
    AmbiguityCase,
    AmbiguityStatus,
    Asset,
    AssetClass,
    BiTemporalWindow,
    Instrument,
    InstrumentType,
    InstrumentVersion,
    ListingEvent,
    ListingEventType,
    MigrationEvent,
    MigrationEventType,
    ResolutionOutcome,
    ResolutionResult,
    TargetKind,
    Venue,
    VenueType,
    dt_to_iso,
    ensure_utc,
    iso_to_dt,
    normalize_alias,
)

_OPEN = None  # sentinel meaning open-ended upper bound in SQL (NULL)


def _json_dumps(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _json_loads(text: str | None) -> dict[str, Any]:
    if not text:
        return {}
    data = json.loads(text)
    if not isinstance(data, dict):
        return {}
    return data


def _window_active_sql(
    valid_from_col: str,
    valid_to_col: str,
    known_from_col: str,
    known_to_col: str,
) -> str:
    """SQL predicate: half-open active at :decision_time and :knowledge_time."""
    return (
        f"{valid_from_col} <= :decision_time "
        f"AND ({valid_to_col} IS NULL OR {valid_to_col} > :decision_time) "
        f"AND {known_from_col} <= :knowledge_time "
        f"AND ({known_to_col} IS NULL OR {known_to_col} > :knowledge_time)"
    )


class ReferenceStore:
    """Point-in-time reference master over an existing control SQLite DB."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")

    @contextmanager
    def _atomic(self) -> Iterator[None]:
        """BEGIN IMMEDIATE when not already in a transaction; else SAVEPOINT.

        Does not commit an outer caller transaction. Concurrent writers serialize
        via IMMEDIATE locks. Overlap checks and writes share one atomic unit.
        """
        outer = self._conn.in_transaction
        sp = None
        if outer:
            sp = "ref_store_sp"
            self._conn.execute(f"SAVEPOINT {sp}")
        else:
            self._conn.execute("BEGIN IMMEDIATE")
        try:
            yield
            if outer:
                self._conn.execute(f"RELEASE {sp}")
            else:
                self._conn.commit()
        except Exception:
            if outer:
                try:
                    self._conn.execute(f"ROLLBACK TO {sp}")
                    self._conn.execute(f"RELEASE {sp}")
                except sqlite3.Error:
                    pass
            else:
                self._conn.rollback()
            raise

    # ---- identity helpers -------------------------------------------------

    @staticmethod
    def venue_id_for(venue_code: str) -> str:
        return fingerprint("ven", {"venue_code": venue_code.strip().upper()})

    @staticmethod
    def asset_id_for(*, asset_class: AssetClass, identity_key: str) -> str:
        """Stable asset id from immutable caller identity material only.

        ``identity_key`` is opaque caller-supplied material (never mutable
        display metadata, never ticker text alone).
        """
        key = identity_key.strip()
        if not key:
            raise ReferenceValidationError(
                "identity_key is required; asset identity is never derived from display metadata or ticker text alone"
            )
        return fingerprint(
            "ast",
            {
                "asset_class": asset_class.value,
                "identity_key": key,
            },
        )

    @staticmethod
    def instrument_id_for(
        *,
        asset_id: str,
        venue_id: str,
        instrument_type: InstrumentType,
        salt: str,
    ) -> str:
        return fingerprint(
            "ins",
            {
                "asset_id": asset_id,
                "venue_id": venue_id,
                "instrument_type": instrument_type.value,
                "salt": salt,
            },
        )

    # ---- writes -----------------------------------------------------------

    def upsert_venue(
        self,
        *,
        venue_code: str,
        display_name: str,
        venue_type: VenueType,
        created_at: datetime | None = None,
    ) -> Venue:
        code = venue_code.strip().upper()
        if not code:
            raise ReferenceValidationError("venue_code must be non-empty")
        vid = self.venue_id_for(code)
        ts = ensure_utc(created_at or datetime.now(timezone.utc))
        try:
            with self._atomic():
                self._conn.execute(
                    "INSERT INTO ref_venue(venue_id, venue_code, display_name, venue_type, created_at) "
                    "VALUES (?, ?, ?, ?, ?) "
                    "ON CONFLICT(venue_id) DO UPDATE SET "
                    "display_name=excluded.display_name, venue_type=excluded.venue_type",
                    (vid, code, display_name, venue_type.value, dt_to_iso(ts)),
                )
        except sqlite3.IntegrityError as exc:
            raise ReferenceConflictError(
                "venue conflict",
                context={"venue_code": code, "error": str(exc)},
            ) from exc
        return Venue(vid, code, display_name, venue_type, ts)

    def register_asset(
        self,
        *,
        asset_class: AssetClass,
        display_name: str,
        identity_key: str,
        created_at: datetime | None = None,
    ) -> Asset:
        aid = self.asset_id_for(asset_class=asset_class, identity_key=identity_key)
        ts = ensure_utc(created_at or datetime.now(timezone.utc))
        try:
            with self._atomic():
                self._conn.execute(
                    "INSERT INTO ref_asset(asset_id, asset_class, display_name, created_at) "
                    "VALUES (?, ?, ?, ?)",
                    (aid, asset_class.value, display_name, dt_to_iso(ts)),
                )
        except sqlite3.IntegrityError as exc:
            raise ReferenceConflictError(
                "asset already registered",
                context={"asset_id": aid},
            ) from exc
        return Asset(aid, asset_class, display_name, ts)

    def register_instrument(
        self,
        *,
        asset_id: str,
        venue_id: str,
        instrument_type: InstrumentType,
        salt: str,
        base_asset_id: str | None = None,
        quote_asset_id: str | None = None,
        created_at: datetime | None = None,
    ) -> Instrument:
        if not salt.strip():
            raise ReferenceValidationError(
                "instrument salt is required; identities are never derived from ticker text alone"
            )
        self._require_asset(asset_id)
        self._require_venue(venue_id)
        if base_asset_id:
            self._require_asset(base_asset_id)
        if quote_asset_id:
            self._require_asset(quote_asset_id)
        iid = self.instrument_id_for(
            asset_id=asset_id,
            venue_id=venue_id,
            instrument_type=instrument_type,
            salt=salt,
        )
        ts = ensure_utc(created_at or datetime.now(timezone.utc))
        try:
            with self._atomic():
                self._conn.execute(
                    "INSERT INTO ref_instrument("
                    "instrument_id, asset_id, venue_id, instrument_type, "
                    "base_asset_id, quote_asset_id, created_at"
                    ") VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        iid,
                        asset_id,
                        venue_id,
                        instrument_type.value,
                        base_asset_id,
                        quote_asset_id,
                        dt_to_iso(ts),
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise ReferenceConflictError(
                "instrument already registered",
                context={"instrument_id": iid},
            ) from exc
        return Instrument(
            iid, asset_id, venue_id, instrument_type, ts, base_asset_id, quote_asset_id
        )

    def add_instrument_version(
        self,
        *,
        instrument_id: str,
        version_seq: int,
        contract_spec: Mapping[str, Any],
        window: BiTemporalWindow,
        supersedes_version_id: str | None = None,
        evidence: Mapping[str, Any] | None = None,
    ) -> InstrumentVersion:
        self._require_instrument(instrument_id)
        if version_seq < 1:
            raise ReferenceValidationError("version_seq must be >= 1")
        vid = fingerprint(
            "iv",
            {
                "instrument_id": instrument_id,
                "version_seq": version_seq,
                "valid_from": dt_to_iso(window.valid_from),
            },
        )
        if supersedes_version_id is not None:
            self._require_instrument_version(supersedes_version_id, instrument_id)
        try:
            with self._atomic():
                self._assert_no_valid_overlap(
                    table="ref_instrument_version",
                    id_col="instrument_id",
                    id_val=instrument_id,
                    window=window,
                )
                self._conn.execute(
                    "INSERT INTO ref_instrument_version("
                    "instrument_version_id, instrument_id, version_seq, contract_spec_json, "
                    "valid_from, valid_to, known_from, known_to, supersedes_version_id, evidence_json"
                    ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        vid,
                        instrument_id,
                        version_seq,
                        _json_dumps(dict(contract_spec)),
                        dt_to_iso(window.valid_from),
                        dt_to_iso(window.valid_to) if window.valid_to else None,
                        dt_to_iso(window.known_from),
                        dt_to_iso(window.known_to) if window.known_to else None,
                        supersedes_version_id,
                        _json_dumps(dict(evidence or {})),
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise ReferenceConflictError(
                "instrument version conflict",
                context={"instrument_id": instrument_id, "version_seq": version_seq},
            ) from exc
        return InstrumentVersion(
            vid,
            instrument_id,
            version_seq,
            dict(contract_spec),
            window,
            supersedes_version_id,
            dict(evidence or {}),
        )

    def add_alias(
        self,
        *,
        alias_text: str,
        target_kind: TargetKind,
        target_id: str,
        window: BiTemporalWindow,
        venue_id: str | None = None,
        confidence: float = 1.0,
        evidence: Mapping[str, Any] | None = None,
        is_primary: bool = False,
    ) -> AliasRecord:
        text = alias_text.strip()
        if not text:
            raise ReferenceValidationError("alias_text must be non-empty")
        if not (0.0 <= confidence <= 1.0):
            raise ReferenceValidationError("confidence must be in [0, 1]")
        norm = normalize_alias(text)
        self._assert_target_exists(target_kind, target_id)
        if venue_id is not None:
            self._require_venue(venue_id)
        # Reject silent collisions: same norm+venue with overlapping both windows
        # pointing at a different target.
        aid = fingerprint(
            "als",
            {
                "alias_text_norm": norm,
                "venue_id": venue_id,
                "target_kind": target_kind.value,
                "target_id": target_id,
                "valid_from": dt_to_iso(window.valid_from),
                "known_from": dt_to_iso(window.known_from),
            },
        )
        try:
            with self._atomic():
                self._assert_no_alias_collision(norm, venue_id, window, target_kind, target_id)
                self._conn.execute(
                    "INSERT INTO ref_alias("
                    "alias_id, alias_text, alias_text_norm, venue_id, target_kind, target_id, "
                    "valid_from, valid_to, known_from, known_to, confidence, evidence_json, is_primary"
                    ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        aid,
                        text,
                        norm,
                        venue_id,
                        target_kind.value,
                        target_id,
                        dt_to_iso(window.valid_from),
                        dt_to_iso(window.valid_to) if window.valid_to else None,
                        dt_to_iso(window.known_from),
                        dt_to_iso(window.known_to) if window.known_to else None,
                        confidence,
                        _json_dumps(dict(evidence or {})),
                        1 if is_primary else 0,
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise ReferenceConflictError(
                "alias insert conflict",
                context={"alias_text": text},
            ) from exc
        return AliasRecord(
            aid,
            text,
            norm,
            target_kind,
            target_id,
            window,
            venue_id,
            confidence,
            dict(evidence or {}),
            is_primary,
        )

    def add_listing_event(
        self,
        *,
        instrument_id: str,
        venue_id: str,
        event_type: ListingEventType,
        window: BiTemporalWindow,
        evidence: Mapping[str, Any] | None = None,
    ) -> ListingEvent:
        self._require_instrument(instrument_id)
        self._require_venue(venue_id)
        instr_venue = self._conn.execute(
            "SELECT venue_id FROM ref_instrument WHERE instrument_id = ?",
            (instrument_id,),
        ).fetchone()
        if instr_venue is None or instr_venue["venue_id"] != venue_id:
            raise ReferenceValidationError(
                "listing venue must match instrument venue",
                context={
                    "instrument_id": instrument_id,
                    "listing_venue_id": venue_id,
                    "instrument_venue_id": None if instr_venue is None else instr_venue["venue_id"],
                },
            )
        eid = fingerprint(
            "lst",
            {
                "instrument_id": instrument_id,
                "venue_id": venue_id,
                "event_type": event_type.value,
                "valid_from": dt_to_iso(window.valid_from),
                "known_from": dt_to_iso(window.known_from),
            },
        )
        with self._atomic():
            self._conn.execute(
                "INSERT INTO ref_listing_event("
                "listing_event_id, instrument_id, venue_id, event_type, "
                "valid_from, valid_to, known_from, known_to, evidence_json"
                ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    eid,
                    instrument_id,
                    venue_id,
                    event_type.value,
                    dt_to_iso(window.valid_from),
                    dt_to_iso(window.valid_to) if window.valid_to else None,
                    dt_to_iso(window.known_from),
                    dt_to_iso(window.known_to) if window.known_to else None,
                    _json_dumps(dict(evidence or {})),
                ),
            )
        return ListingEvent(
            eid,
            instrument_id,
            venue_id,
            event_type,
            window,
            dict(evidence or {}),
        )

    def add_migration_event(
        self,
        *,
        event_type: MigrationEventType,
        from_kind: TargetKind,
        from_id: str,
        to_kind: TargetKind,
        to_id: str,
        window: BiTemporalWindow,
        ratio_num: float | None = None,
        ratio_den: float | None = None,
        evidence: Mapping[str, Any] | None = None,
    ) -> MigrationEvent:
        self._assert_target_exists(from_kind, from_id)
        self._assert_target_exists(to_kind, to_id)
        if (ratio_num is None) ^ (ratio_den is None):
            raise ReferenceValidationError("ratio_num and ratio_den must both be set or both null")
        if ratio_den is not None and ratio_den == 0:
            raise ReferenceValidationError("ratio_den must be non-zero")
        mid = fingerprint(
            "mig",
            {
                "event_type": event_type.value,
                "from_kind": from_kind.value,
                "from_id": from_id,
                "to_kind": to_kind.value,
                "to_id": to_id,
                "valid_from": dt_to_iso(window.valid_from),
                "known_from": dt_to_iso(window.known_from),
            },
        )
        with self._atomic():
            self._conn.execute(
                "INSERT INTO ref_migration_event("
                "migration_event_id, event_type, from_kind, from_id, to_kind, to_id, "
                "ratio_num, ratio_den, valid_from, valid_to, known_from, known_to, evidence_json"
                ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    mid,
                    event_type.value,
                    from_kind.value,
                    from_id,
                    to_kind.value,
                    to_id,
                    ratio_num,
                    ratio_den,
                    dt_to_iso(window.valid_from),
                    dt_to_iso(window.valid_to) if window.valid_to else None,
                    dt_to_iso(window.known_from),
                    dt_to_iso(window.known_to) if window.known_to else None,
                    _json_dumps(dict(evidence or {})),
                ),
            )
        return MigrationEvent(
            mid,
            event_type,
            from_kind,
            from_id,
            to_kind,
            to_id,
            window,
            ratio_num,
            ratio_den,
            dict(evidence or {}),
        )

    def queue_ambiguity(
        self,
        *,
        alias_text: str,
        decision_time: datetime,
        knowledge_time: datetime,
        candidates: Sequence[Mapping[str, Any]],
        venue_id: str | None = None,
    ) -> AmbiguityCase:
        """Idempotent: same norm/venue/decision/knowledge returns existing QUEUED case."""
        text = alias_text.strip()
        norm = normalize_alias(text)
        d = ensure_utc(decision_time)
        k = ensure_utc(knowledge_time)
        now = datetime.now(timezone.utc)
        # Idempotency key excludes candidate ordering noise
        cid = fingerprint(
            "amb",
            {
                "alias_text_norm": norm,
                "venue_id": venue_id,
                "decision_time": dt_to_iso(d),
                "knowledge_time": dt_to_iso(k),
            },
        )
        with self._atomic():
            existing = self._conn.execute(
                "SELECT * FROM ref_ambiguity_case WHERE case_id = ?",
                (cid,),
            ).fetchone()
            if existing is not None:
                return self._row_to_ambiguity(existing)
            self._conn.execute(
                "INSERT INTO ref_ambiguity_case("
                "case_id, alias_text, alias_text_norm, venue_id, decision_time, knowledge_time, "
                "status, candidate_json, created_at, updated_at"
                ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    cid,
                    text,
                    norm,
                    venue_id,
                    dt_to_iso(d),
                    dt_to_iso(k),
                    AmbiguityStatus.QUEUED.value,
                    _json_dumps({"candidates": list(candidates)}),
                    dt_to_iso(now),
                    dt_to_iso(now),
                ),
            )
        return AmbiguityCase(
            cid,
            text,
            norm,
            d,
            k,
            AmbiguityStatus.QUEUED,
            list(candidates),
            now,
            now,
            venue_id,
        )

    def resolve_ambiguity_case(
        self,
        case_id: str,
        *,
        target_kind: TargetKind,
        target_id: str,
        resolution_note: str | None = None,
        status: AmbiguityStatus = AmbiguityStatus.RESOLVED,
    ) -> AmbiguityCase:
        """Typed manual resolution transition with validated target lineage."""
        if status not in (AmbiguityStatus.RESOLVED, AmbiguityStatus.REJECTED, AmbiguityStatus.DEFERRED):
            raise ReferenceResolutionError(
                "invalid resolution status transition",
                context={"status": status.value},
            )
        if status is AmbiguityStatus.RESOLVED:
            self._assert_target_exists(target_kind, target_id)
        now = datetime.now(timezone.utc)
        with self._atomic():
            row = self._conn.execute(
                "SELECT * FROM ref_ambiguity_case WHERE case_id = ?",
                (case_id,),
            ).fetchone()
            if row is None:
                raise ReferenceNotFoundError(
                    "ambiguity case not found", context={"case_id": case_id}
                )
            if row["status"] != AmbiguityStatus.QUEUED.value:
                raise ReferenceResolutionError(
                    "only QUEUED cases can be transitioned",
                    context={"case_id": case_id, "status": row["status"]},
                )
            self._conn.execute(
                "UPDATE ref_ambiguity_case SET "
                "status = ?, resolution_target_kind = ?, resolution_target_id = ?, "
                "resolution_note = ?, updated_at = ? "
                "WHERE case_id = ?",
                (
                    status.value,
                    target_kind.value if status is AmbiguityStatus.RESOLVED else None,
                    target_id if status is AmbiguityStatus.RESOLVED else None,
                    resolution_note,
                    dt_to_iso(now),
                    case_id,
                ),
            )
            row2 = self._conn.execute(
                "SELECT * FROM ref_ambiguity_case WHERE case_id = ?",
                (case_id,),
            ).fetchone()
        assert row2 is not None
        return self._row_to_ambiguity(row2)

    def supersede_alias(
        self,
        alias_id: str,
        *,
        close_known_at: datetime,
        new_alias_text: str | None = None,
        new_target_kind: TargetKind | None = None,
        new_target_id: str | None = None,
        new_window: BiTemporalWindow | None = None,
        new_confidence: float | None = None,
        new_evidence: Mapping[str, Any] | None = None,
    ) -> AliasRecord:
        """Atomic knowledge-time correction: close prior known_to, insert replacement.

        Historical as-of queries with knowledge_time before close_known_at still
        see the prior row; later knowledge sees the replacement.
        """
        close_at = ensure_utc(close_known_at)
        with self._atomic():
            row = self._conn.execute(
                "SELECT * FROM ref_alias WHERE alias_id = ?", (alias_id,)
            ).fetchone()
            if row is None:
                raise ReferenceNotFoundError(
                    "alias not found", context={"alias_id": alias_id}
                )
            prior = self._row_to_alias(row)
            if prior.window.known_to is not None:
                raise ReferenceConflictError(
                    "alias already closed for knowledge time",
                    context={"alias_id": alias_id, "known_to": dt_to_iso(prior.window.known_to)},
                )
            if close_at <= prior.window.known_from:
                raise ReferenceValidationError(
                    "close_known_at must be > prior known_from",
                    context={"close_known_at": dt_to_iso(close_at)},
                )
            # Close prior open known_to
            self._conn.execute(
                "UPDATE ref_alias SET known_to = ? WHERE alias_id = ?",
                (dt_to_iso(close_at), alias_id),
            )
            # Build replacement
            text = (new_alias_text or prior.alias_text).strip()
            norm = normalize_alias(text)
            tkind = new_target_kind or prior.target_kind
            tid = new_target_id or prior.target_id
            self._assert_target_exists(tkind, tid)
            if new_window is not None:
                window = new_window
            else:
                window = BiTemporalWindow(
                    valid_from=prior.window.valid_from,
                    valid_to=prior.window.valid_to,
                    known_from=close_at,
                    known_to=None,
                )
            conf = prior.confidence if new_confidence is None else new_confidence
            evid = dict(new_evidence) if new_evidence is not None else dict(prior.evidence)
            evid = {**evid, "supersedes_alias_id": alias_id}
            self._assert_no_alias_collision(norm, prior.venue_id, window, tkind, tid)
            new_id = fingerprint(
                "als",
                {
                    "alias_text_norm": norm,
                    "venue_id": prior.venue_id,
                    "target_kind": tkind.value,
                    "target_id": tid,
                    "valid_from": dt_to_iso(window.valid_from),
                    "known_from": dt_to_iso(window.known_from),
                },
            )
            self._conn.execute(
                "INSERT INTO ref_alias("
                "alias_id, alias_text, alias_text_norm, venue_id, target_kind, target_id, "
                "valid_from, valid_to, known_from, known_to, confidence, evidence_json, is_primary"
                ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    new_id,
                    text,
                    norm,
                    prior.venue_id,
                    tkind.value,
                    tid,
                    dt_to_iso(window.valid_from),
                    dt_to_iso(window.valid_to) if window.valid_to else None,
                    dt_to_iso(window.known_from),
                    dt_to_iso(window.known_to) if window.known_to else None,
                    conf,
                    _json_dumps(evid),
                    1 if prior.is_primary else 0,
                ),
            )
        return AliasRecord(
            new_id,
            text,
            norm,
            tkind,
            tid,
            window,
            prior.venue_id,
            conf,
            evid,
            prior.is_primary,
        )

    # ---- as-of resolution -------------------------------------------------

    def resolve_alias(
        self,
        alias_text: str,
        *,
        decision_time: datetime,
        knowledge_time: datetime,
        venue_id: str | None = None,
        queue_if_ambiguous: bool = True,
    ) -> ResolutionResult:
        """Resolve alias at decision_time under knowledge_time (both required)."""
        d = ensure_utc(decision_time)
        k = ensure_utc(knowledge_time)
        text = alias_text.strip()
        norm = normalize_alias(text)
        pred = _window_active_sql("valid_from", "valid_to", "known_from", "known_to")
        params: dict[str, Any] = {
            "norm": norm,
            "decision_time": dt_to_iso(d),
            "knowledge_time": dt_to_iso(k),
        }
        if venue_id is None:
            sql = (
                f"SELECT * FROM ref_alias WHERE alias_text_norm = :norm "
                f"AND venue_id IS NULL AND {pred} "
                f"ORDER BY confidence DESC, alias_id ASC"
            )
        else:
            sql = (
                f"SELECT * FROM ref_alias WHERE alias_text_norm = :norm "
                f"AND (venue_id = :venue_id OR venue_id IS NULL) AND {pred} "
                f"ORDER BY "
                f"CASE WHEN venue_id = :venue_id THEN 0 ELSE 1 END, "
                f"confidence DESC, alias_id ASC"
            )
            params["venue_id"] = venue_id
        rows = list(self._conn.execute(sql, params))
        records = tuple(self._row_to_alias(r) for r in rows)
        if not records:
            return ResolutionResult(
                outcome=ResolutionOutcome.UNRESOLVED,
                alias_text=text,
                alias_text_norm=norm,
                decision_time=d,
                knowledge_time=k,
                evidence={"reason": "no_active_alias"},
            )
        # Distinct targets among active matches
        targets = {(r.target_kind, r.target_id) for r in records}
        if len(targets) == 1:
            best = records[0]
            return ResolutionResult(
                outcome=ResolutionOutcome.RESOLVED,
                alias_text=text,
                alias_text_norm=norm,
                decision_time=d,
                knowledge_time=k,
                target_kind=best.target_kind,
                target_id=best.target_id,
                confidence=best.confidence,
                candidates=records,
                evidence=dict(best.evidence),
            )
        # Ambiguous — optional queue
        case_id = None
        outcome = ResolutionOutcome.AMBIGUOUS
        if queue_if_ambiguous:
            case = self.queue_ambiguity(
                alias_text=text,
                decision_time=d,
                knowledge_time=k,
                candidates=[
                    {
                        "alias_id": r.alias_id,
                        "target_kind": r.target_kind.value,
                        "target_id": r.target_id,
                        "confidence": r.confidence,
                    }
                    for r in records
                ],
                venue_id=venue_id,
            )
            case_id = case.case_id
            outcome = ResolutionOutcome.QUEUED
        return ResolutionResult(
            outcome=outcome,
            alias_text=text,
            alias_text_norm=norm,
            decision_time=d,
            knowledge_time=k,
            candidates=records,
            case_id=case_id,
            evidence={"reason": "multiple_targets", "target_count": len(targets)},
        )

    def instrument_version_as_of(
        self,
        instrument_id: str,
        *,
        decision_time: datetime,
        knowledge_time: datetime,
    ) -> InstrumentVersion | None:
        d = ensure_utc(decision_time)
        k = ensure_utc(knowledge_time)
        pred = _window_active_sql("valid_from", "valid_to", "known_from", "known_to")
        row = self._conn.execute(
            f"SELECT * FROM ref_instrument_version "
            f"WHERE instrument_id = :iid AND {pred} "
            f"ORDER BY version_seq DESC LIMIT 1",
            {
                "iid": instrument_id,
                "decision_time": dt_to_iso(d),
                "knowledge_time": dt_to_iso(k),
            },
        ).fetchone()
        if row is None:
            return None
        return self._row_to_instr_version(row)

    # ---- internals --------------------------------------------------------

    def _require_venue(self, venue_id: str) -> None:
        row = self._conn.execute(
            "SELECT 1 FROM ref_venue WHERE venue_id = ?", (venue_id,)
        ).fetchone()
        if row is None:
            raise ReferenceNotFoundError("venue not found", context={"venue_id": venue_id})

    def _require_asset(self, asset_id: str) -> None:
        row = self._conn.execute(
            "SELECT 1 FROM ref_asset WHERE asset_id = ?", (asset_id,)
        ).fetchone()
        if row is None:
            raise ReferenceNotFoundError("asset not found", context={"asset_id": asset_id})

    def _require_instrument(self, instrument_id: str) -> None:
        row = self._conn.execute(
            "SELECT 1 FROM ref_instrument WHERE instrument_id = ?", (instrument_id,)
        ).fetchone()
        if row is None:
            raise ReferenceNotFoundError(
                "instrument not found", context={"instrument_id": instrument_id}
            )

    def _require_instrument_version(
        self, version_id: str, instrument_id: str
    ) -> None:
        row = self._conn.execute(
            "SELECT 1 FROM ref_instrument_version "
            "WHERE instrument_version_id = ? AND instrument_id = ?",
            (version_id, instrument_id),
        ).fetchone()
        if row is None:
            raise ReferenceNotFoundError(
                "instrument version not found",
                context={"instrument_version_id": version_id, "instrument_id": instrument_id},
            )

    def _assert_target_exists(self, kind: TargetKind, target_id: str) -> None:
        if kind is TargetKind.VENUE:
            self._require_venue(target_id)
        elif kind is TargetKind.ASSET:
            self._require_asset(target_id)
        elif kind is TargetKind.INSTRUMENT:
            self._require_instrument(target_id)
        else:
            raise ReferenceValidationError(f"unknown target kind {kind}")

    def _assert_no_valid_overlap(
        self,
        *,
        table: str,
        id_col: str,
        id_val: str,
        window: BiTemporalWindow,
    ) -> None:
        """Reject overlapping valid-time for same entity when known windows also overlap."""
        vf = dt_to_iso(window.valid_from)
        vt = dt_to_iso(window.valid_to) if window.valid_to else None
        kf = dt_to_iso(window.known_from)
        kt = dt_to_iso(window.known_to) if window.known_to else None
        # valid overlap AND known overlap
        sql = f"""
            SELECT 1 FROM {table}
            WHERE {id_col} = ?
              AND valid_from < COALESCE(?, '9999-12-31T00:00:00Z')
              AND COALESCE(valid_to, '9999-12-31T00:00:00Z') > ?
              AND known_from < COALESCE(?, '9999-12-31T00:00:00Z')
              AND COALESCE(known_to, '9999-12-31T00:00:00Z') > ?
            LIMIT 1
        """
        row = self._conn.execute(sql, (id_val, vt, vf, kt, kf)).fetchone()
        if row is not None:
            raise ReferenceConflictError(
                "overlapping active version windows",
                context={id_col: id_val, "valid_from": vf},
            )

    def _assert_no_alias_collision(
        self,
        norm: str,
        venue_id: str | None,
        window: BiTemporalWindow,
        target_kind: TargetKind,
        target_id: str,
    ) -> None:
        vf = dt_to_iso(window.valid_from)
        vt = dt_to_iso(window.valid_to) if window.valid_to else None
        kf = dt_to_iso(window.known_from)
        kt = dt_to_iso(window.known_to) if window.known_to else None
        if venue_id is None:
            venue_pred = "venue_id IS NULL"
            params: list[Any] = [norm, vt, vf, kt, kf]
        else:
            venue_pred = "(venue_id = ? OR venue_id IS NULL)"
            params = [norm, venue_id, vt, vf, kt, kf]
        sql = f"""
            SELECT alias_id, target_kind, target_id FROM ref_alias
            WHERE alias_text_norm = ?
              AND {venue_pred}
              AND valid_from < COALESCE(?, '9999-12-31T00:00:00Z')
              AND COALESCE(valid_to, '9999-12-31T00:00:00Z') > ?
              AND known_from < COALESCE(?, '9999-12-31T00:00:00Z')
              AND COALESCE(known_to, '9999-12-31T00:00:00Z') > ?
        """
        for row in self._conn.execute(sql, params):
            if row["target_kind"] != target_kind.value or row["target_id"] != target_id:
                raise ReferenceConflictError(
                    "silent alias collision with different target",
                    context={
                        "alias_text_norm": norm,
                        "existing_alias_id": row["alias_id"],
                        "existing_target": f"{row['target_kind']}:{row['target_id']}",
                        "new_target": f"{target_kind.value}:{target_id}",
                    },
                )

    def _row_to_alias(self, row: sqlite3.Row) -> AliasRecord:
        window = BiTemporalWindow(
            valid_from=iso_to_dt(row["valid_from"]),
            valid_to=iso_to_dt(row["valid_to"]) if row["valid_to"] else None,
            known_from=iso_to_dt(row["known_from"]),
            known_to=iso_to_dt(row["known_to"]) if row["known_to"] else None,
        )
        return AliasRecord(
            alias_id=row["alias_id"],
            alias_text=row["alias_text"],
            alias_text_norm=row["alias_text_norm"],
            target_kind=TargetKind(row["target_kind"]),
            target_id=row["target_id"],
            window=window,
            venue_id=row["venue_id"],
            confidence=float(row["confidence"]),
            evidence=_json_loads(row["evidence_json"]),
            is_primary=bool(row["is_primary"]),
        )

    def _row_to_ambiguity(self, row: sqlite3.Row) -> AmbiguityCase:
        return AmbiguityCase(
            case_id=row["case_id"],
            alias_text=row["alias_text"],
            alias_text_norm=row["alias_text_norm"],
            decision_time=iso_to_dt(row["decision_time"]),
            knowledge_time=iso_to_dt(row["knowledge_time"]),
            status=AmbiguityStatus(row["status"]),
            candidates=_json_loads(row["candidate_json"]).get("candidates", []),
            created_at=iso_to_dt(row["created_at"]),
            updated_at=iso_to_dt(row["updated_at"]),
            venue_id=row["venue_id"],
            resolution_target_kind=(
                TargetKind(row["resolution_target_kind"])
                if row["resolution_target_kind"] is not None
                else None
            ),
            resolution_target_id=row["resolution_target_id"],
            resolution_note=row["resolution_note"],
        )

    def _row_to_instr_version(self, row: sqlite3.Row) -> InstrumentVersion:
        window = BiTemporalWindow(
            valid_from=iso_to_dt(row["valid_from"]),
            valid_to=iso_to_dt(row["valid_to"]) if row["valid_to"] else None,
            known_from=iso_to_dt(row["known_from"]),
            known_to=iso_to_dt(row["known_to"]) if row["known_to"] else None,
        )
        return InstrumentVersion(
            instrument_version_id=row["instrument_version_id"],
            instrument_id=row["instrument_id"],
            version_seq=int(row["version_seq"]),
            contract_spec=_json_loads(row["contract_spec_json"]),
            window=window,
            supersedes_version_id=row["supersedes_version_id"],
            evidence=_json_loads(row["evidence_json"]),
        )
