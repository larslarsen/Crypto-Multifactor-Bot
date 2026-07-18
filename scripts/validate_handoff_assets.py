#!/usr/bin/env python3
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    for path in sorted((ROOT / "schemas").glob("*.schema.json")):
        json.loads(path.read_text(encoding="utf-8"))
    hypotheses = json.loads((ROOT / "research/evidence/hypotheses.yaml").read_text(encoding="utf-8"))
    ids = [item["hypothesis_id"] for item in hypotheses["hypotheses"]]
    if len(ids) != len(set(ids)):
        raise RuntimeError("duplicate hypothesis IDs")
    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA foreign_keys = ON")
    # The baseline control migration must be applied by the project before 0002.
    connection.executescript("""
    CREATE TABLE experiment_spec(fingerprint TEXT PRIMARY KEY);
    """)
    connection.executescript((ROOT / "sql/migrations/0002_evidence_registry.sql").read_text())
    connection.executescript((ROOT / "sql/views/evidence_views.sql").read_text())
    connection.close()
    print(f"validated {len(ids)} hypotheses, schemas, and evidence SQL")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
