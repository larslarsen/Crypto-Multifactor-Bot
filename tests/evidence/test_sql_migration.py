import sqlite3
from pathlib import Path


def test_evidence_migration_applies() -> None:
    root = Path(__file__).resolve().parents[2]
    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("CREATE TABLE experiment_spec(fingerprint TEXT PRIMARY KEY)")
    connection.executescript((root / "sql/migrations/0002_evidence_registry.sql").read_text())
    names = {
        row[0]
        for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }
    assert "hypothesis" in names
    assert "hypothesis_version" in names
    assert "hypothesis_decision_event" in names
