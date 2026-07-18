"""Deterministic JSON/CSV serialization without lossy fallbacks."""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any

from .errors import SerializationError


def _normalize_for_json(value: Any) -> Any:
    """Convert supported values to JSON-safe, deterministic forms.

    Canonical representations
    -------------------------
    - ``datetime`` (UTC-aware) → ISO-8601 with ``+00:00`` offset
    - ``Decimal`` → normalized string via ``format(d, 'f')`` (no exponent)
    - ``Path`` → POSIX-style string (``as_posix()``)
    - ``Enum`` → ``.value`` (recursively normalized)
    - ``dataclass`` → dict of fields (sorted keys at dump time)
    - ``tuple`` / ``list`` → list
    - ``dict`` → requires string keys only
    - ``int``, ``str``, ``bool``, ``None`` → as-is
    - ``float`` → rejected (use Decimal)
    """
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value

    if isinstance(value, float):
        raise SerializationError(
            "float is not supported; use Decimal for numeric values",
            context={"value": repr(value)},
        )

    if isinstance(value, Decimal):
        if not value.is_finite():
            raise SerializationError("non-finite Decimal is not supported")
        return format(value, "f")

    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise SerializationError(
                "naive datetime is rejected; provide timezone-aware UTC",
                context={"value": str(value)},
            )
        utc = value.astimezone(timezone.utc)
        return utc.isoformat()

    if isinstance(value, Path):
        return value.as_posix()

    if isinstance(value, Enum):
        return _normalize_for_json(value.value)

    if is_dataclass(value) and not isinstance(value, type):
        return _normalize_for_json(asdict(value))

    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise SerializationError(
                    f"Mapping keys must be strings, got {type(key).__name__}",
                    context={"key": repr(key)},
                )
            out[key] = _normalize_for_json(item)
        return out

    if isinstance(value, (list, tuple)):
        return [_normalize_for_json(item) for item in value]

    if isinstance(value, set):
        raise SerializationError("set is not supported (unordered)")

    raise SerializationError(
        f"Unsupported type for deterministic serialization: {type(value).__name__}",
        context={"type": type(value).__name__},
    )


def dumps_json(value: Any, *, indent: int = 2) -> str:
    """Serialize ``value`` to a deterministic JSON string (sorted keys, stable format)."""
    normalized = _normalize_for_json(value)
    return json.dumps(
        normalized,
        indent=indent,
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,
    ) + "\n"


def dump_json(value: Any, path: Path, *, indent: int = 2) -> None:
    """Atomically write deterministic JSON to ``path``."""
    text = dumps_json(value, indent=indent)
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=".ser-",
        suffix=".json.partial",
        dir=destination.parent,
    )
    tmp_path: Path | None = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(str(tmp_path), str(destination))
        tmp_path = None  # published
    finally:
        if tmp_path is not None and tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


def dumps_csv(
    headers: Sequence[str],
    rows: Sequence[Sequence[Any]],
    *,
    delimiter: str = ",",
) -> str:
    """Serialize rows to deterministic CSV text (no quoting surprises for simple values).

    All cells are normalized via :func:`_normalize_for_json` then stringified.
    Fields containing the delimiter, quotes, or newlines are RFC-4180 quoted.
    """
    if not headers:
        raise SerializationError("CSV headers must be non-empty")
    if len(set(headers)) != len(headers):
        raise SerializationError("CSV headers must be unique")

    def _escape(cell: str) -> str:
        if any(c in cell for c in (delimiter, '"', "\n", "\r")):
            return '"' + cell.replace('"', '""') + '"'
        return cell

    lines: list[str] = [delimiter.join(_escape(h) for h in headers)]
    width = len(headers)
    for row in rows:
        if len(row) != width:
            raise SerializationError(
                "CSV row width mismatch",
                context={"expected": width, "observed": len(row)},
            )
        cells: list[str] = []
        for item in row:
            normalized = _normalize_for_json(item)
            if normalized is None:
                cells.append("")
            elif isinstance(normalized, bool):
                cells.append("true" if normalized else "false")
            else:
                cells.append(str(normalized))
        lines.append(delimiter.join(_escape(c) for c in cells))
    return "\n".join(lines) + "\n"


def dump_csv(
    headers: Sequence[str],
    rows: Sequence[Sequence[Any]],
    path: Path,
    *,
    delimiter: str = ",",
) -> None:
    """Atomically write deterministic CSV to ``path``."""
    text = dumps_csv(headers, rows, delimiter=delimiter)
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=".ser-",
        suffix=".csv.partial",
        dir=destination.parent,
    )
    tmp_path: Path | None = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(str(tmp_path), str(destination))
        tmp_path = None
    finally:
        if tmp_path is not None and tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
