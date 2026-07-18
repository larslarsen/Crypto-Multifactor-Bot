"""Focused synthetic tests for pagination."""

from source_audit.pagination import paginate


def fake_fetch_normal(cursor, limit):
    if cursor is None:
        return [{"id": 1}, {"id": 2}]
    return []


def test_normal_progression():
    result = paginate(fake_fetch_normal, max_pages=5)
    assert result.pages_fetched == 1
    assert len(result.records) == 2
    assert result.duplicates == 0
