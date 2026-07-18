"""Runner-focused tests for the AUD-003 Sprint 003 audit runner.

These tests exercise `scripts/audit/run_sprint003_audit.py` deterministically
against the external staging area at /tmp/crypto_source_audit. They assert:

- the runner produces all expected report files;
- re-running yields byte-identical outputs (determinism);
- the Bybit pagination replay completes and consumes the captured chain;
- the headerless precision adapter reports an ms->us transition;
- the trade-to-bar reconstruction completes (comparison may be partial).

The staging directory must exist; tests skip (not fail) if it is absent.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
STAGING = Path("/tmp/crypto_source_audit")
OUT = REPO / "research" / "sprint_003" / "audit_results"
RUNNER = REPO / "scripts" / "audit" / "run_sprint003_audit.py"

EXPECTED_REPORTS = [
    "evidence_reconciliation.json", "evidence_reconciliation.csv",
    "hash_verification.json", "archive_safety.json", "csv_schema_timestamp.json",
    "binance_precision_comparison.json", "binance_precision_comparison_adapter.json",
    "pagination.json", "bar_reconstruction_comparison.json",
    "bybit_archive_inspection.json", "storage_statistics.json",
    "provider_coverage.json", "execution_manifest.json",
]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run():
    subprocess.run(
        [sys.executable, str(RUNNER), "--staging", str(STAGING),
         "--out", str(OUT)],
        cwd=str(REPO), check=True,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


@pytest.fixture(scope="module")
def outputs():
    if not STAGING.exists():
        pytest.skip("staging area /tmp/crypto_source_audit absent")
    OUT.mkdir(parents=True, exist_ok=True)
    _run()
    return {p.name: p for p in OUT.glob("*.json")}


def test_all_expected_reports_present(outputs):
    names = {p.name for p in OUT.glob("*") if p.suffix in (".json", ".csv")}
    missing = [r for r in EXPECTED_REPORTS if r not in names]
    assert not missing, f"missing reports: {missing}"


def test_deterministic_outputs(outputs):
    hashes_a = {name: _sha(p) for name, p in outputs.items() if name.endswith(".json")}
    _run()
    hashes_b = {name: _sha(p) for name, p in outputs.items() if name.endswith(".json")}
    assert hashes_a == hashes_b, "re-run produced non-identical outputs"


def test_bybit_pagination_replay_completes(outputs):
    doc = json.loads(outputs["pagination.json"].read_text())
    assert doc["status"] == "completed"
    assert doc["pages_consumed"] >= 2
    assert doc["termination_reason"] in ("empty_page", "no_next_cursor")
    assert doc["gaps"] == 0
    assert doc["repeated_cursors"] == 0


def test_headerless_precision_adapter_transition(outputs):
    doc = json.loads(outputs["binance_precision_comparison_adapter.json"].read_text())
    assert doc["native_status"].startswith("failed")
    assert doc["supports_unit_transition"] is True
    assert doc["transition"].endswith("MICROSECONDS")
    assert "MILLISECONDS" in doc["transition"]


def test_trade_to_bar_reconstruction_completes(outputs):
    doc = json.loads(outputs["bar_reconstruction_comparison.json"].read_text())
    # Reconstruction must succeed even if the toolkit compare_bars is blocked.
    assert doc["status"] in ("partial", "completed")
    assert doc["reconstructed_bars"] > 0
    assert doc["comparison_status"] in ("completed", "failed")
    # Semantic separation must be explicit.
    assert "semantic_mismatch_flag" in doc


def test_provider_coverage_present(outputs):
    doc = json.loads(outputs["provider_coverage.json"].read_text())
    for prov in ["binance", "bybit", "coin_metrics", "okx", "kraken",
                 "defillama", "token_unlocks"]:
        assert prov in doc["providers"]
    # Kraken must be described as HTTP 404, not a DNS failure.
    kraken = doc["providers"]["kraken"]["restrictions"]
    assert "HTTP 404" in kraken
    assert "DNS" in kraken  # both layers documented distinctly
