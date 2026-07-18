"""Focused tests for deterministic serialization."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from pathlib import Path

import pytest

from source_audit.errors import SerializationError
from source_audit.models import TimestampUnit
from source_audit.serialization import dump_json, dumps_csv, dumps_json


class Color(Enum):
    RED = "red"


def test_dumps_json_deterministic_and_sorted() -> None:
    payload = {
        "z": 1,
        "a": Decimal("1.50"),
        "ts": datetime(2025, 1, 1, tzinfo=timezone.utc),
        "path": Path("foo/bar"),
        "unit": TimestampUnit.MILLISECONDS,
        "nested": {"b": 2, "a": 1},
        "tuple": (1, 2),
    }
    text1 = dumps_json(payload)
    text2 = dumps_json(payload)
    assert text1 == text2
    assert text1.index('"a"') < text1.index('"z"')
    assert "1.50" in text1
    assert "2025-01-01T00:00:00+00:00" in text1
    assert "foo/bar" in text1
    assert "ms" in text1


def test_reject_naive_datetime() -> None:
    with pytest.raises(SerializationError, match="naive"):
        dumps_json({"ts": datetime(2025, 1, 1)})


def test_reject_float() -> None:
    with pytest.raises(SerializationError, match="float"):
        dumps_json({"x": 1.2})


def test_reject_non_string_keys() -> None:
    with pytest.raises(SerializationError, match="string"):
        dumps_json({1: "x"})  # type: ignore[dict-item]


def test_reject_set() -> None:
    with pytest.raises(SerializationError, match="set"):
        dumps_json({"s": {1, 2}})


def test_atomic_dump_json(tmp_path: Path) -> None:
    path = tmp_path / "out.json"
    dump_json({"b": 2, "a": 1}, path)
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert text.index('"a"') < text.index('"b"')
    assert list(tmp_path.glob("*.partial")) == []


def test_csv_deterministic() -> None:
    text = dumps_csv(
        ["id", "px"],
        [(1, Decimal("1.5")), (2, Decimal("2.0"))],
    )
    assert text.splitlines()[0] == "id,px"
    assert "1.5" in text


def test_csv_nested_uses_canonical_json_not_str() -> None:
    import csv
    import io
    import json

    text = dumps_csv(
        ["id", "meta"],
        [(1, {"b": 2, "a": [1, Decimal("1.5")]})],
    )
    # Decode the CSV field first — the raw line has RFC-4180 doubled quotes.
    rows = list(csv.reader(io.StringIO(text)))
    assert rows[0] == ["id", "meta"]
    assert rows[1][0] == "1"
    meta_json = rows[1][1]
    assert "Decimal" not in meta_json
    assert "{'b'" not in meta_json
    decoded = json.loads(meta_json)
    assert decoded == {"a": [1, "1.5"], "b": 2}
    # Canonical form: sorted keys, compact separators.
    assert meta_json == json.dumps(
        {"a": [1, "1.5"], "b": 2},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
