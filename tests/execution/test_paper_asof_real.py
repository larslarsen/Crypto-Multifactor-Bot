"""Tests for DATA-003 Real As-Of Paper Path Correctness & Fail-Closed Guards."""

import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from cryptofactors.catalog.runner import apply_migrations
from cryptofactors.execution import (
    PAPER_TO_BINANCE_MAP,
    PaperExecutionError,
    to_binance_symbol,
    to_paper_symbol,
)

UTC = timezone.utc


def test_symbol_mapping_bidirectional() -> None:
    """DATA-003: Verify symbol translation between paper universe and Binance spot symbols."""
    assert to_binance_symbol("XBTUSD") == "BTCUSDT"
    assert to_binance_symbol("ETHUSD") == "ETHUSDT"
    assert to_binance_symbol("SOLUSD") == "SOLUSDT"

    assert to_paper_symbol("BTCUSDT") == "XBTUSD"
    assert to_paper_symbol("ETHUSDT") == "ETHUSD"
    assert to_paper_symbol("SOLUSDT") == "SOLUSD"


def test_paper_path_fails_closed_without_control_db() -> None:
    """DATA-003: Non-dry-run path must fail closed if control database is missing."""
    import subprocess

    cmd = [
        ".venv/bin/python",
        "scripts/run_paper_momts.py",
        "--db-path",
        "/nonexistent/path/control.db",
        "--store-root",
        "/nonexistent/store",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)

    assert res.returncode != 0
    assert "Control database missing" in res.stderr or "PaperExecutionError" in res.stderr


def test_paper_path_fails_closed_without_store_root() -> None:
    """DATA-003: Non-dry-run path must fail closed if dataset_store_root does not exist."""
    import subprocess

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "control.db"
        apply_migrations(db_path)

        cmd = [
            ".venv/bin/python",
            "scripts/run_paper_momts.py",
            "--db-path",
            str(db_path),
            "--store-root",
            "/nonexistent/store/root",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)

        assert res.returncode != 0
        assert "Dataset store root missing" in res.stderr or "PaperExecutionError" in res.stderr


def test_paper_path_fails_closed_without_market_bars_dataset() -> None:
    """DATA-003: Non-dry-run path must fail closed if no market_bars dataset exists in catalog."""
    import subprocess

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "control.db"
        store_root = Path(tmpdir) / "store"
        store_root.mkdir(parents=True, exist_ok=True)
        apply_migrations(db_path)

        cmd = [
            ".venv/bin/python",
            "scripts/run_paper_momts.py",
            "--db-path",
            str(db_path),
            "--store-root",
            str(store_root),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)

        assert res.returncode != 0
        assert "market_bars dataset" in res.stderr or "PaperExecutionError" in res.stderr
