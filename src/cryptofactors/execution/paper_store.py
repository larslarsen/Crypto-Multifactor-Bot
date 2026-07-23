"""PAPER-003 — Paper Session Persistence Store.

Persists paper account snapshots (cash, positions, equity, timestamp) and trade records
to SQLite control database tables and/or JSONL files, enabling resume and auditability.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Final

from cryptofactors.execution.errors import PaperOpsError
from cryptofactors.execution.models import PaperAccountState, PaperTrade

_US_PER_SECOND: Final[int] = 1_000_000


def _dt_to_iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.isoformat()


def _parse_iso(iso_str: str) -> datetime:
    dt = datetime.fromisoformat(iso_str)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class PaperSessionStore:
    """SQLite-backed persistence repository for paper trading snapshots and trade records."""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path: Path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _ensure_schema(self) -> None:
        conn = self._get_connection()
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS paper_account_snapshot (
                    snapshot_id TEXT PRIMARY KEY,
                    model_artifact_id TEXT NOT NULL,
                    cash REAL NOT NULL,
                    equity REAL NOT NULL,
                    positions_json TEXT NOT NULL,
                    target_weights_json TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    timestamp_us INTEGER NOT NULL
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS paper_trade_record (
                    trade_id TEXT PRIMARY KEY,
                    model_artifact_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    base_price REAL NOT NULL,
                    effective_price REAL NOT NULL,
                    fee REAL NOT NULL,
                    notional REAL NOT NULL,
                    timestamp TEXT NOT NULL,
                    timestamp_us INTEGER NOT NULL
                );
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_paper_snap_model_ts ON paper_account_snapshot(model_artifact_id, timestamp_us);"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_paper_trade_model_ts ON paper_trade_record(model_artifact_id, timestamp_us);"
            )
            conn.commit()
        finally:
            conn.close()

    def save_snapshot(
        self,
        model_artifact_id: str,
        state: PaperAccountState,
        target_weights: dict[str, float] | None = None,
    ) -> str:
        """Save a paper account state snapshot."""
        if not model_artifact_id:
            raise PaperOpsError("model_artifact_id must be non-empty")

        snapshot_id = f"snap_{uuid.uuid4().hex[:16]}"
        ts_iso = _dt_to_iso(state.timestamp)
        ts_us = int(state.timestamp.timestamp() * _US_PER_SECOND)

        positions_json = json.dumps(state.positions)
        weights_json = json.dumps(target_weights or {})

        conn = self._get_connection()
        try:
            conn.execute(
                """
                INSERT INTO paper_account_snapshot (
                    snapshot_id, model_artifact_id, cash, equity,
                    positions_json, target_weights_json, timestamp, timestamp_us
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    snapshot_id,
                    model_artifact_id,
                    state.cash,
                    state.equity,
                    positions_json,
                    weights_json,
                    ts_iso,
                    ts_us,
                ),
            )
            conn.commit()
        finally:
            conn.close()

        return snapshot_id

    def save_trades(
        self,
        model_artifact_id: str,
        trades: Sequence[PaperTrade],
    ) -> None:
        """Save a sequence of executed paper trade records."""
        if not trades:
            return

        conn = self._get_connection()
        try:
            for tr in trades:
                ts_iso = _dt_to_iso(tr.timestamp)
                ts_us = int(tr.timestamp.timestamp() * _US_PER_SECOND)
                conn.execute(
                    """
                    INSERT OR REPLACE INTO paper_trade_record (
                        trade_id, model_artifact_id, symbol, side,
                        quantity, base_price, effective_price, fee, notional,
                        timestamp, timestamp_us
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        tr.trade_id,
                        model_artifact_id,
                        tr.symbol,
                        tr.side,
                        tr.quantity,
                        tr.base_price,
                        tr.effective_price,
                        tr.fee,
                        tr.notional,
                        ts_iso,
                        ts_us,
                    ),
                )
            conn.commit()
        finally:
            conn.close()

    def load_latest_snapshot(self, model_artifact_id: str) -> PaperAccountState | None:
        """Load the most recent PaperAccountState snapshot for model_artifact_id."""
        conn = self._get_connection()
        try:
            row = conn.execute(
                """
                SELECT * FROM paper_account_snapshot
                WHERE model_artifact_id = ?
                ORDER BY timestamp_us DESC, rowid DESC
                LIMIT 1;
                """,
                (model_artifact_id,),
            ).fetchone()

            if row is None:
                return None

            positions = json.loads(row["positions_json"])
            return PaperAccountState(
                cash=float(row["cash"]),
                positions={str(k): float(v) for k, v in positions.items()},
                equity=float(row["equity"]),
                timestamp=_parse_iso(row["timestamp"]),
            )
        finally:
            conn.close()

    def load_trade_history(self, model_artifact_id: str) -> list[PaperTrade]:
        """Load all executed trade records for model_artifact_id."""
        conn = self._get_connection()
        try:
            rows = conn.execute(
                """
                SELECT * FROM paper_trade_record
                WHERE model_artifact_id = ?
                ORDER BY timestamp_us ASC, rowid ASC;
                """,
                (model_artifact_id,),
            ).fetchall()

            trades: list[PaperTrade] = []
            for r in rows:
                trades.append(
                    PaperTrade(
                        trade_id=r["trade_id"],
                        symbol=r["symbol"],
                        side=r["side"],
                        quantity=float(r["quantity"]),
                        base_price=float(r["base_price"]),
                        effective_price=float(r["effective_price"]),
                        fee=float(r["fee"]),
                        notional=float(r["notional"]),
                        timestamp=_parse_iso(r["timestamp"]),
                    )
                )
            return trades
        finally:
            conn.close()
