"""Focused Binance archive timestamp-precision comparison.

Operates only on already-downloaded local archive objects. Does not call Binance REST
and does not hard-code that a precision transition occurred.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
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
        diffs.append(
            SchemaFieldDiff(field_name=name, side="only_left", detail="present only in A")
        )
    for name in sorted(set_b - set_a):
        diffs.append(
            SchemaFieldDiff(field_name=name, side="only_right", detail="present only in B")
        )
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


def _rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 1.0
    return numerator / denominator


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
    min_valid_inferences: int = 5,
    max_malformed_rate: float = 0.1,
    max_ambiguous_rate: float = 0.05,
) -> BinancePrecisionComparison:
    """Compare timestamp units inferred from two local Binance ZIP archives.

    A transition is supported only when **both** sides meet the evidence thresholds:
    at least ``min_valid_inferences`` successful unit inferences, malformed rate
    ≤ ``max_malformed_rate``, ambiguous rate ≤ ``max_ambiguous_rate``, and the
    dominant units differ. A single valid row is never enough when
    ``min_valid_inferences > 1`` (default 5).

    When ``has_header`` is ``False``, the first row of each member is treated as
    data. ``timestamp_column`` must then be an integer column index (a string
    column name cannot be resolved against a header that is not present). The
    reported schema for headerless archives is an empty tuple, because there are
    no column names to inspect.
    """
    if max_sample_rows <= 0:
        raise ValueError("max_sample_rows must be positive")
    if min_valid_inferences < 1:
        raise ValueError("min_valid_inferences must be >= 1")
    if not (0.0 <= max_malformed_rate <= 1.0):
        raise ValueError("max_malformed_rate must be in [0, 1]")
    if not (0.0 <= max_ambiguous_rate <= 1.0):
        raise ValueError("max_ambiguous_rate must be in [0, 1]")
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

    if not has_header:
        if isinstance(timestamp_column, str):
            # Resolve from the first data row only so we can report a useful message.
            first_a = rows_a[0] if rows_a else ()
            first_b = rows_b[0] if rows_b else ()
            raise PrecisionComparisonError(
                "timestamp_column name cannot be resolved against a headerless archive; "
                "provide an integer column index",
                context={"column": timestamp_column, "sample_a": first_a, "sample_b": first_b},
            )
        schema_a = ()
        schema_b = ()

    def _ts_index(
        schema: tuple[str, ...],
        column: str | int,
        row_width: int | None = None,
    ) -> int:
        if isinstance(column, int):
            bound = row_width if row_width is not None else len(schema)
            if column < 0 or column >= bound:
                raise PrecisionComparisonError(
                    f"timestamp_column index {column} out of range",
                    context={"bound": bound},
                )
            return column
        if not schema:
            raise PrecisionComparisonError(
                "timestamp_column name cannot be resolved against a headerless archive; "
                "provide an integer index",
                context={"column": column},
            )
        if column not in schema:
            raise PrecisionComparisonError(
                f"timestamp column {column!r} not in schema",
                context={"schema": list(schema)},
            )
        return schema.index(column)

    width_a = len(rows_a[0]) if rows_a else 0
    width_b = len(rows_b[0]) if rows_b else 0
    idx_a = _ts_index(schema_a, timestamp_column, row_width=width_a)
    idx_b = _ts_index(schema_b, timestamp_column, row_width=width_b)

    def _analyze(
        rows: list[tuple[str, ...]],
        idx: int,
    ) -> tuple[tuple[str, ...], str | None, Mapping[str, int], int, int, int, int]:
        raw_samples: list[str] = []
        unit_counts: dict[str, int] = {}
        malformed = 0
        ambiguous = 0
        sampled = 0
        for row in rows[:max_sample_rows]:
            sampled += 1
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
                unit_counts[unit] = unit_counts.get(unit, 0) + 1
            except AmbiguousTimestampError:
                ambiguous += 1
            except OutOfRangeTimestampError:
                malformed += 1
            except Exception:
                malformed += 1

        valid = sum(unit_counts.values())
        dominant: str | None
        if not unit_counts:
            dominant = None
        else:
            dominant = sorted(unit_counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
        # Deterministic key order for distributions.
        distribution = {k: unit_counts[k] for k in sorted(unit_counts)}
        return (
            tuple(raw_samples[:10]),
            dominant,
            distribution,
            sampled,
            valid,
            malformed,
            ambiguous,
        )

    (
        rep_a,
        unit_a,
        dist_a,
        sampled_a,
        valid_a,
        mal_a,
        amb_a,
    ) = _analyze(rows_a, idx_a)
    (
        rep_b,
        unit_b,
        dist_b,
        sampled_b,
        valid_b,
        mal_b,
        amb_b,
    ) = _analyze(rows_b, idx_b)

    diffs = _schema_diff(schema_a, schema_b)
    if schema_a == () and schema_b == () and width_a != width_b:
        diffs = tuple(
            list(diffs)
            + [
                SchemaFieldDiff(
                    field_name="*",
                    side="both",
                    detail=f"Column count differs: A={width_a}, B={width_b}",
                )
            ]
        )

    supports = False
    rationale_parts: list[str] = []

    def _side_ok(label: str, valid: int, mal: int, amb: int, sampled: int) -> bool:
        ok = True
        if valid < min_valid_inferences:
            rationale_parts.append(
                f"{label}: valid inferences {valid} < min_valid_inferences "
                f"{min_valid_inferences}"
            )
            ok = False
        mal_rate = _rate(mal, sampled)
        amb_rate = _rate(amb, sampled)
        if mal_rate > max_malformed_rate:
            rationale_parts.append(
                f"{label}: malformed rate {mal_rate:.4f} > max_malformed_rate "
                f"{max_malformed_rate}"
            )
            ok = False
        if amb_rate > max_ambiguous_rate:
            rationale_parts.append(
                f"{label}: ambiguous rate {amb_rate:.4f} > max_ambiguous_rate "
                f"{max_ambiguous_rate}"
            )
            ok = False
        return ok

    a_ok = _side_ok("A", valid_a, mal_a, amb_a, sampled_a)
    b_ok = _side_ok("B", valid_b, mal_b, amb_b, sampled_b)

    if unit_a is None or unit_b is None:
        rationale_parts.append(
            "one or both archives lack a dominant inferred unit from sampled rows"
        )
    elif unit_a == unit_b:
        rationale_parts.append(
            f"both archives infer the same dominant unit ({unit_a}); "
            "no precision transition supported by this sample"
        )
    elif a_ok and b_ok:
        supports = True
        rationale_parts.append(
            f"sampled rows support a unit change from {unit_a} to {unit_b} "
            f"with valid_a={valid_a}, valid_b={valid_b}, "
            f"distributions A={dist_a} B={dist_b}"
        )
    else:
        rationale_parts.append(
            f"units differ ({unit_a} vs {unit_b}) but evidence thresholds not met"
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
        unit_distribution_a=dist_a,
        unit_distribution_b=dist_b,
        sampled_rows_a=sampled_a,
        sampled_rows_b=sampled_b,
        valid_inferences_a=valid_a,
        valid_inferences_b=valid_b,
        schema_a=schema_a,
        schema_b=schema_b,
        schema_differences=diffs,
        malformed_a=mal_a,
        malformed_b=mal_b,
        ambiguous_a=amb_a,
        ambiguous_b=amb_b,
        supports_timestamp_precision_transition=supports,
        transition_rationale="; ".join(rationale_parts),
        min_valid_inferences=min_valid_inferences,
        max_malformed_rate=max_malformed_rate,
        max_ambiguous_rate=max_ambiguous_rate,
    )
