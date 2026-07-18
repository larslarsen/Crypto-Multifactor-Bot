"""Focused tests for bar reconstruction."""

from source_audit.bars import reconstruct_bars


def test_empty_trades():
    assert reconstruct_bars([]) == []
