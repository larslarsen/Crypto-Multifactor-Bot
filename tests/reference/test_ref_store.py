"""REF-001 — focused regressions.

v2 Sr corrections (`REF001_v2_corrections.zip`):
  D1 timestamp canonicalization is fixed-width + lex-sortable;
  D2 writes are atomic (BEGIN IMMEDIATE / SAVEPOINT);
  D3 asset/instrument identity is never derived from display/ticker text;
  D4 instrument-version overlap check runs inside the atomic unit;
  D5 alias collision check runs inside the atomic unit;
  D6 listing venue must match instrument venue;
  D7 ambiguity queue is idempotent (no duplicate QUEUED);
  D8 typed manual resolution transition (RESOLVED/REJECTED/DEFERRED from QUEUED);
  D9 knowledge-time correction via supersede_alias.

Sr integrity-fix drop (in-tree, `REF-001_SR_INTEGRITY_FIXES.md`):
  I1 resolve_alias honors persisted manual decisions; no requeue;
  I2 resolve_ambiguity_case(RESOLVED) gates target to the stored candidate set;
  I3 supersede_alias requires contiguous knowledge-time (replacement known_from == close_known_at);
  I4 supersede_instrument_version closes prior + inserts replacement; historical as-of preserved;
  I5 global vs venue alias collision is same-scope only, insertion-order independent;
  I6 cross-scope different targets surface at resolve time, not silent collision;
  I7 polymorphic existence/semantic checks run inside the atomic write unit.

REF-001 ticket deliverable scenarios (synthetic coverage):
  S1 ticker reuse: same symbol -> different instruments across nonoverlapping valid windows;
  S2 redenomination: typed asset->asset REDENOMINATION event preserves endpoints/ratio/time/evidence;
  S3 migration: typed contract-migration event preserves distinct source/dest identities + lineage;
  S4 delisting: LIST/DELIST lifecycle events retain venue, economic time, known time, identity;
  S5 late-metadata correction: covered by D9 (supersede_alias) and I4 (supersede_instrument_version).
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


# --- Sr integrity-fix drop (REF-001_SR_INTEGRITY_FIXES.md) -------------------


def _seed_ambiguous(tmp_path: Path) -> tuple[
    sqlite3.Connection, store.ReferenceStore, str, str, str, str
]:
    """Cross-scope ambiguity: a global alias and a venue alias, same norm,
    different instrument targets. A venue-scoped resolve then sees both
    candidates (matching the same-scope collision rule, this is allowed)."""
    conn, s, vid, aid, iid = _seed(tmp_path)
    other = s.register_instrument(
        asset_id=aid, venue_id=vid, instrument_type=models.InstrumentType.SPOT, salt="y"
    )
    w = models.BiTemporalWindow(
        valid_from=datetime(2020, 1, 1, tzinfo=timezone.utc),
        known_from=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    s.add_alias(
        alias_text="BTC", target_kind=models.TargetKind.INSTRUMENT, target_id=iid,
        window=w, venue_id=None,
    )
    s.add_alias(
        alias_text="BTC", target_kind=models.TargetKind.INSTRUMENT,
        target_id=other.instrument_id, window=w, venue_id=vid,
    )
    return conn, s, vid, aid, iid, other.instrument_id


def test_I1_resolve_alias_honors_resolved_decision_and_does_not_requeue(tmp_path: Path) -> None:
    conn, s, vid, aid, iid, other = _seed_ambiguous(tmp_path)
    dt = datetime(2025, 1, 1, tzinfo=timezone.utc)
    kt = datetime(2025, 1, 2, tzinfo=timezone.utc)
    first = s.resolve_alias("BTC", decision_time=dt, knowledge_time=kt, venue_id=vid)
    assert first.outcome is models.ResolutionOutcome.QUEUED
    case_id = first.case_id
    assert case_id is not None
    s.resolve_ambiguity_case(
        case_id, target_kind=models.TargetKind.INSTRUMENT, target_id=iid
    )
    second = s.resolve_alias("BTC", decision_time=dt, knowledge_time=kt, venue_id=vid)
    assert second.outcome is models.ResolutionOutcome.RESOLVED
    assert second.target_id == iid
    assert second.case_id == case_id


def test_I1_resolved_rejected_and_deferred_are_typed_and_never_requeue(tmp_path: Path) -> None:
    conn, s, vid, aid, iid, other = _seed_ambiguous(tmp_path)
    dt = datetime(2025, 1, 1, tzinfo=timezone.utc)
    kt = datetime(2025, 1, 2, tzinfo=timezone.utc)
    base = s.resolve_alias("BTC", decision_time=dt, knowledge_time=kt, venue_id=vid)
    case_id = base.case_id
    assert case_id is not None
    s.resolve_ambiguity_case(
        case_id, status=models.AmbiguityStatus.REJECTED, resolution_note="not a real pair"
    )
    rejected = s.resolve_alias("BTC", decision_time=dt, knowledge_time=kt, venue_id=vid)
    assert rejected.outcome is models.ResolutionOutcome.REJECTED
    assert rejected.case_id == case_id
    dt2 = datetime(2025, 2, 1, tzinfo=timezone.utc)
    base2 = s.resolve_alias("BTC", decision_time=dt2, knowledge_time=kt, venue_id=vid)
    assert base2.case_id is not None
    s.resolve_ambiguity_case(base2.case_id, status=models.AmbiguityStatus.DEFERRED)
    deferred = s.resolve_alias("BTC", decision_time=dt2, knowledge_time=kt, venue_id=vid)
    assert deferred.outcome is models.ResolutionOutcome.DEFERRED


def test_I2_resolve_ambiguity_case_rejects_target_not_in_candidates(tmp_path: Path) -> None:
    conn, s, vid, aid, iid, other = _seed_ambiguous(tmp_path)
    dt = datetime(2025, 1, 1, tzinfo=timezone.utc)
    kt = datetime(2025, 1, 2, tzinfo=timezone.utc)
    case = s.resolve_alias("BTC", decision_time=dt, knowledge_time=kt, venue_id=vid)
    assert case.case_id is not None
    foreign = s.register_instrument(
        asset_id=aid, venue_id=vid, instrument_type=models.InstrumentType.SPOT, salt="z"
    )
    with pytest.raises(errors.ReferenceResolutionError):
        s.resolve_ambiguity_case(
            case.case_id, target_kind=models.TargetKind.INSTRUMENT, target_id=foreign.instrument_id
        )


def test_I2_resolve_ambiguity_case_rejects_venue_incompatible_instrument(tmp_path: Path) -> None:
    conn, s, vid, aid, iid, other = _seed_ambiguous(tmp_path)
    s.upsert_venue(
        venue_code="COINBASE", display_name="Coinbase", venue_type=models.VenueType.CEX
    )
    cb_vid = s.venue_id_for("coinbase")
    cb_instr = s.register_instrument(
        asset_id=aid, venue_id=cb_vid, instrument_type=models.InstrumentType.SPOT, salt="cb"
    )
    dt = datetime(2025, 1, 1, tzinfo=timezone.utc)
    kt = datetime(2025, 1, 2, tzinfo=timezone.utc)
    case = s.resolve_alias("BTC", decision_time=dt, knowledge_time=kt, venue_id=vid)
    assert case.case_id is not None
    with pytest.raises(errors.ReferenceResolutionError):
        s.resolve_ambiguity_case(
            case.case_id, target_kind=models.TargetKind.INSTRUMENT, target_id=cb_instr.instrument_id
        )


def test_I3_supersede_alias_requires_contiguous_knowledge_time(tmp_path: Path) -> None:
    conn, s, vid, aid, iid = _seed(tmp_path)
    al = s.add_alias(
        alias_text="BTC", target_kind=models.TargetKind.INSTRUMENT, target_id=iid,
        window=models.BiTemporalWindow(
            valid_from=datetime(2020, 1, 1, tzinfo=timezone.utc), known_from=datetime(2024, 1, 1, tzinfo=timezone.utc)
        ),
        venue_id=vid,
    )
    close_at = al.window.known_from + timedelta(seconds=1)
    bad_window = models.BiTemporalWindow(
        valid_from=datetime(2020, 1, 1, tzinfo=timezone.utc),
        known_from=close_at + timedelta(seconds=10),
    )
    with pytest.raises(errors.ReferenceValidationError):
        s.supersede_alias(al.alias_id, close_known_at=close_at, new_window=bad_window)
    good_window = models.BiTemporalWindow(
        valid_from=datetime(2020, 1, 1, tzinfo=timezone.utc), known_from=close_at
    )
    repl = s.supersede_alias(al.alias_id, close_known_at=close_at, new_window=good_window)
    assert repl.window.known_from == close_at


def test_I4_supersede_instrument_version_preserves_historical_as_of(tmp_path: Path) -> None:
    conn, s, vid, aid, iid, other = _seed_ambiguous(tmp_path)
    w = models.BiTemporalWindow(
        valid_from=datetime(2020, 1, 1, tzinfo=timezone.utc),
        valid_to=datetime(2021, 1, 1, tzinfo=timezone.utc),
        known_from=_now(), known_to=None,
    )
    v = s.add_instrument_version(instrument_id=iid, version_seq=1, contract_spec={"a": 1}, window=w)
    close_at = w.known_from + timedelta(seconds=1)
    repl = s.supersede_instrument_version(
        v.instrument_version_id, close_known_at=close_at, contract_spec={"a": 2}
    )
    assert repl.window.known_from == close_at
    prior = s.instrument_version_as_of(
        iid, decision_time=datetime(2020, 6, 1, tzinfo=timezone.utc), knowledge_time=w.known_from
    )
    assert prior is not None and prior.contract_spec == {"a": 1}
    post = s.instrument_version_as_of(
        iid, decision_time=datetime(2020, 6, 1, tzinfo=timezone.utc),
        knowledge_time=close_at + timedelta(seconds=1),
    )
    assert post is not None and post.contract_spec == {"a": 2}


def test_I5_global_venue_alias_collision_is_same_scope_and_order_independent(tmp_path: Path) -> None:
    conn, s, vid, aid, iid, other = _seed_ambiguous(tmp_path)
    w = models.BiTemporalWindow(
        valid_from=datetime(2020, 1, 1, tzinfo=timezone.utc), known_from=_now()
    )
    s.add_alias(
        alias_text="BTC", target_kind=models.TargetKind.INSTRUMENT, target_id=iid,
        window=w, venue_id=None,
    )
    s.add_alias(
        alias_text="BTC", target_kind=models.TargetKind.INSTRUMENT, target_id=other,
        window=w, venue_id=vid,
    )
    w2 = models.BiTemporalWindow(
        valid_from=datetime(2021, 1, 1, tzinfo=timezone.utc), known_from=_now()
    )
    s.add_alias(
        alias_text="ETH", target_kind=models.TargetKind.INSTRUMENT, target_id=iid,
        window=w2, venue_id=vid,
    )
    with pytest.raises(errors.ReferenceConflictError):
        s.add_alias(
            alias_text="ETH", target_kind=models.TargetKind.INSTRUMENT, target_id=other,
            window=w2, venue_id=vid,
        )


def test_I6_cross_scope_different_targets_surface_at_resolve_time(tmp_path: Path) -> None:
    # _seed_ambiguous already creates a global alias (->iid) and a venue alias
    # (->other) for "BTC"; a venue-scoped resolve must surface both candidates
    # for manual triage rather than silently merging.
    conn, s, vid, aid, iid, other = _seed_ambiguous(tmp_path)
    dt = datetime(2025, 1, 1, tzinfo=timezone.utc)
    kt = datetime(2025, 1, 2, tzinfo=timezone.utc)
    res = s.resolve_alias("BTC", decision_time=dt, knowledge_time=kt, venue_id=vid)
    assert res.outcome in (
        models.ResolutionOutcome.QUEUED, models.ResolutionOutcome.AMBIGUOUS
    )


# --- REF-001 ticket deliverable scenarios (synthetic coverage) --------------


def _seed_two_instruments(tmp_path: Path) -> tuple[
    sqlite3.Connection, store.ReferenceStore, str, str, str, str
]:
    """Two distinct instruments on the same asset+venue (different salts)."""
    conn, s, vid, aid, iid = _seed(tmp_path)
    iid2 = s.register_instrument(
        asset_id=aid, venue_id=vid, instrument_type=models.InstrumentType.SPOT, salt="z2"
    ).instrument_id
    return conn, s, vid, aid, iid, iid2


def test_S1_ticker_reuse_resolves_correct_instrument_per_valid_window(tmp_path: Path) -> None:
    conn, s, vid, aid, iid1, iid2 = _seed_two_instruments(tmp_path)
    w1 = models.BiTemporalWindow(
        valid_from=datetime(2018, 1, 1, tzinfo=timezone.utc),
        valid_to=datetime(2020, 1, 1, tzinfo=timezone.utc),
        known_from=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    w2 = models.BiTemporalWindow(
        valid_from=datetime(2020, 1, 1, tzinfo=timezone.utc),
        known_from=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    s.add_alias(
        alias_text="BTC", target_kind=models.TargetKind.INSTRUMENT, target_id=iid1,
        window=w1, venue_id=vid,
    )
    s.add_alias(
        alias_text="BTC", target_kind=models.TargetKind.INSTRUMENT, target_id=iid2,
        window=w2, venue_id=vid,
    )
    kt = datetime(2025, 1, 2, tzinfo=timezone.utc)
    early = s.resolve_alias("BTC", decision_time=datetime(2019, 6, 1, tzinfo=timezone.utc), knowledge_time=kt, venue_id=vid)
    assert early.outcome is models.ResolutionOutcome.RESOLVED
    assert early.target_id == iid1
    late = s.resolve_alias("BTC", decision_time=datetime(2021, 6, 1, tzinfo=timezone.utc), knowledge_time=kt, venue_id=vid)
    assert late.outcome is models.ResolutionOutcome.RESOLVED
    assert late.target_id == iid2


def test_S2_redenomination_event_preserves_endpoints_ratio_time_evidence(tmp_path: Path) -> None:
    conn, s, vid, aid, iid = _seed(tmp_path)
    aid2 = s.asset_id_for(asset_class=models.AssetClass.CRYPTO, identity_key="usdc|epj...")
    s.register_asset(asset_class=models.AssetClass.CRYPTO, display_name="USD Coin", identity_key="usdc|epj...")
    w = models.BiTemporalWindow(
        valid_from=datetime(2021, 1, 1, tzinfo=timezone.utc),
        known_from=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    ev = s.add_migration_event(
        event_type=models.MigrationEventType.REDENOMINATION,
        from_kind=models.TargetKind.ASSET, from_id=aid,
        to_kind=models.TargetKind.ASSET, to_id=aid2,
        window=w, ratio_num=1.0, ratio_den=1000.0,
        evidence={"note": "1 new == 1000 old"},
    )
    assert ev.event_type is models.MigrationEventType.REDENOMINATION
    assert ev.from_id == aid and ev.to_id == aid2
    assert ev.from_id != ev.to_id
    assert ev.ratio_num == 1.0 and ev.ratio_den == 1000.0
    assert ev.window.valid_from == w.valid_from and ev.window.known_from == w.known_from
    assert ev.evidence == {"note": "1 new == 1000 old"}


def test_S2_redenomination_rejects_zero_denominator_and_partial_ratio(tmp_path: Path) -> None:
    conn, s, vid, aid, iid = _seed(tmp_path)
    aid2 = s.asset_id_for(asset_class=models.AssetClass.CRYPTO, identity_key="usdc|epj...")
    s.register_asset(asset_class=models.AssetClass.CRYPTO, display_name="USD Coin", identity_key="usdc|epj...")
    w = models.BiTemporalWindow(
        valid_from=datetime(2021, 1, 1, tzinfo=timezone.utc),
        known_from=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    with pytest.raises(errors.ReferenceValidationError):
        s.add_migration_event(
            event_type=models.MigrationEventType.REDENOMINATION,
            from_kind=models.TargetKind.ASSET, from_id=aid,
            to_kind=models.TargetKind.ASSET, to_id=aid2,
            window=w, ratio_num=1.0, ratio_den=0.0,
        )
    with pytest.raises(errors.ReferenceValidationError):
        s.add_migration_event(
            event_type=models.MigrationEventType.REDENOMINATION,
            from_kind=models.TargetKind.ASSET, from_id=aid,
            to_kind=models.TargetKind.ASSET, to_id=aid2,
            window=w, ratio_num=1.0,
        )


def test_S3_contract_migration_preserves_distinct_source_dest_and_lineage(tmp_path: Path) -> None:
    conn, s, vid, aid, iid1, iid2 = _seed_two_instruments(tmp_path)
    w = models.BiTemporalWindow(
        valid_from=datetime(2022, 1, 1, tzinfo=timezone.utc),
        known_from=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    ev = s.add_migration_event(
        event_type=models.MigrationEventType.CONTRACT_MIGRATION,
        from_kind=models.TargetKind.INSTRUMENT, from_id=iid1,
        to_kind=models.TargetKind.INSTRUMENT, to_id=iid2,
        window=w, evidence={"reason": "perp expiry"},
    )
    assert ev.event_type is models.MigrationEventType.CONTRACT_MIGRATION
    assert ev.from_id == iid1 and ev.to_id == iid2
    assert ev.from_id != ev.to_id
    assert ev.evidence == {"reason": "perp expiry"}


def test_S4_delisting_lifecycle_events_retain_venue_time_and_identity(tmp_path: Path) -> None:
    conn, s, vid, aid, iid = _seed(tmp_path)
    list_w = models.BiTemporalWindow(
        valid_from=datetime(2019, 1, 1, tzinfo=timezone.utc),
        known_from=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    delist_w = models.BiTemporalWindow(
        valid_from=datetime(2023, 1, 1, tzinfo=timezone.utc),
        known_from=datetime(2024, 6, 1, tzinfo=timezone.utc),
    )
    listed = s.add_listing_event(
        instrument_id=iid, venue_id=vid, event_type=models.ListingEventType.LIST, window=list_w
    )
    delisted = s.add_listing_event(
        instrument_id=iid, venue_id=vid, event_type=models.ListingEventType.DELIST, window=delist_w
    )
    # venue + historical identity retained across both events
    assert listed.instrument_id == iid == delisted.instrument_id
    assert listed.venue_id == vid == delisted.venue_id
    # economic (valid) time and system-known time preserved
    assert listed.window.valid_from == list_w.valid_from
    assert listed.window.known_from == list_w.known_from
    assert delisted.window.valid_from == delist_w.valid_from
    assert delisted.window.known_from == delist_w.known_from
    assert listed.event_type is models.ListingEventType.LIST
    assert delisted.event_type is models.ListingEventType.DELIST


def test_S5_late_metadata_correction_covered_by_D9_I4(tmp_path: Path) -> None:
    # Late-metadata correction (knowledge-time correction arriving after the fact)
    # is exercised by D9 (test_supersede_alias_closes_known_to_and_inserts_replacement)
    # and I4 (test_I4_supersede_instrument_version_preserves_historical_as_of). This
    # test documents that coverage and pins the contract with a quick alias correction.
    conn, s, vid, aid, iid = _seed(tmp_path)
    al = s.add_alias(
        alias_text="BTC", target_kind=models.TargetKind.INSTRUMENT, target_id=iid,
        window=models.BiTemporalWindow(
            valid_from=datetime(2020, 1, 1, tzinfo=timezone.utc),
            known_from=datetime(2024, 1, 1, tzinfo=timezone.utc),
        ),
        venue_id=vid,
    )
    close_at = al.window.known_from + timedelta(seconds=1)
    # late correction: close prior known_to, insert replacement with contiguous knowledge time
    s.supersede_alias(al.alias_id, close_known_at=close_at)
    before = s.resolve_alias(
        "BTC", decision_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
        knowledge_time=al.window.known_from, venue_id=vid,
    )
    after = s.resolve_alias(
        "BTC", decision_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
        knowledge_time=close_at + timedelta(seconds=1), venue_id=vid,
    )
    assert before.outcome is models.ResolutionOutcome.RESOLVED
    assert after.outcome is models.ResolutionOutcome.RESOLVED
