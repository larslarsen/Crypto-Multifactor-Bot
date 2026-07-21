from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from shutil import copy2

import pytest

from cryptofactors.catalog.runner import MIGRATIONS_DIR, apply_migrations
from cryptofactors.reference import (
    BiTemporalWindow,
    FeeEvidenceClass,
    FeeSchedule,
    dt_to_iso,
    ReferenceConflictError,
    ReferenceNotFoundError,
    ReferenceStore,
    ReferenceValidationError,
    AssetClass,
    InstrumentType,
    VenueType,
)


def _db(tmp_path: Path, *, migrations_dir: Path = MIGRATIONS_DIR) -> sqlite3.Connection:
    db = tmp_path / "ref.db"
    apply_migrations(db, migrations_dir=migrations_dir)
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _seed_store(tmp_path: Path) -> tuple[sqlite3.Connection, ReferenceStore, str, str, str]:
    conn = _db(tmp_path)
    ref = ReferenceStore(conn)
    venue = ref.upsert_venue(venue_code="BYBIT", display_name="Bybit", venue_type=VenueType.CEX)
    asset = ref.register_asset(
        asset_class=AssetClass.CRYPTO,
        display_name="Bitcoin",
        identity_key="btc|seed",
    )
    instrument = ref.register_instrument(
        asset_id=asset.asset_id,
        venue_id=venue.venue_id,
        instrument_type=InstrumentType.PERPETUAL,
        salt="fee-test",
    )
    return conn, ref, venue.venue_id, asset.asset_id, instrument.instrument_id


def _copy_first_six_migrations(root: Path) -> Path:
    copied = root / "migrations_0006"
    copied.mkdir()
    for mig in sorted(MIGRATIONS_DIR.glob("000[1-6]_*.sql")):
        copy2(mig, copied / mig.name)
    return copied


def _fee_window(
    valid_from: datetime,
    *,
    valid_to: datetime | None = None,
    known_from: datetime,
    known_to: datetime | None = None,
) -> BiTemporalWindow:
    return BiTemporalWindow(
        valid_from=valid_from,
        valid_to=valid_to,
        known_from=known_from,
        known_to=known_to,
    )


def test_migration_0007_applies_to_fresh_and_previously_migrated_databases(
    tmp_path: Path,
) -> None:
    fresh = tmp_path / "fresh.db"
    apply_migrations(fresh, migrations_dir=MIGRATIONS_DIR)
    conn = sqlite3.connect(fresh)
    fresh_tables = {
        row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    assert "ref_fee_schedule" in fresh_tables
    assert (
        conn.execute(
            "SELECT COUNT(*) FROM migration_history WHERE filename = ?",
            ("0007_reference_fee_schedule.sql",),
        ).fetchone()[0]
        == 1
    )
    conn.close()

    legacy_db = tmp_path / "legacy.db"
    mig_dir = _copy_first_six_migrations(tmp_path)
    apply_migrations(legacy_db, migrations_dir=mig_dir)
    conn = sqlite3.connect(legacy_db)
    legacy_tables = {
        row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    assert "ref_fee_schedule" not in legacy_tables
    conn.close()

    apply_migrations(legacy_db, migrations_dir=MIGRATIONS_DIR)
    conn = sqlite3.connect(legacy_db)
    migrated_tables = {
        row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    assert "ref_fee_schedule" in migrated_tables
    assert (
        conn.execute(
            "SELECT COUNT(*) FROM migration_history WHERE filename = ?",
            ("0007_reference_fee_schedule.sql",),
        ).fetchone()[0]
        == 1
    )
    conn.close()


def test_fee_schedule_public_exports() -> None:
    assert FeeSchedule.__name__ == "FeeSchedule"
    assert FeeEvidenceClass.OFFICIAL_SCHEDULE.value == "OFFICIAL_SCHEDULE"
    assert FeeEvidenceClass.ASSUMED_CONSERVATIVE.value == "ASSUMED_CONSERVATIVE"


def test_fee_schedule_identity_and_storage_are_canonical(tmp_path: Path) -> None:
    conn, ref, _, _, instrument_id = _seed_store(tmp_path)
    t0 = datetime(2024, 1, 1, tzinfo=timezone.utc)
    k0 = datetime(2024, 1, 2, tzinfo=timezone.utc)

    canonical = ref.fee_schedule_id_for(
        instrument_id=instrument_id,
        fee_tier_id="  vip  ",
        maker_fee_rate=Decimal("0.001"),
        taker_fee_rate=Decimal("0.0010"),
        evidence_class=FeeEvidenceClass.OFFICIAL_SCHEDULE,
        valid_from=t0,
        known_from=k0,
    )
    equivalent = ref.fee_schedule_id_for(
        instrument_id=instrument_id,
        fee_tier_id="vip",
        maker_fee_rate=Decimal("0.0010"),
        taker_fee_rate=Decimal("0.001"),
        evidence_class=FeeEvidenceClass.OFFICIAL_SCHEDULE,
        valid_from=t0,
        known_from=k0,
    )
    zero_a = ref.fee_schedule_id_for(
        instrument_id=instrument_id,
        fee_tier_id="zero",
        maker_fee_rate=Decimal("-0"),
        taker_fee_rate=Decimal("0.000"),
        evidence_class=FeeEvidenceClass.ASSUMED_CONSERVATIVE,
        valid_from=t0,
        known_from=k0,
    )
    zero_b = ref.fee_schedule_id_for(
        instrument_id=instrument_id,
        fee_tier_id=" zero ",
        maker_fee_rate=Decimal("0"),
        taker_fee_rate=Decimal("-0.0"),
        evidence_class=FeeEvidenceClass.ASSUMED_CONSERVATIVE,
        valid_from=t0,
        known_from=k0,
    )

    assert canonical == equivalent
    assert zero_a == zero_b

    schedule = ref.add_fee_schedule(
        instrument_id=instrument_id,
        fee_tier_id="  vip  ",
        maker_fee_rate=Decimal("0.0010"),
        taker_fee_rate=Decimal("0.001"),
        evidence_class=FeeEvidenceClass.OFFICIAL_SCHEDULE,
        window=_fee_window(t0, known_from=k0),
        evidence={"source": "official"},
    )
    zero_schedule = ref.add_fee_schedule(
        instrument_id=instrument_id,
        fee_tier_id="zero",
        maker_fee_rate=Decimal("-0"),
        taker_fee_rate=Decimal("0.000"),
        evidence_class=FeeEvidenceClass.ASSUMED_CONSERVATIVE,
        window=_fee_window(
            t0 + timedelta(days=1),
            known_from=k0 + timedelta(days=1),
        ),
        evidence={},
    )

    assert schedule.fee_tier_id == "vip"
    assert schedule.maker_fee_rate == Decimal("0.001")
    assert schedule.taker_fee_rate == Decimal("0.001")
    assert zero_schedule.maker_fee_rate == Decimal("0")
    assert zero_schedule.taker_fee_rate == Decimal("0")

    rows = conn.execute(
        "SELECT fee_tier_id, maker_fee_rate, taker_fee_rate, evidence_json "
        "FROM ref_fee_schedule ORDER BY fee_tier_id"
    ).fetchall()
    assert [tuple(row[:3]) for row in rows] == [
        ("vip", "0.001", "0.001"),
        ("zero", "0", "0"),
    ]
    assert json.loads(rows[0][3]) == {"source": "official"}
    assert json.loads(rows[1][3]) == {}
    conn.close()


@pytest.mark.parametrize(
    "invalid_rate",
    [
        True,
        False,
        1,
        1.0,
        "0.1",
        Decimal("NaN"),
        Decimal("Infinity"),
        Decimal("-Infinity"),
        Decimal("-0.1"),
        Decimal("1"),
        Decimal("1.000"),
    ],
)
def test_fee_rate_validation_rejects_helper_and_insert_paths(
    tmp_path: Path, invalid_rate: object
) -> None:
    conn, ref, _, _, instrument_id = _seed_store(tmp_path)
    t0 = datetime(2024, 1, 1, tzinfo=timezone.utc)
    k0 = datetime(2024, 1, 2, tzinfo=timezone.utc)

    with pytest.raises(ReferenceValidationError):
        ref.fee_schedule_id_for(
            instrument_id=instrument_id,
            fee_tier_id="standard",
            maker_fee_rate=invalid_rate,
            taker_fee_rate=Decimal("0.001"),
            evidence_class=FeeEvidenceClass.OFFICIAL_SCHEDULE,
            valid_from=t0,
            known_from=k0,
        )

    with pytest.raises(ReferenceValidationError):
        ref.add_fee_schedule(
            instrument_id=instrument_id,
            fee_tier_id="standard",
            maker_fee_rate=invalid_rate,
            taker_fee_rate=Decimal("0.001"),
            evidence_class=FeeEvidenceClass.OFFICIAL_SCHEDULE,
            window=_fee_window(t0, known_from=k0),
        )
    conn.close()


def test_fee_schedule_validation_rejects_invalid_evidence_class_and_tier(
    tmp_path: Path,
) -> None:
    conn, ref, _, _, instrument_id = _seed_store(tmp_path)
    t0 = datetime(2024, 1, 1, tzinfo=timezone.utc)
    k0 = datetime(2024, 1, 2, tzinfo=timezone.utc)

    with pytest.raises(ReferenceValidationError):
        ref.fee_schedule_id_for(
            instrument_id=instrument_id,
            fee_tier_id="   ",
            maker_fee_rate=Decimal("0.001"),
            taker_fee_rate=Decimal("0.002"),
            evidence_class=FeeEvidenceClass.OFFICIAL_SCHEDULE,
            valid_from=t0,
            known_from=k0,
        )
    with pytest.raises(ReferenceValidationError):
        ref.add_fee_schedule(
            instrument_id=instrument_id,
            fee_tier_id="   ",
            maker_fee_rate=Decimal("0.001"),
            taker_fee_rate=Decimal("0.002"),
            evidence_class=FeeEvidenceClass.OFFICIAL_SCHEDULE,
            window=_fee_window(t0, known_from=k0),
        )

    with pytest.raises(ReferenceValidationError):
        ref.fee_schedule_id_for(
            instrument_id=instrument_id,
            fee_tier_id="standard",
            maker_fee_rate=Decimal("0.001"),
            taker_fee_rate=Decimal("0.002"),
            evidence_class="OFFICIAL_SCHEDULE",  # type: ignore[arg-type]
            valid_from=t0,
            known_from=k0,
        )
    with pytest.raises(ReferenceValidationError):
        ref.add_fee_schedule(
            instrument_id=instrument_id,
            fee_tier_id="standard",
            maker_fee_rate=Decimal("0.001"),
            taker_fee_rate=Decimal("0.002"),
            evidence_class="OFFICIAL_SCHEDULE",  # type: ignore[arg-type]
            window=_fee_window(t0, known_from=k0),
        )
    conn.close()


def test_fee_schedule_validation_rejects_naive_timestamps(tmp_path: Path) -> None:
    conn, ref, _, _, instrument_id = _seed_store(tmp_path)
    aware = datetime(2024, 1, 1, tzinfo=timezone.utc)
    naive = datetime(2024, 1, 1)

    with pytest.raises(ValueError):
        ref.fee_schedule_id_for(
            instrument_id=instrument_id,
            fee_tier_id="standard",
            maker_fee_rate=Decimal("0.001"),
            taker_fee_rate=Decimal("0.002"),
            evidence_class=FeeEvidenceClass.OFFICIAL_SCHEDULE,
            valid_from=naive,
            known_from=aware,
        )

    with pytest.raises(ValueError):
        ref.add_fee_schedule(
            instrument_id=instrument_id,
            fee_tier_id="standard",
            maker_fee_rate=Decimal("0.001"),
            taker_fee_rate=Decimal("0.002"),
            evidence_class=FeeEvidenceClass.OFFICIAL_SCHEDULE,
            window=_fee_window(naive, known_from=aware),
        )
    conn.close()


def test_missing_instrument_insertion_fails_atomically_with_no_fee_row(
    tmp_path: Path,
) -> None:
    conn = _db(tmp_path)
    ref = ReferenceStore(conn)
    with pytest.raises(ReferenceNotFoundError):
        ref.add_fee_schedule(
            instrument_id="missing-instrument",
            fee_tier_id="standard",
            maker_fee_rate=Decimal("0.001"),
            taker_fee_rate=Decimal("0.002"),
            evidence_class=FeeEvidenceClass.OFFICIAL_SCHEDULE,
            window=_fee_window(
                datetime(2024, 1, 1, tzinfo=timezone.utc),
                known_from=datetime(2024, 1, 2, tzinfo=timezone.utc),
            ),
        )
    assert conn.execute("SELECT COUNT(*) FROM ref_fee_schedule").fetchone()[0] == 0
    conn.close()


def test_same_instrument_tier_overlap_is_rejected_and_other_tiers_stay_independent(
    tmp_path: Path,
) -> None:
    conn, ref, _, _, instrument_id = _seed_store(tmp_path)
    first = ref.add_fee_schedule(
        instrument_id=instrument_id,
        fee_tier_id="vip",
        maker_fee_rate=Decimal("0.001"),
        taker_fee_rate=Decimal("0.002"),
        evidence_class=FeeEvidenceClass.OFFICIAL_SCHEDULE,
        window=_fee_window(
            datetime(2024, 1, 1, tzinfo=timezone.utc),
            valid_to=datetime(2024, 6, 1, tzinfo=timezone.utc),
            known_from=datetime(2024, 1, 2, tzinfo=timezone.utc),
        ),
    )
    with pytest.raises(ReferenceConflictError):
        ref.add_fee_schedule(
            instrument_id=instrument_id,
            fee_tier_id="vip",
            maker_fee_rate=Decimal("0.0015"),
            taker_fee_rate=Decimal("0.0025"),
            evidence_class=FeeEvidenceClass.OFFICIAL_SCHEDULE,
            window=_fee_window(
                datetime(2024, 3, 1, tzinfo=timezone.utc),
                valid_to=datetime(2024, 9, 1, tzinfo=timezone.utc),
                known_from=datetime(2024, 3, 2, tzinfo=timezone.utc),
            ),
        )
    other = ref.add_fee_schedule(
        instrument_id=instrument_id,
        fee_tier_id="maker",
        maker_fee_rate=Decimal("0.003"),
        taker_fee_rate=Decimal("0.004"),
        evidence_class=FeeEvidenceClass.ASSUMED_CONSERVATIVE,
        window=_fee_window(
            datetime(2024, 3, 1, tzinfo=timezone.utc),
            valid_to=datetime(2024, 9, 1, tzinfo=timezone.utc),
            known_from=datetime(2024, 3, 2, tzinfo=timezone.utc),
        ),
    )
    rows = conn.execute(
        "SELECT fee_tier_id, COUNT(*) AS c FROM ref_fee_schedule GROUP BY fee_tier_id"
    ).fetchall()
    assert {(row[0], row[1]) for row in rows} == {("maker", 1), ("vip", 1)}
    assert (
        ref.fee_schedule_as_of(
            instrument_id,
            "vip",
            decision_time=datetime(2024, 2, 1, tzinfo=timezone.utc),
            knowledge_time=datetime(2024, 2, 1, tzinfo=timezone.utc),
        )
        == first
    )
    assert (
        ref.fee_schedule_as_of(
            instrument_id,
            "maker",
            decision_time=datetime(2024, 4, 1, tzinfo=timezone.utc),
            knowledge_time=datetime(2024, 4, 1, tzinfo=timezone.utc),
        )
        == other
    )
    conn.close()


def test_fee_schedule_as_of_enforces_half_open_boundaries_and_no_fallback(
    tmp_path: Path,
) -> None:
    conn, ref, _, _, instrument_id = _seed_store(tmp_path)
    window = _fee_window(
        datetime(2024, 1, 1, tzinfo=timezone.utc),
        valid_to=datetime(2024, 6, 1, tzinfo=timezone.utc),
        known_from=datetime(2024, 1, 2, tzinfo=timezone.utc),
        known_to=datetime(2024, 7, 1, tzinfo=timezone.utc),
    )
    schedule = ref.add_fee_schedule(
        instrument_id=instrument_id,
        fee_tier_id="vip",
        maker_fee_rate=Decimal("0.001"),
        taker_fee_rate=Decimal("0.002"),
        evidence_class=FeeEvidenceClass.OFFICIAL_SCHEDULE,
        window=window,
    )

    assert (
        ref.fee_schedule_as_of(
            instrument_id,
            "vip",
            decision_time=window.valid_from,
            knowledge_time=window.known_from,
        )
        == schedule
    )
    assert (
        ref.fee_schedule_as_of(
            instrument_id,
            "vip",
            decision_time=window.valid_to,
            knowledge_time=window.known_from,
        )
        is None
    )
    assert (
        ref.fee_schedule_as_of(
            instrument_id,
            "vip",
            decision_time=window.valid_from,
            knowledge_time=window.known_to,
        )
        is None
    )
    assert (
        ref.fee_schedule_as_of(
            instrument_id,
            "missing",
            decision_time=window.valid_from,
            knowledge_time=window.known_from,
        )
        is None
    )
    conn.close()


def test_contiguous_supersession_closes_previous_window_and_preserves_history(
    tmp_path: Path,
) -> None:
    conn, ref, _, _, instrument_id = _seed_store(tmp_path)
    prior_window = _fee_window(
        datetime(2024, 1, 1, tzinfo=timezone.utc),
        valid_to=datetime(2024, 12, 31, tzinfo=timezone.utc),
        known_from=datetime(2024, 1, 2, tzinfo=timezone.utc),
    )
    prior = ref.add_fee_schedule(
        instrument_id=instrument_id,
        fee_tier_id="vip",
        maker_fee_rate=Decimal("0.001"),
        taker_fee_rate=Decimal("0.002"),
        evidence_class=FeeEvidenceClass.OFFICIAL_SCHEDULE,
        window=prior_window,
        evidence={"source": "official"},
    )
    close_at = prior_window.known_from + timedelta(days=1)
    replacement = ref.supersede_fee_schedule(
        prior.fee_schedule_id,
        close_known_at=close_at,
        maker_fee_rate=Decimal("0.0015"),
        taker_fee_rate=Decimal("0.0025"),
        evidence_class=FeeEvidenceClass.ASSUMED_CONSERVATIVE,
        evidence={"source": "correction"},
    )

    prior_row = conn.execute(
        "SELECT known_to, supersedes_fee_schedule_id, evidence_json "
        "FROM ref_fee_schedule WHERE fee_schedule_id = ?",
        (prior.fee_schedule_id,),
    ).fetchone()
    replacement_row = conn.execute(
        "SELECT known_from, known_to, supersedes_fee_schedule_id, evidence_json "
        "FROM ref_fee_schedule WHERE fee_schedule_id = ?",
        (replacement.fee_schedule_id,),
    ).fetchone()

    assert prior_row[0] == dt_to_iso(close_at)
    assert prior_row[1] is None
    assert json.loads(prior_row[2]) == {"source": "official"}
    assert replacement_row[0] == dt_to_iso(close_at)
    assert replacement_row[1] is None
    assert replacement_row[2] == prior.fee_schedule_id
    assert json.loads(replacement_row[3]) == {
        "source": "correction",
        "knowledge_correction_at": dt_to_iso(close_at),
        "supersedes_fee_schedule_id": prior.fee_schedule_id,
    }

    before = ref.fee_schedule_as_of(
        instrument_id,
        "vip",
        decision_time=datetime(2024, 6, 1, tzinfo=timezone.utc),
        knowledge_time=close_at - timedelta(microseconds=1),
    )
    after = ref.fee_schedule_as_of(
        instrument_id,
        "vip",
        decision_time=datetime(2024, 6, 1, tzinfo=timezone.utc),
        knowledge_time=close_at + timedelta(microseconds=1),
    )
    assert before.fee_schedule_id == prior.fee_schedule_id
    assert before.maker_fee_rate == prior.maker_fee_rate
    assert before.taker_fee_rate == prior.taker_fee_rate
    assert before.evidence_class == prior.evidence_class
    assert before.window.known_to == close_at
    assert after == replacement
    conn.close()


def test_supersession_rejects_noncontiguous_knowledge_window(tmp_path: Path) -> None:
    conn, ref, _, _, instrument_id = _seed_store(tmp_path)
    prior_window = _fee_window(
        datetime(2024, 1, 1, tzinfo=timezone.utc),
        valid_to=datetime(2024, 6, 1, tzinfo=timezone.utc),
        known_from=datetime(2024, 1, 2, tzinfo=timezone.utc),
    )
    prior = ref.add_fee_schedule(
        instrument_id=instrument_id,
        fee_tier_id="vip",
        maker_fee_rate=Decimal("0.001"),
        taker_fee_rate=Decimal("0.002"),
        evidence_class=FeeEvidenceClass.OFFICIAL_SCHEDULE,
        window=prior_window,
    )

    with pytest.raises(ReferenceValidationError):
        ref.supersede_fee_schedule(
            prior.fee_schedule_id,
            close_known_at=prior_window.known_from + timedelta(days=1),
            new_window=_fee_window(
                datetime(2024, 4, 1, tzinfo=timezone.utc),
                valid_to=datetime(2024, 9, 1, tzinfo=timezone.utc),
                known_from=prior_window.known_from + timedelta(days=2),
            ),
        )

    prior_row = conn.execute(
        "SELECT known_to FROM ref_fee_schedule WHERE fee_schedule_id = ?",
        (prior.fee_schedule_id,),
    ).fetchone()
    assert prior_row[0] is None
    conn.close()


def test_supersession_failure_rolls_back_prior_window_and_rejects_conflicts(
    tmp_path: Path,
) -> None:
    conn, ref, _, _, instrument_id = _seed_store(tmp_path)
    prior_window = _fee_window(
        datetime(2024, 1, 1, tzinfo=timezone.utc),
        valid_to=datetime(2024, 6, 1, tzinfo=timezone.utc),
        known_from=datetime(2024, 1, 2, tzinfo=timezone.utc),
    )
    prior = ref.add_fee_schedule(
        instrument_id=instrument_id,
        fee_tier_id="vip",
        maker_fee_rate=Decimal("0.001"),
        taker_fee_rate=Decimal("0.002"),
        evidence_class=FeeEvidenceClass.OFFICIAL_SCHEDULE,
        window=prior_window,
    )
    conflict = ref.add_fee_schedule(
        instrument_id=instrument_id,
        fee_tier_id="vip",
        maker_fee_rate=Decimal("0.003"),
        taker_fee_rate=Decimal("0.004"),
        evidence_class=FeeEvidenceClass.OFFICIAL_SCHEDULE,
        window=_fee_window(
            datetime(2024, 6, 1, tzinfo=timezone.utc),
            valid_to=datetime(2024, 12, 31, tzinfo=timezone.utc),
            known_from=datetime(2024, 1, 3, tzinfo=timezone.utc),
        ),
    )

    with pytest.raises(ReferenceConflictError):
        ref.supersede_fee_schedule(
            prior.fee_schedule_id,
            close_known_at=prior_window.known_from + timedelta(days=1),
            new_window=_fee_window(
                datetime(2024, 4, 1, tzinfo=timezone.utc),
                valid_to=datetime(2024, 9, 1, tzinfo=timezone.utc),
                known_from=prior_window.known_from + timedelta(days=1),
            ),
        )

    prior_row = conn.execute(
        "SELECT known_to FROM ref_fee_schedule WHERE fee_schedule_id = ?",
        (prior.fee_schedule_id,),
    ).fetchone()
    assert prior_row[0] is None

    with pytest.raises(ReferenceConflictError):
        ref.supersede_fee_schedule(
            prior.fee_schedule_id,
            close_known_at=prior_window.known_from + timedelta(days=1),
            new_window=_fee_window(
                datetime(2024, 5, 1, tzinfo=timezone.utc),
                valid_to=datetime(2024, 9, 1, tzinfo=timezone.utc),
                known_from=prior_window.known_from + timedelta(days=1),
            ),
        )

    repeated = ref.supersede_fee_schedule(
        prior.fee_schedule_id,
        close_known_at=prior_window.known_from + timedelta(days=1),
    )
    with pytest.raises(ReferenceConflictError):
        ref.supersede_fee_schedule(
            prior.fee_schedule_id,
            close_known_at=prior_window.known_from + timedelta(days=2),
        )
    repeated_row = conn.execute(
        "SELECT known_to FROM ref_fee_schedule WHERE fee_schedule_id = ?",
        (repeated.fee_schedule_id,),
    ).fetchone()
    assert repeated_row[0] is None
    conflict_row = conn.execute(
        "SELECT fee_tier_id FROM ref_fee_schedule WHERE fee_schedule_id = ?",
        (conflict.fee_schedule_id,),
    ).fetchone()
    assert conflict_row[0] == "vip"
    conn.close()


def test_evidence_defaults_are_independent_between_records(tmp_path: Path) -> None:
    conn, ref, _, _, instrument_id = _seed_store(tmp_path)
    first = ref.add_fee_schedule(
        instrument_id=instrument_id,
        fee_tier_id="first",
        maker_fee_rate=Decimal("0.001"),
        taker_fee_rate=Decimal("0.002"),
        evidence_class=FeeEvidenceClass.OFFICIAL_SCHEDULE,
        window=_fee_window(
            datetime(2024, 1, 1, tzinfo=timezone.utc),
            known_from=datetime(2024, 1, 2, tzinfo=timezone.utc),
        ),
    )
    second = ref.add_fee_schedule(
        instrument_id=instrument_id,
        fee_tier_id="second",
        maker_fee_rate=Decimal("0.003"),
        taker_fee_rate=Decimal("0.004"),
        evidence_class=FeeEvidenceClass.ASSUMED_CONSERVATIVE,
        window=_fee_window(
            datetime(2024, 2, 1, tzinfo=timezone.utc),
            known_from=datetime(2024, 2, 2, tzinfo=timezone.utc),
        ),
    )

    assert first.evidence == {}
    assert second.evidence == {}
    assert first.evidence is not second.evidence
    first.evidence["mutated"] = True
    assert second.evidence == {}
    conn.close()
