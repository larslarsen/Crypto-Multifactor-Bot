"""Focused synthetic tests for the pagination framework."""

from __future__ import annotations

from typing import Any

import pytest

from source_audit.errors import PaginationError
from source_audit.models import BoundaryPolicy, PaginationMode
from source_audit.pagination import PaginationCallbacks, paginate

Record = dict[str, Any]


def _cbs(
    pages: list[list[Record]],
    *,
    is_gap: Any = None,
) -> PaginationCallbacks:
    """Build callbacks over a fixed list of pages. Cursor is page index."""

    def parse(raw: Any) -> list[Record]:
        return list(raw)

    def rid(rec: Record) -> tuple[Any, ...]:
        return (rec["id"],)

    def order(rec: Record) -> tuple[Any, ...]:
        return (rec["ts"], rec["id"])

    state = {"last_cursor": None}

    def fetch2(cursor: Any, limit: int) -> list[Record]:
        del limit
        idx = 0 if cursor is None else int(cursor)
        state["last_cursor"] = idx
        if idx < 0 or idx >= len(pages):
            return []
        return list(pages[idx])

    def next2(raw: Any, records: list[Record]) -> Any:
        del raw, records
        cur = state["last_cursor"]
        assert cur is not None
        nxt = cur + 1
        if nxt >= len(pages):
            return None
        return nxt

    return PaginationCallbacks(
        fetch_page=fetch2,
        parse_records=parse,
        record_id=rid,
        order_key=order,
        next_cursor=next2,
        time_boundary=lambda r: r["ts"],
        is_gap=is_gap,
    )


def test_normal_forward_progression() -> None:
    pages = [
        [{"id": 1, "ts": 1}, {"id": 2, "ts": 2}],
        [{"id": 3, "ts": 3}, {"id": 4, "ts": 4}],
    ]
    result = paginate(
        _cbs(pages),
        mode=PaginationMode.FORWARD_TIME,
        max_pages=10,
        max_records=100,
        raise_on_safety_violation=True,
    )
    assert result.diagnostics.pages_fetched == 2
    assert len(result.records) == 4
    assert result.diagnostics.overlap_count == 0


def test_cursor_loop_raises() -> None:
    def fetch(cursor: Any, limit: int) -> list[Record]:
        del limit
        # Always return same page content for cursor 0/1 alternating but same next cursor.
        return [{"id": 1, "ts": 1}]

    def next_c(raw: Any, records: list[Record]) -> Any:
        del raw, records
        return 0  # always same next cursor after first

    cbs = PaginationCallbacks(
        fetch_page=fetch,
        parse_records=lambda r: list(r),
        record_id=lambda r: (r["id"],),
        order_key=lambda r: (r["ts"],),
        next_cursor=next_c,
    )
    with pytest.raises(PaginationError, match="Repeated page|Repeated cursor|Non-progress"):
        paginate(cbs, start_cursor=None, max_pages=5)


def test_non_progress_cursor() -> None:
    # Distinct increasing order keys/ids per page so only non-progress fires.
    calls = {"n": 0}

    def fetch(cursor: Any, limit: int) -> list[Record]:
        del limit
        calls["n"] += 1
        n = calls["n"]
        return [{"id": n, "ts": n}]

    def next_c(raw: Any, records: list[Record]) -> Any:
        del raw, records
        # After first page (cursor None), return 0; thereafter stay at 0.
        return 0

    cbs = PaginationCallbacks(
        fetch_page=fetch,
        parse_records=lambda r: list(r),
        record_id=lambda r: (r["id"],),
        order_key=lambda r: (r["ts"],),
        next_cursor=next_c,
        page_fingerprint=lambda raw, recs: (recs[0]["id"],),
    )
    with pytest.raises(PaginationError, match="Non-progress"):
        paginate(cbs, max_pages=5)


def test_repeated_page_detection() -> None:
    def fetch(cursor: Any, limit: int) -> list[Record]:
        del limit
        return [{"id": 1, "ts": 1}]

    n = {"c": 0}

    def next_c(raw: Any, records: list[Record]) -> Any:
        del raw, records
        n["c"] += 1
        return n["c"]

    cbs = PaginationCallbacks(
        fetch_page=fetch,
        parse_records=lambda r: list(r),
        record_id=lambda r: (r["id"], n["c"]),
        order_key=lambda r: (r["ts"], n["c"]),
        next_cursor=next_c,
        # Same fingerprint every time.
        page_fingerprint=lambda raw, recs: ("same",),
    )
    with pytest.raises(PaginationError, match="Repeated page"):
        paginate(cbs, max_pages=5)


def test_within_page_reversed_order() -> None:
    pages = [[{"id": 2, "ts": 2}, {"id": 1, "ts": 1}]]
    with pytest.raises(PaginationError, match="Within-page order"):
        paginate(_cbs(pages), mode=PaginationMode.FORWARD_TIME, max_pages=5)


def test_boundary_duplicate_inclusive_reported() -> None:
    pages = [
        [{"id": 1, "ts": 1}, {"id": 2, "ts": 2}],
        [{"id": 2, "ts": 2}, {"id": 3, "ts": 3}],
    ]
    result = paginate(
        _cbs(pages),
        mode=PaginationMode.FORWARD_TIME,
        boundary_policy=BoundaryPolicy.INCLUSIVE,
        raise_on_safety_violation=False,
        max_pages=5,
    )
    assert result.diagnostics.boundary_duplicate_count >= 1
    assert any(o.kind == "boundary_duplicate" for o in result.overlaps)
    # No silent dedup: all records retained.
    assert len(result.records) == 4


def test_exclusive_boundary_overlap_flag() -> None:
    pages = [
        [{"id": 1, "ts": 1}, {"id": 2, "ts": 2}],
        [{"id": 2, "ts": 2}, {"id": 3, "ts": 3}],
    ]
    result = paginate(
        _cbs(pages),
        mode=PaginationMode.FORWARD_TIME,
        boundary_policy=BoundaryPolicy.EXCLUSIVE,
        raise_on_safety_violation=False,
        max_pages=5,
    )
    assert any(o.kind == "overlap" for o in result.overlaps)


def test_gap_not_inferred_without_policy() -> None:
    """Forward jumps are not gaps unless the caller supplies is_gap."""
    pages = [
        [{"id": 1, "ts": 1}, {"id": 2, "ts": 2}],
        [{"id": 5, "ts": 5}, {"id": 6, "ts": 6}],
    ]
    result = paginate(
        _cbs(pages),  # no is_gap
        mode=PaginationMode.FORWARD_TIME,
        raise_on_safety_violation=False,
        max_pages=5,
    )
    assert result.diagnostics.gap_count == 0
    assert result.gaps == ()


def test_gap_reporting_with_explicit_policy() -> None:
    pages = [
        [{"id": 1, "ts": 1}, {"id": 2, "ts": 2}],
        [{"id": 5, "ts": 5}, {"id": 6, "ts": 6}],
    ]

    def is_gap(prev: Any, nxt: Any) -> bool:
        return int(nxt) - int(prev) > 1

    result = paginate(
        _cbs(pages, is_gap=is_gap),
        mode=PaginationMode.FORWARD_TIME,
        raise_on_safety_violation=False,
        max_pages=5,
    )
    assert result.diagnostics.gap_count >= 1
    assert len(result.gaps) >= 1


def test_adjacent_boundaries_not_gap_under_policy() -> None:
    pages = [
        [{"id": 1, "ts": 1}, {"id": 2, "ts": 2}],
        [{"id": 3, "ts": 3}, {"id": 4, "ts": 4}],
    ]

    def is_gap(prev: Any, nxt: Any) -> bool:
        return int(nxt) - int(prev) > 1

    result = paginate(
        _cbs(pages, is_gap=is_gap),
        mode=PaginationMode.FORWARD_TIME,
        raise_on_safety_violation=False,
        max_pages=5,
    )
    assert result.diagnostics.gap_count == 0


def test_backward_time_order() -> None:
    pages = [
        [{"id": 4, "ts": 4}, {"id": 3, "ts": 3}],
        [{"id": 2, "ts": 2}, {"id": 1, "ts": 1}],
    ]
    result = paginate(
        _cbs(pages),
        mode=PaginationMode.BACKWARD_TIME,
        raise_on_safety_violation=True,
        max_pages=5,
    )
    assert result.diagnostics.pages_fetched == 2
    assert len(result.records) == 4


def test_backward_within_page_violation() -> None:
    pages = [[{"id": 1, "ts": 1}, {"id": 2, "ts": 2}]]  # ascending while backward expects desc
    with pytest.raises(PaginationError, match="backward_time"):
        paginate(_cbs(pages), mode=PaginationMode.BACKWARD_TIME, max_pages=5)


def test_max_records_bound() -> None:
    pages = [
        [{"id": i, "ts": i} for i in range(1, 6)],
        [{"id": i, "ts": i} for i in range(6, 11)],
    ]
    result = paginate(
        _cbs(pages),
        mode=PaginationMode.FORWARD_TIME,
        max_records=3,
        max_pages=10,
        raise_on_safety_violation=False,
    )
    assert len(result.records) == 3
    assert result.diagnostics.stopped_reason == "max_records"


def test_raw_page_retention() -> None:
    pages = [[{"id": 1, "ts": 1}]]
    result = paginate(
        _cbs(pages),
        retain_raw_pages=True,
        max_pages=5,
        raise_on_safety_violation=False,
    )
    assert len(result.raw_pages) == 1


def test_no_silent_dedup_overlap_records_kept() -> None:
    pages = [
        [{"id": 1, "ts": 1}],
        [{"id": 1, "ts": 1}],
    ]
    result = paginate(
        _cbs(pages),
        mode=PaginationMode.FORWARD_TIME,
        raise_on_safety_violation=False,
        max_pages=5,
    )
    assert len(result.records) == 2
    assert result.diagnostics.overlap_count >= 1
