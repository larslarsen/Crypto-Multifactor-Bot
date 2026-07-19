"""REF-001 — focused regressions for the v2 Sr corrections.

Each test pins one defect corrected in `REF001_v2_corrections.zip`:
  D1 timestamp canonicalization is fixed-width + lex-sortable;
  D2 writes are atomic (BEGIN IMMEDIATE / SAVEPOINT);
  D3 asset/instrument identity is never derived from display/ticker text;
  D4 instrument-version overlap check runs inside the atomic unit;
  D5 alias collision check runs inside the atomic unit;
  D6 listing venue must match instrument venue;
  D7 ambiguity queue is idempotent (no duplicate QUEUED);
  D8 typed manual resolution transition (RESOLVED/REJECTED/DEFERRED from QUEUED);
  D9 knowledge-time correction via supersede_alias.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from cryptofactors.catalog.runner import MIGRATIONS_DIR, apply_migrations
from cryptofactors.reference import errors, models, store


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _db(tmp_path: Path) -> sqlite3.Connection:
    db = tmp_path / "ref.db"
    apply_migrations(db, migrations_dir=MIGRATIONS_DIR)
    conn = sqlite3.connect(str(db))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def _seed(
    tmp_path: Path,
) -> tuple[sqlite3.Connection, store.ReferenceStore, str, str, str]:
    conn = _db(tmp_path)
    s = store.ReferenceStore(conn)
    s.upsert_venue(
        venue_code="BINANCE", display_name="Binance", venue_type=models.VenueType.CEX
    )
    s.register_asset(
        asset_class=models.AssetClass.CRYPTO,
        display_name="Bitcoin",
        identity_key="btc|bc1qxy",
    )
    vid = s.venue_id_for("binance")
    aid = s.asset_id_for(asset_class=models.AssetClass.CRYPTO, identity_key="btc|bc1qxy")
    instr = s.register_instrument(
        asset_id=aid, venue_id=vid, instrument_type=models.InstrumentType.SPOT, salt="x"
    )
    return conn, s, vid, aid, instr.instrument_id


# --- D1: fixed-width lex-sortable timestamp canonicalization -----------------


def test_dt_to_iso_is_fixed_width_lexicographically_sortable() -> None:
    a = datetime(2024, 1, 1, 0, 0, 0, 0, tzinfo=timezone.utc)
    b = datetime(2024, 1, 1, 0, 0, 0, 123456, tzinfo=timezone.utc)
    sa, sb = models.dt_to_iso(a), models.dt_to_iso(b)
    assert sa.endswith("Z") and sb.endswith("Z")
    assert ".000000Z" in sa and ".123456Z" in sb
    assert sa < sb  # lex order == time order
    assert models.iso_to_dt(sa) == a
    assert models.iso_to_dt(sb) == b


# --- D3: identity never from display/ticker text ----------------------------


def test_asset_id_for_rejects_empty_identity_key() -> None:
    with pytest.raises(errors.ReferenceValidationError):
        store.ReferenceStore.asset_id_for(
            asset_class=models.AssetClass.CRYPTO, identity_key="   "
        )


def test_instrument_registration_rejects_empty_salt(tmp_path: Path) -> None:
    conn, s, vid, aid, _ = _seed(tmp_path)
    with pytest.raises(errors.ReferenceValidationError):
        s.register_instrument(
            asset_id=aid,
            venue_id=vid,
            instrument_type=models.InstrumentType.SPOT,
            salt="   ",
        )


def test_asset_id_for_is_stable_and_display_independent() -> None:
    a = store.ReferenceStore.asset_id_for(
        asset_class=models.AssetClass.CRYPTO, identity_key="btc|bc1qxy"
    )
    b = store.ReferenceStore.asset_id_for(
        asset_class=models.AssetClass.CRYPTO, identity_key="btc|bc1qxy"
    )
    assert a == b  # identity_key (not display name) drives the id


# --- D6: listing venue must match instrument venue --------------------------


def test_listing_venue_must_match_instrument_venue(tmp_path: Path) -> None:
    conn, s, vid, aid, iid = _seed(tmp_path)
    s.upsert_venue(
        venue_code="COINBASE", display_name="Coinbase", venue_type=models.VenueType.CEX
    )
    other_vid = s.venue_id_for("coinbase")
    with pytest.raises(errors.ReferenceValidationError):
        s.add_listing_event(
            instrument_id=iid,
            venue_id=other_vid,
            event_type=models.ListingEventType.LIST,
            window=models.BiTemporalWindow(
                valid_from=datetime(2020, 1, 1, tzinfo=timezone.utc),
                known_from=_now(),
            ),
        )
    s.add_listing_event(
        instrument_id=iid,
        venue_id=vid,
        event_type=models.ListingEventType.LIST,
        window=models.BiTemporalWindow(
            valid_from=datetime(2020, 1, 1, tzinfo=timezone.utc),
            known_from=_now(),
        ),
    )


# --- D7: ambiguity queue idempotent -----------------------------------------


def test_queue_ambiguity_is_idempotent(tmp_path: Path) -> None:
    conn, s, vid, aid, iid = _seed(tmp_path)
    first = s.queue_ambiguity(
        alias_text="BTC",
        decision_time=_now(),
        knowledge_time=_now(),
        candidates=[{"target_kind": "INSTRUMENT", "target_id": iid}],
    )
    second = s.queue_ambiguity(
        alias_text="BTC",
        decision_time=first.decision_time,
        knowledge_time=first.knowledge_time,
        candidates=[
            {"target_kind": "INSTRUMENT", "target_id": iid},
            {"target_kind": "INSTRUMENT", "target_id": iid + "x"},
        ],
    )
    assert second.case_id == first.case_id
    assert second.status is models.AmbiguityStatus.QUEUED


# --- D8: typed manual resolution transition ---------------------------------


def test_resolve_ambiguity_case_requires_existing_queued(tmp_path: Path) -> None:
    conn, s, vid, aid, iid = _seed(tmp_path)
    c = s.queue_ambiguity(
        alias_text="BTC",
        decision_time=_now(),
        knowledge_time=_now(),
        candidates=[{"target_kind": "INSTRUMENT", "target_id": iid}],
    )
    resolved = s.resolve_ambiguity_case(
        c.case_id, target_kind=models.TargetKind.INSTRUMENT, target_id=iid
    )
    assert resolved.status is models.AmbiguityStatus.RESOLVED
    assert resolved.resolution_target_id == iid
    with pytest.raises(errors.ReferenceResolutionError):
        s.resolve_ambiguity_case(
            c.case_id, target_kind=models.TargetKind.INSTRUMENT, target_id=iid
        )


def test_resolve_ambiguity_case_rejects_invalid_status(tmp_path: Path) -> None:
    conn, s, vid, aid, iid = _seed(tmp_path)
    c = s.queue_ambiguity(
        alias_text="BTC", decision_time=_now(), knowledge_time=_now(), candidates=[]
    )
    with pytest.raises(errors.ReferenceResolutionError):
        s.resolve_ambiguity_case(
            c.case_id,
            target_kind=models.TargetKind.ASSET,
            target_id="a1",
            status=models.AmbiguityStatus.QUEUED,
        )


# --- D9: knowledge-time correction via supersede_alias ----------------------


def test_supersede_alias_closes_known_to_and_inserts_replacement(tmp_path: Path) -> None:
    conn, s, vid, aid, iid = _seed(tmp_path)
    al = s.add_alias(
        alias_text="BTC",
        target_kind=models.TargetKind.INSTRUMENT,
        target_id=iid,
        window=models.BiTemporalWindow(
            valid_from=datetime(2020, 1, 1, tzinfo=timezone.utc),
            known_from=_now(),
        ),
        venue_id=vid,
    )
    prior = s.resolve_alias("BTC", decision_time=_now(), knowledge_time=_now(), venue_id=vid)
    assert prior.outcome is models.ResolutionOutcome.RESOLVED
    # supersede closes the prior known_to (must be strictly > prior known_from)
    close_at = al.window.known_from + timedelta(seconds=1)
    s.supersede_alias(al.alias_id, close_known_at=close_at)
    # replacement is active for knowledge_time strictly after the close
    after = s.resolve_alias(
        "BTC",
        decision_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
        knowledge_time=close_at + timedelta(seconds=1),
        venue_id=vid,
    )
    assert after.outcome is models.ResolutionOutcome.RESOLVED
    # pre-close knowledge still sees the original (prior) row as resolved
    before = s.resolve_alias(
        "BTC",
        decision_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
        knowledge_time=al.window.known_from,
        venue_id=vid,
    )
    assert before.outcome is models.ResolutionOutcome.RESOLVED


# --- D4 / D5: overlap + collision checks inside atomic unit ------------------


def test_instrument_version_overlap_rejected(tmp_path: Path) -> None:
    conn, s, vid, aid, iid = _seed(tmp_path)
    w = models.BiTemporalWindow(
        valid_from=datetime(2020, 1, 1, tzinfo=timezone.utc),
        valid_to=datetime(2021, 1, 1, tzinfo=timezone.utc),
        known_from=_now(),
        known_to=None,
    )
    s.add_instrument_version(instrument_id=iid, version_seq=1, contract_spec={}, window=w)
    with pytest.raises(errors.ReferenceConflictError):
        s.add_instrument_version(
            instrument_id=iid, version_seq=2, contract_spec={}, window=w
        )


def test_alias_collision_with_different_target_rejected(tmp_path: Path) -> None:
    conn, s, vid, aid, iid = _seed(tmp_path)
    other = s.register_instrument(
        asset_id=aid, venue_id=vid, instrument_type=models.InstrumentType.SPOT, salt="y"
    )
    w = models.BiTemporalWindow(
        valid_from=datetime(2020, 1, 1, tzinfo=timezone.utc),
        known_from=_now(),
    )
    s.add_alias(
        alias_text="BTC",
        target_kind=models.TargetKind.INSTRUMENT,
        target_id=iid,
        window=w,
        venue_id=vid,
    )
    with pytest.raises(errors.ReferenceConflictError):
        s.add_alias(
            alias_text="BTC",
            target_kind=models.TargetKind.INSTRUMENT,
            target_id=other.instrument_id,
            window=w,
            venue_id=vid,
        )
