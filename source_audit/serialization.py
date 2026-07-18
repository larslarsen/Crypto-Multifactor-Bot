"""Deterministic JSON/CSV serialization for audit results."""

import json
from pathlib import Path
from typing import Any
from .models import AuditReport


def to_json(report: AuditReport, path: Path) -> None:
    """Serialize report to JSON deterministically."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report.__dict__, f, indent=2, default=str, sort_keys=True)
