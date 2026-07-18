"""Focused Binance archive timestamp-precision comparison.

Operates only on already-downloaded local archive objects. Does not call Binance REST
and does not hard-code that a precision transition occurred.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from .archives import (
    audit_zip_safe,
    iter_csv_rows_from_text,
    read_zip_member_text,
)
from .errors import AmbiguousTimestampError, OutOfRangeTimestampError, PrecisionComparisonError
from .models import BinancePrecisionComparison, SchemaFieldDiff, TimestampUnit
from .timestamps import infer_timestamp_unit


def _select_member(
    zip_path: Path,
    *,
    member_name: str | None,
    member_suffix: str | None,
) -> str:
    result = audit_zip_safe(zip_path)
    names = [m.name for m in result.members if not m.is_directory]
    if not names:
        raise PrecisionComparisonError(
            f"No file members in archive {zip_path}",
            context={"path": str(zip_path)},
        )
    if member_name is not None:
        if member_name not in names:
            raise PrecisionComparisonError(
                f"Member {member_name!r} not found",
                context={"path": str(zip_path), "members": names},
            )
        return member_name
    # Deterministic policy: lexicographically first member matching suffix, else first.
    if member_suffix is not None:
        matched = sorted(n for n in names if n.endswith(member_suffix))
        if matched:
            return matched[0]
    return sorted(names)[0]


def _schema_diff(
    schema_a: Sequence[str],
    schema_b: Sequence[str],
) -> tuple[SchemaFieldDiff, ...]:
    set_a = set(schema_a)
    set_b = set(schema_b)
    diffs: list[SchemaFieldDiff] = []
    for name in sorted(set_a - set_b):
        diffs.append(SchemaFieldDiff(field_name=name, side="only_left", detail="present only in A"))
    for name in sorted(set_b - set_a):
        diffs.append(SchemaFieldDiff(field_name=name, side="only_right", detail="present only in B"))
    # Order differences for shared fields.
    shared = [n for n in schema_a if n in set_b]
    shared_b = [n for n in schema_b if n in set_a]
    if shared != shared_b:
        diffs.append(
            SchemaFieldDiff(
                field_name="*",
                side="both",
                detail=f"column order differs: A={list(schema_a)} B={list(schema_b)}",
            )
        )
    return tuple(diffs)


def compare_binance_archive_precision(
    archive_a: Path,
    archive_b: Path,
    *,
    member_a: str | None = None,
    member_b: str | None = None,
    member_suffix: str | None = ".csv",
    encoding: str = "utf-8",
    delimiter: str = ",",
    timestamp_column: str | int = 0,
    timestamp_min_utc: datetime,
    timestamp_max_utc: datetime,
    max_sample_rows: int = 50,
    max_extracted_bytes: int = 50 * 1024 * 1024,
    has_header: bool = True,
) -> BinancePrecisionComparison:
    """Compare timestamp units inferred from two local Binance ZIP archives.

    Parameters
    ----------
    archive_a / archive_b:
        Paths to already-downloaded ZIP objects.
    member_a / member_b:
        Explicit member names, or ``None`` to apply the deterministic selection policy
        (lexicographically first member ending with ``member_suffix``, else first file).
    timestamp_column:
        Header name (when ``has_header``) or zero-based index.
    timestamp_min_utc / timestamp_max_utc:
        Bounds forwarded to timestamp inference.
    """
    if max_sample_rows <= 0:
        raise ValueError("max_sample_rows must be positive")

    path_a = Path(archive_a)
    path_b = Path(archive_b)
    if not path_a.exists() or not path_b.exists():
        raise PrecisionComparisonError(
            "Both archive paths must exist",
            context={"a": str(path_a), "b": str(path_b)},
        )

    sel_a = _select_member(path_a, member_name=member_a, member_suffix=member_suffix)
    sel_b = _select_member(path_b, member_name=member_b, member_suffix=member_suffix)

    text_a = read_zip_member_text(
        path_a, sel_a, encoding=encoding, max_extracted_bytes=max_extracted_bytes
    )
    text_b = read_zip_member_text(
        path_b, sel_b, encoding=encoding, max_extracted_bytes=max_extracted_bytes
    )

    schema_a, rows_a = iter_csv_rows_from_text(
        text_a, delimiter=delimiter, has_header=has_header
    )
    schema_b, rows_b = iter_csv_rows_from_text(
        text_b, delimiter=delimiter, has_header=has_header
    )

    def _ts_index(schema: tuple[str, ...], column: str | int) -> int:
        if isinstance(column, int):
            if column < 0 or column >= len(schema):
                raise PrecisionComparisonError(
                    f"timestamp_column index {column} out of range",
                    context={"schema": list(schema)},
                )
            return column
        if column not in schema:
            raise PrecisionComparisonError(
                f"timestamp column {column!r} not in schema",
                context={"schema": list(schema)},
            )
        return schema.index(column)

    idx_a = _ts_index(schema_a, timestamp_column)
    idx_b = _ts_index(schema_b, timestamp_column)

    def _analyze(
        rows: list[tuple[str, ...]],
        idx: int,
    ) -> tuple[tuple[str, ...], str | None, int, int]:
        raw_samples: list[str] = []
        units: list[str] = []
        malformed = 0
        ambiguous = 0
        for row in rows[:max_sample_rows]:
            if idx >= len(row):
                malformed += 1
                continue
            raw = row[idx]
            raw_samples.append(raw)
            try:
                inference = infer_timestamp_unit(
                    raw,
                    min_utc=timestamp_min_utc,
                    max_utc=timestamp_max_utc,
                )
                unit = (
                    inference.unit.value
                    if isinstance(inference.unit, TimestampUnit)
                    else str(inference.unit)
                )
                units.append(unit)
            except AmbiguousTimestampError:
                ambiguous += 1
            except OutOfRangeTimestampError:
                malformed += 1
            except Exception:
                malformed += 1

        dominant: str | None
        if not units:
            dominant = None
        else:
            # Deterministic: most frequent unit; ties broken by unit name sort.
            counts: dict[str, int] = {}
            for u in units:
                counts[u] = counts.get(u, 0) + 1
            dominant = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
        return tuple(raw_samples[:10]), dominant, malformed, ambiguous

    rep_a, unit_a, mal_a, amb_a = _analyze(rows_a, idx_a)
    rep_b, unit_b, mal_b, amb_b = _analyze(rows_b, idx_b)

    diffs = _schema_diff(schema_a, schema_b)

    # Evidence-based transition support: different dominant units, both non-null,
    # and low ambiguity. Never hard-coded.
    supports = False
    rationale_parts: list[str] = []
    if unit_a is None or unit_b is None:
        rationale_parts.append(
            "one or both archives lack a dominant inferred unit from sampled rows"
        )
    elif unit_a == unit_b:
        rationale_parts.append(
            f"both archives infer the same dominant unit ({unit_a}); "
            "no precision transition supported by this sample"
        )
    else:
        if amb_a > 0 or amb_b > 0:
            rationale_parts.append(
                f"units differ ({unit_a} vs {unit_b}) but ambiguous observations "
                f"are present (A={amb_a}, B={amb_b}); transition not supported"
            )
        else:
            supports = True
            rationale_parts.append(
                f"sampled rows support a unit change from {unit_a} to {unit_b} "
                f"with zero ambiguous observations in the sample window"
            )

    return BinancePrecisionComparison(
        archive_a_path=path_a,
        archive_b_path=path_b,
        member_a=sel_a,
        member_b=sel_b,
        representative_raw_a=rep_a,
        representative_raw_b=rep_b,
        inferred_unit_a=unit_a,
        inferred_unit_b=unit_b,
        schema_a=schema_a,
        schema_b=schema_b,
        schema_differences=diffs,
        malformed_a=mal_a,
        malformed_b=mal_b,
        ambiguous_a=amb_a,
        ambiguous_b=amb_b,
        supports_timestamp_precision_transition=supports,
        transition_rationale="; ".join(rationale_parts),
    )
