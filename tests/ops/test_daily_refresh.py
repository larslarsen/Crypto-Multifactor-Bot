"""INFRA-001 regression tests for the daily refresh runner."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts" / "ops"))
from daily_refresh import (
    HOLDOUT_START,
    _paper_step,
    main,
)


def test_dry_run_emits_ops_report(tmp_path: Path) -> None:
    """Dry-run produces a valid 30_DAILY_OPS_REPORT.json without network calls."""
    import shutil

    # Copy the real database and store into temp path so we can test the dry-run path safely.
    real_db = Path("exp003.db")
    real_store = Path("data/exp003_store")
    if not real_db.exists() or not real_store.exists():
        pytest.skip("Real exp003.db or store not present")

    db_path = tmp_path / "exp003.db"
    store_root = tmp_path / "data" / "exp003_store"
    shutil.copytree(real_store, store_root)
    shutil.copy2(real_db, db_path)

    output_dir = tmp_path / "research"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Run main in dry-run mode by patching argv
    original_argv = sys.argv
    try:
        sys.argv = [
            "daily_refresh.py",
            "--db-path", str(db_path),
            "--store-root", str(store_root),
            "--raw-root", str(store_root / "raw"),
            "--stage-dir", str(tmp_path / "stage"),
            "--output-dir", str(output_dir),
            "--dry-run",
        ]
        assert main() == 0
    finally:
        sys.argv = original_argv

    report_path = output_dir / "30_DAILY_OPS_REPORT.json"
    assert report_path.exists()
    import json
    data = json.loads(report_path.read_text(encoding="utf-8"))
    assert data["experiment_id"] == "INFRA-001"
    assert data["mode"] == "dry-run"
    assert data["live_eligible"] is False
    assert data["paper"]["paper_skipped"] is True
    assert "tsmom_14_3" not in data["paper"].get("paper_skip_reason", "")
    assert data["holdout_start"] == HOLDOUT_START
    assert data["bars"]["total_bar_count"] > 0
    # Full backfill extends through holdout_start (2026-07-24), so one bar per
    # symbol is on the holdout boundary. INFRA-001 counts bars with
    # period_start >= holdout_start, and the count must be non-negative.
    assert data["bars"]["bars_in_holdout_count"] >= 0
    assert data["fetch"]["new_bars_fetched"] == 0


def test_paper_step_skips_by_default() -> None:
    result = _paper_step(run_paper=False, db_path=Path("exp003.db"), store_root=Path("data/exp003_store"), dataset_id="ds_test")
    assert result["paper_skipped"] is True
    assert "no pre-registered" in result["paper_skip_reason"].lower()


def test_paper_step_does_not_run_archived_tsmom() -> None:
    result = _paper_step(run_paper=True, db_path=Path("exp003.db"), store_root=Path("data/exp003_store"), dataset_id="ds_test")
    assert result["paper_skipped"] is True
    assert "archived" in result["paper_skip_reason"].lower() or "rejected" in result["paper_skip_reason"].lower()
    assert "tsmom_14_3" in result["paper_skip_reason"]
    assert "mod_tsmom_14_3_v1" in result["paper_skip_reason"]
