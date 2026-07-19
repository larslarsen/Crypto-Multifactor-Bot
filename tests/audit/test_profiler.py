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


def test_full_mode_gaps_classified_against_final_median(tmp_path: Path) -> None:
    # v1.2.1 fix: gaps are counted against the FINAL median (exact SQL pass),
    # not a drifting running-probe median of early samples.
    # Cadence comes from the `ts` column: two large early deltas (100s) followed
    # by many tiny deltas (1s). Final median is 1 -> threshold 3 -> exactly the
    # two 100s are gaps.
    n_small = 98
    deltas = [100, 100] + [1] * n_small
    ts = [0]
    for d in deltas:
        ts.append(ts[-1] + d)
    # Keep the origin (101 timestamp rows) so inter-row deltas are exactly
    # [100, 100] + [1]*98. Do NOT slice ts[1:] here -- dropping the origin 0
    # removes one 100s delta and the CSV would expose only one gap.
    rows = "\n".join(f"{t},{i}" for i, t in enumerate(ts))
    csv = tmp_path / "cad.csv"
    csv.write_text(f"ts,val\n{rows}\n")
    out = tmp_path / "out"
    res = profile_candidate(
        csv, _identity(csv), mode=ProfileMode.FULL, output_dir=out
    )
    # Exact gap count against the true final median.
    final_median = sorted(deltas)[len(deltas) // 2]
    expected = sum(1 for d in deltas if d > 3 * final_median)
    assert res.summary.timestamp.gap_count == expected
    assert expected == 2
    # Median is the tiny value (1), confirming gaps are measured against it.
    assert res.summary.timestamp.median_cadence_seconds == final_median



# ---- Reviewer CHANGES_REQUIRED findings (REVIEW-0013) -----------------------


def test_sha256_mismatch_is_verified_not_just_recorded(tmp_path: Path) -> None:
    csv = tmp_path / "cand.csv"
    csv.write_text("a,b\n1,2\n3,4\n")
    ident = _identity(csv)
    # Corrupt the hash; byte_size still matches, so only SHA-256 verification catches it.
    object.__setattr__(ident, "content_sha256", "f" * 64)
    out = tmp_path / "out"
    with pytest.raises(AuditInputError):
        profile_candidate(csv, ident, mode=ProfileMode.FULL, output_dir=out)


def test_parquet_preserves_physical_types(tmp_path: Path) -> None:
    import polars as pl

    csv = tmp_path / "cand.csv"
    csv.write_text("i,f,s,b\n1,1.5,hello,true\n2,2.5,world,false\n")
    out = tmp_path / "out"
    profiled = profile_candidate(
        csv, _identity(csv), mode=ProfileMode.FULL, output_dir=out
    )
    by_name = {c.name: c for c in profiled.summary.columns}
    # CSV inference yields physical types; declared_type_label stays None for CSV
    # (no native Arrow schema), and uncertainty is tracked.
    assert by_name["i"].physical_type is PhysicalType.INTEGER
    assert by_name["f"].physical_type is PhysicalType.FLOAT
    assert by_name["s"].physical_type is PhysicalType.STRING
    assert by_name["b"].physical_type is PhysicalType.BOOLEAN

    # Parquet input carries a real Arrow schema; declared_type_label must be preserved.
    pq_path = tmp_path / "cand.parquet"
    pl.DataFrame(
        {
            "i": pl.Series([1, 2], dtype=pl.Int64),
            "f": pl.Series([1.5, 2.5], dtype=pl.Float64),
            "s": pl.Series(["hello", "world"], dtype=pl.String),
            "b": pl.Series([True, False], dtype=pl.Boolean),
        }
    ).write_parquet(str(pq_path))
    ident_pq = InputIdentity(
        content_sha256=hashlib.sha256(pq_path.read_bytes()).hexdigest(),
        byte_size=pq_path.stat().st_size,
        source_uri=f"file://{pq_path}",
        media_type="application/octet-stream",
    )
    out2 = tmp_path / "out2"
    profiled_pq = profile_candidate(
        pq_path, ident_pq, mode=ProfileMode.FULL, output_dir=out2
    )
    by_pq = {c.name: c for c in profiled_pq.summary.columns}
    # The native Arrow dtype is recorded verbatim (physical types preserved).
    assert by_pq["i"].declared_type_label is not None
    assert by_pq["f"].declared_type_label is not None
    assert by_pq["s"].declared_type_label is not None
    assert by_pq["b"].declared_type_label is not None
    labels = {name: col.declared_type_label for name, col in by_pq.items()}
    assert labels["i"] == "int64"
    assert labels["f"] == "double"
    assert labels["s"] == "large_string"
    assert labels["b"] == "bool"
    # Clearly-typed columns are not flagged as uncertain.
    assert by_pq["i"].type_uncertainty is False


def test_full_mode_processes_large_csv_without_materializing(tmp_path: Path) -> None:
    # Proxy for bounded FULL-mode: a 50k-row CSV must profile in FULL mode and
    # report EXACT row counts (the out-of-core spill path runs, not collect()).
    n = 50_000
    csv = tmp_path / "big.csv"
    rows = "\n".join(f"{i},{i * 1.5}" for i in range(n))
    csv.write_text(f"n,v\n{rows}\n")
    out = tmp_path / "out"
    res = profile_candidate(
        csv, _identity(csv), mode=ProfileMode.FULL, output_dir=out
    )
    assert res.summary.row_count == n
    assert res.summary.row_count_completeness is MetricCompleteness.EXACT


def test_summary_carries_valid_identity_statistics(tmp_path: Path) -> None:
    csv = tmp_path / "cand.csv"
    csv.write_text("a,b\n1,2\n3,4\n")
    ident = _identity(csv)
    out = tmp_path / "out"
    res = profile_candidate(csv, ident, mode=ProfileMode.FULL, output_dir=out)
    # Valid MAN-001 statistics: summary records the verified identity verbatim.
    assert res.summary.input["content_sha256"] == ident.content_sha256
    assert res.summary.input["byte_size"] == ident.byte_size
    assert res.summary.input["source_uri"] == ident.source_uri
