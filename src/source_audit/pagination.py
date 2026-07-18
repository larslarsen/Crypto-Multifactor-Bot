"""Generic pagination framework with safety checks and deterministic diagnostics.

Provider-specific request creation, response parsing, record identity, ordering keys,
cursors, and time boundaries are supplied through typed callbacks. The engine never
silently deduplicates records.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol, TypeVar

from .errors import PaginationError
from .models import (
    BoundaryPolicy,
    GapReport,
    OverlapReport,
    PaginationDiagnostics,
    PaginationMode,
    PaginationResult,
)

Record = Mapping[str, Any]
Cursor = Any
TPage = TypeVar("TPage")


class PageFetcher(Protocol):
    """Fetch one raw page given the current cursor and page limit."""

    def __call__(self, cursor: Cursor | None, limit: int) -> Any: ...


@dataclass(frozen=True, slots=True)
class PaginationCallbacks:
    """Provider-specific hooks for the pagination engine."""

    fetch_page: PageFetcher
    parse_records: Callable[[Any], Sequence[Record]]
    record_id: Callable[[Record], tuple[Any, ...]]
    order_key: Callable[[Record], tuple[Any, ...]]
    next_cursor: Callable[[Any, Sequence[Record]], Cursor | None]
    """Return the next cursor, or None when exhausted."""
    page_fingerprint: Callable[[Any, Sequence[Record]], tuple[Any, ...]] | None = None
    """Stable fingerprint of a page for repeated-page detection."""
    time_boundary: Callable[[Record], Any] | None = None
    """Optional time boundary extractor for time-mode gap/overlap checks."""


def _default_page_fingerprint(raw: Any, records: Sequence[Record]) -> tuple[Any, ...]:
    del raw
    return tuple(tuple(sorted(r.items())) for r in records)


def paginate(
    callbacks: PaginationCallbacks,
    *,
    mode: PaginationMode = PaginationMode.CURSOR,
    start_cursor: Cursor | None = None,
    max_pages: int = 100,
    max_records: int = 100_000,
    page_limit: int = 1000,
    boundary_policy: BoundaryPolicy = BoundaryPolicy.INCLUSIVE,
    raw_page_sink: Callable[[Any], None] | None = None,
    retain_raw_pages: bool = False,
    raise_on_safety_violation: bool = True,
) -> PaginationResult:
    """Run bounded pagination with progress, order, gap, and overlap diagnostics.

    Records are retained as observed. Duplicate identities are reported via overlap
    diagnostics and counts; they are **not** silently dropped.
    """
    if max_pages <= 0:
        raise ValueError("max_pages must be positive")
    if max_records <= 0:
        raise ValueError("max_records must be positive")
    if page_limit <= 0:
        raise ValueError("page_limit must be positive")

    records_out: list[Record] = []
    gaps: list[GapReport] = []
    overlaps: list[OverlapReport] = []
    raw_pages: list[Any] = []

    seen_cursors: set[Any] = set()
    seen_page_fps: set[tuple[Any, ...]] = set()
    seen_record_ids: dict[tuple[Any, ...], int] = {}

    repeated_cursor_events = 0
    non_progress_events = 0
    repeated_page_events = 0
    within_page_order_violations = 0
    across_page_order_violations = 0
    boundary_duplicate_count = 0

    cursor: Cursor | None = start_cursor
    pages_fetched = 0
    stopped_reason = "exhausted"
    prev_page_last_key: tuple[Any, ...] | None = None
    prev_page_last_id: tuple[Any, ...] | None = None
    prev_page_index = -1
    fingerprint_fn = callbacks.page_fingerprint or _default_page_fingerprint

    while pages_fetched < max_pages:
        if len(records_out) >= max_records:
            stopped_reason = "max_records"
            break

        try:
            raw_page = callbacks.fetch_page(cursor, page_limit)
        except PaginationError:
            raise
        except Exception as exc:
            raise PaginationError(
                f"Page fetch failed: {exc}",
                context={"page_index": pages_fetched, "cursor": cursor},
            ) from exc

        pages_fetched += 1
        if retain_raw_pages:
            raw_pages.append(raw_page)
        if raw_page_sink is not None:
            raw_page_sink(raw_page)

        page_records = list(callbacks.parse_records(raw_page))
        if not page_records:
            stopped_reason = "empty_page"
            break

        # Within-page stable order.
        for i in range(1, len(page_records)):
            prev_k = callbacks.order_key(page_records[i - 1])
            cur_k = callbacks.order_key(page_records[i])
            if mode is PaginationMode.BACKWARD_TIME:
                if cur_k > prev_k:
                    within_page_order_violations += 1
                    if raise_on_safety_violation:
                        raise PaginationError(
                            "Within-page order violation (backward_time)",
                            context={"page_index": pages_fetched - 1, "index": i},
                        )
            else:
                if cur_k < prev_k:
                    within_page_order_violations += 1
                    if raise_on_safety_violation:
                        raise PaginationError(
                            "Within-page order violation",
                            context={"page_index": pages_fetched - 1, "index": i},
                        )

        # Across-page order + boundary duplicates / gaps / overlaps.
        first_key = callbacks.order_key(page_records[0])
        first_id = callbacks.record_id(page_records[0])
        if prev_page_last_key is not None:
            if mode is PaginationMode.BACKWARD_TIME:
                if first_key > prev_page_last_key:
                    across_page_order_violations += 1
                    if raise_on_safety_violation:
                        raise PaginationError(
                            "Across-page order violation (backward_time)",
                            context={"page_index": pages_fetched - 1},
                        )
            else:
                if first_key < prev_page_last_key:
                    across_page_order_violations += 1
                    if raise_on_safety_violation:
                        raise PaginationError(
                            "Across-page order violation",
                            context={"page_index": pages_fetched - 1},
                        )

            # Boundary duplicate: first record of this page equals last of previous.
            if first_id == prev_page_last_id:
                boundary_duplicate_count += 1
                overlaps.append(
                    OverlapReport(
                        key=first_id,
                        previous_page_index=prev_page_index,
                        page_index=pages_fetched - 1,
                        kind="boundary_duplicate",
                    )
                )
                if boundary_policy is BoundaryPolicy.EXCLUSIVE:
                    # Caller expected exclusive boundaries; report as overlap.
                    overlaps.append(
                        OverlapReport(
                            key=first_id,
                            previous_page_index=prev_page_index,
                            page_index=pages_fetched - 1,
                            kind="overlap",
                        )
                    )
            elif mode is PaginationMode.FORWARD_TIME and callbacks.time_boundary is not None:
                # Gap heuristic: order keys strictly after previous without equality.
                if first_key > prev_page_last_key:
                    # Only report gap when keys are comparable and not adjacent by equality.
                    # Without a domain-specific adjacency function we report non-equal
                    # forward jumps as gaps for diagnostics.
                    gaps.append(
                        GapReport(
                            previous_key=prev_page_last_key,
                            next_key=first_key,
                            page_index=pages_fetched - 1,
                        )
                    )
            elif mode is PaginationMode.BACKWARD_TIME and callbacks.time_boundary is not None:
                if first_key < prev_page_last_key:
                    gaps.append(
                        GapReport(
                            previous_key=prev_page_last_key,
                            next_key=first_key,
                            page_index=pages_fetched - 1,
                        )
                    )

        # Overlap with any previously seen record id (no silent dedup).
        for rec in page_records:
            rid = callbacks.record_id(rec)
            if rid in seen_record_ids:
                overlaps.append(
                    OverlapReport(
                        key=rid,
                        previous_page_index=seen_record_ids[rid],
                        page_index=pages_fetched - 1,
                        kind="overlap",
                    )
                )
            else:
                seen_record_ids[rid] = pages_fetched - 1
            records_out.append(dict(rec))
            if len(records_out) >= max_records:
                stopped_reason = "max_records"
                break

        # Repeated-page detection.
        fp = fingerprint_fn(raw_page, page_records)
        if fp in seen_page_fps:
            repeated_page_events += 1
            if raise_on_safety_violation:
                raise PaginationError(
                    "Repeated page detected",
                    context={"page_index": pages_fetched - 1},
                )
        seen_page_fps.add(fp)

        # Cursor progression.
        next_c = callbacks.next_cursor(raw_page, page_records)
        if next_c is None:
            stopped_reason = "no_next_cursor"
            break

        # Non-progress: cursor unchanged.
        if next_c == cursor:
            non_progress_events += 1
            if raise_on_safety_violation:
                raise PaginationError(
                    "Non-progress: cursor did not advance",
                    context={"cursor": cursor, "page_index": pages_fetched - 1},
                )
            stopped_reason = "non_progress"
            break

        # Repeated cursor over the session.
        # For cursor mode, the *next* cursor must not have been used as a start before.
        cursor_key = _cursor_key(next_c)
        if cursor_key in seen_cursors:
            repeated_cursor_events += 1
            if raise_on_safety_violation:
                raise PaginationError(
                    "Repeated cursor detected",
                    context={"cursor": next_c, "page_index": pages_fetched - 1},
                )
        if cursor is not None:
            seen_cursors.add(_cursor_key(cursor))
        seen_cursors.add(cursor_key)

        prev_page_last_key = callbacks.order_key(page_records[-1])
        prev_page_last_id = callbacks.record_id(page_records[-1])
        prev_page_index = pages_fetched - 1
        cursor = next_c

        if stopped_reason == "max_records":
            break
    else:
        if pages_fetched >= max_pages:
            stopped_reason = "max_pages"

    diagnostics = PaginationDiagnostics(
        mode=mode,
        pages_fetched=pages_fetched,
        records_yielded=len(records_out),
        max_pages=max_pages,
        max_records=max_records,
        repeated_cursor_events=repeated_cursor_events,
        non_progress_events=non_progress_events,
        repeated_page_events=repeated_page_events,
        within_page_order_violations=within_page_order_violations,
        across_page_order_violations=across_page_order_violations,
        boundary_duplicate_count=boundary_duplicate_count,
        gap_count=len(gaps),
        overlap_count=len(overlaps),
        stopped_reason=stopped_reason,
    )
    return PaginationResult(
        records=tuple(records_out),
        diagnostics=diagnostics,
        gaps=tuple(gaps),
        overlaps=tuple(overlaps),
        raw_pages=tuple(raw_pages),
    )


def _cursor_key(cursor: Any) -> Any:
    if isinstance(cursor, (str, int, float, bool, type(None))):
        return cursor
    if isinstance(cursor, tuple):
        return cursor
    if isinstance(cursor, list):
        return tuple(cursor)
    if isinstance(cursor, dict):
        return tuple(sorted(cursor.items()))
    return str(cursor)
