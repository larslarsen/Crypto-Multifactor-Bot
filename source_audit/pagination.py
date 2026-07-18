"""Generic pagination engine with safety checks."""

from typing import Callable, Dict, List, Any, Optional, Tuple
from .errors import PaginationError
from .models import PaginationResult


def paginate(
    fetch_page: Callable[[Optional[Any], int], List[Dict]],
    start_cursor: Optional[Any] = None,
    max_pages: int = 100,
    limit: int = 1000,
    extract_cursor: Optional[Callable[[Dict], Any]] = None,
) -> PaginationResult:
    """
    Generic paginator with duplicate and progress detection.
    Provider-specific logic supplied via callbacks.
    """
    records: List[Dict] = []
    seen_cursors = set()
    seen_records = set()
    duplicates = 0
    pages = 0
    cursor = start_cursor

    while pages < max_pages:
        page = fetch_page(cursor, limit)
        pages += 1

        if not page:
            break

        for rec in page:
            key = tuple(rec.items()) if isinstance(rec, dict) else str(rec)
            if key in seen_records:
                duplicates += 1
            else:
                seen_records.add(key)
                records.append(rec)

        # Cursor update
        if extract_cursor and page:
            new_cursor = extract_cursor(page[-1])
            if new_cursor in seen_cursors:
                raise PaginationError("Repeated cursor detected")
            seen_cursors.add(new_cursor)
            cursor = new_cursor
        else:
            # Assume time-based or break if no progress
            break

    return PaginationResult(
        records=records,
        pages_fetched=pages,
        duplicates=duplicates,
        gaps=[],
        overlaps=[],
        ordering_violations=0,
    )
