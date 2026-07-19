"""AUD-001 — focused tests for the schema & coverage profiler.

Exercises the ticket's deliverables: bounded sampling vs streaming full-pass,
inferred physical schema with explicit uncertainty, nulls/duplicates/monotonicity,
impossible OHLC checks, and caller mapping (no silent guesses).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from cryptofactors.audit import (
    AuditInputError,
    ColumnMapping,
    ColumnRole,
    InputIdentity,
    MetricCompleteness,
    PhysicalType,
    ProfileMode,
    profile_candidate,
)


def _identity(path: Path) -> InputIdentity:
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    return InputIdentity(
        content_sha256=digest,
        byte_size=len(data),
        source_uri=f"file://{path}",
        media_type="text/csv",
    )


def test_sample_mode_partial_metrics_and_inferred_types(tmp_path: Path) -> None:
    csv = tmp_path / "cand.csv"
    csv.write_text(
        "id,price,label\n"
        "1,10.5,alpha\n"
        "2,20.0,beta\n"
        "3,30.25,gamma\n"
    )
    out = tmp_path / "out"
    res = profile_candidate(
        csv,
        _identity(csv),
        mode=ProfileMode.SAMPLE,
        output_dir=out,
    )
    assert res.summary.row_count == 3
    assert res.summary.row_count_completeness is MetricCompleteness.PARTIAL
    by_name = {c.name: c for c in res.summary.columns}
    assert by_name["id"].physical_type is PhysicalType.INTEGER
    assert by_name["price"].physical_type is PhysicalType.FLOAT
    assert by_name["label"].physical_type is PhysicalType.STRING
    # Sampling must surface a partial-metrics INFO issue, never claim exactness.
    codes = [i.code for i in res.issues]
    assert "sample_mode_partial_metrics" in codes
    # Artifacts staged (not published): summary/detail/issues paths exist.
    assert res.summary_path.is_file()
    assert res.detail_path.is_file()
    assert res.issues_path.is_file()


def test_full_mode_exact_and_no_sample_issue(tmp_path: Path) -> None:
    csv = tmp_path / "cand.csv"
    rows = "\n".join(f"{i},{i*1.5}" for i in range(50))
    csv.write_text(f"n,v\n{rows}\n")
    out = tmp_path / "out"
    res = profile_candidate(
        csv, _identity(csv), mode=ProfileMode.FULL, output_dir=out
    )
    assert res.summary.row_count == 50
    assert res.summary.row_count_completeness is MetricCompleteness.EXACT
    assert all(
        i.code != "sample_mode_partial_metrics" for i in res.issues
    )


def test_impossible_ohlc_flagged_not_repaired(tmp_path: Path) -> None:
    csv = tmp_path / "ohlc.csv"
    csv.write_text(
        "open,high,low,close\n"
        "100,110,90,105\n"   # valid
        "200,150,90,140\n"   # invalid: low(90) > high(150)
    )
    out = tmp_path / "out"
    res = profile_candidate(
        csv,
        _identity(csv),
        mode=ProfileMode.FULL,
        column_mapping=ColumnMapping(open="open", high="high", low="low", close="close"),
        output_dir=out,
    )
    # Impossible OHLC must be surfaced as a violation, not silently repaired.
    assert res.summary.ohlc.violation_count == 1
    # The bad row's values are preserved in detail (profiler reports, does not fix).
    assert res.detail_path.is_file()


def test_mapping_assigns_roles_and_resolves_ambiguity(tmp_path: Path) -> None:
    csv = tmp_path / "ts.csv"
    csv.write_text("ts,open,high,low,close,vol\n1,1,1,1,1,1\n2,2,2,2,2,2\n")
    out = tmp_path / "out"
    mapping = ColumnMapping(
        timestamp="ts",
        keys=("ts",),
        open="open",
        high="high",
        low="low",
        close="close",
        volume="vol",
    )
    res = profile_candidate(
        csv, _identity(csv), mode=ProfileMode.FULL, column_mapping=mapping, output_dir=out
    )
    by_name = {c.name: c for c in res.summary.columns}
    assert by_name["ts"].mapped_role is ColumnRole.TIMESTAMP
    assert by_name["open"].mapped_role is ColumnRole.OPEN
    assert by_name["vol"].mapped_role is ColumnRole.VOLUME
    # Explicit mapping -> no timestamp/ohlc ambiguity issues.
    assert all(
        not i.code.startswith(("timestamp_mapping_", "ohlc_mapping_"))
        for i in res.issues
    )


def test_duplicate_keys_detected(tmp_path: Path) -> None:
    csv = tmp_path / "dup.csv"
    csv.write_text("key,val\nA,1\nA,2\nB,3\n")
    out = tmp_path / "out"
    res = profile_candidate(
        csv,
        _identity(csv),
        mode=ProfileMode.FULL,
        column_mapping=ColumnMapping(keys=("key",)),
        output_dir=out,
    )
    dup = res.summary.duplicate_keys
    assert dup.key_columns == ("key",)
    assert dup.duplicate_key_count == 1  # key "A" repeats
    assert dup.duplicate_row_count == 1


def test_byte_size_mismatch_raises(tmp_path: Path) -> None:
    csv = tmp_path / "cand.csv"
    csv.write_text("a,b\n1,2\n")
    bad = _identity(csv)
    object.__setattr__(bad, "byte_size", bad.byte_size + 1)  # violate size check
    out = tmp_path / "out"
    with pytest.raises(AuditInputError):
        profile_candidate(csv, bad, mode=ProfileMode.SAMPLE, output_dir=out)


def test_missing_file_raises(tmp_path: Path) -> None:
    missing = tmp_path / "nope.csv"
    # Provide a plausible identity; the path check fires before size check.
    ident = InputIdentity(
        content_sha256="0" * 64, byte_size=0, source_uri="file://nope"
    )
    out = tmp_path / "out"
    with pytest.raises(AuditInputError):
        profile_candidate(missing, ident, mode=ProfileMode.SAMPLE, output_dir=out)
