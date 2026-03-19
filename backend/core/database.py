"""SQLite database connection and queries."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA = """
CREATE TABLE IF NOT EXISTS signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stream TEXT NOT NULL,
    source TEXT NOT NULL,
    instrument TEXT NOT NULL,
    direction TEXT NOT NULL,
    confidence REAL NOT NULL,
    reasoning TEXT,
    was_traded INTEGER DEFAULT 0,
    trade_id INTEGER,
    rejection_reason TEXT,
    is_comparison INTEGER DEFAULT 0,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stream TEXT NOT NULL,
    instrument TEXT NOT NULL,
    direction TEXT NOT NULL,
    entry_price REAL NOT NULL,
    exit_price REAL,
    stop_loss REAL NOT NULL,
    take_profit REAL NOT NULL,
    position_size REAL NOT NULL,
    pnl REAL,
    pnl_pips REAL,
    status TEXT DEFAULT 'open',
    signal_ids JSON,
    opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS equity_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stream TEXT NOT NULL,
    equity REAL NOT NULL,
    open_positions INTEGER NOT NULL,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS news_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    headline TEXT NOT NULL,
    source TEXT NOT NULL,
    url TEXT,
    summary TEXT,
    mapped_instruments JSON,
    published_at TIMESTAMP,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS hybrid_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    modules JSON NOT NULL,
    combiner_mode TEXT NOT NULL,
    instruments JSON NOT NULL,
    interval TEXT NOT NULL,
    is_active INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_signals_stream ON signals(stream, created_at);
CREATE INDEX IF NOT EXISTS idx_signals_instrument ON signals(instrument, created_at);
CREATE INDEX IF NOT EXISTS idx_trades_stream ON trades(stream, opened_at);
CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status);
CREATE INDEX IF NOT EXISTS idx_equity_stream ON equity_snapshots(stream, recorded_at);
"""


class Database:
    def __init__(self, db_path: str = "data/sentinel.db"):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._init_schema()

    def _init_schema(self):
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        return self.conn.execute(sql, params)

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()

    # ── Signals ──────────────────────────────────────────

    def insert_signal(self, **kwargs) -> int:
        metadata = kwargs.get("metadata")
        if isinstance(metadata, dict):
            kwargs["metadata"] = json.dumps(metadata)
        cols = ", ".join(kwargs.keys())
        placeholders = ", ".join(["?"] * len(kwargs))
        cur = self.execute(
            f"INSERT INTO signals ({cols}) VALUES ({placeholders})",
            tuple(kwargs.values()),
        )
        self.commit()
        return cur.lastrowid

    def get_signals(self, stream: str | None = None, limit: int = 50,
                    since: datetime | None = None) -> list[dict]:
        sql = "SELECT * FROM signals WHERE 1=1"
        params: list[Any] = []
        if stream:
            sql += " AND stream = ?"
            params.append(stream)
        if since:
            sql += " AND created_at >= ?"
            params.append(since.isoformat())
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        rows = self.execute(sql, tuple(params)).fetchall()
        return [self._row_to_dict(r) for r in rows]

    # ── Trades ───────────────────────────────────────────

    def insert_trade(self, **kwargs) -> int:
        signal_ids = kwargs.get("signal_ids")
        if isinstance(signal_ids, list):
            kwargs["signal_ids"] = json.dumps(signal_ids)
        cols = ", ".join(kwargs.keys())
        placeholders = ", ".join(["?"] * len(kwargs))
        cur = self.execute(
            f"INSERT INTO trades ({cols}) VALUES ({placeholders})",
            tuple(kwargs.values()),
        )
        self.commit()
        return cur.lastrowid

    def update_trade(self, trade_id: int, **kwargs):
        if "signal_ids" in kwargs and isinstance(kwargs["signal_ids"], list):
            kwargs["signal_ids"] = json.dumps(kwargs["signal_ids"])
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        self.execute(
            f"UPDATE trades SET {sets} WHERE id = ?",
            (*kwargs.values(), trade_id),
        )
        self.commit()

    def get_open_trades(self, stream: str | None = None) -> list[dict]:
        sql = "SELECT * FROM trades WHERE status = 'open'"
        params: list[Any] = []
        if stream:
            sql += " AND stream = ?"
            params.append(stream)
        sql += " ORDER BY opened_at DESC"
        rows = self.execute(sql, tuple(params)).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def get_trades(self, stream: str | None = None, limit: int = 100,
                   since: datetime | None = None) -> list[dict]:
        sql = "SELECT * FROM trades WHERE 1=1"
        params: list[Any] = []
        if stream:
            sql += " AND stream = ?"
            params.append(stream)
        if since:
            sql += " AND opened_at >= ?"
            params.append(since.isoformat())
        sql += " ORDER BY opened_at DESC LIMIT ?"
        params.append(limit)
        rows = self.execute(sql, tuple(params)).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def count_open_positions(self, stream: str) -> int:
        row = self.execute(
            "SELECT COUNT(*) as cnt FROM trades WHERE stream = ? AND status = 'open'",
            (stream,),
        ).fetchone()
        return row["cnt"] if row else 0

    # ── Equity ───────────────────────────────────────────

    def insert_equity_snapshot(self, stream: str, equity: float, open_positions: int):
        self.execute(
            "INSERT INTO equity_snapshots (stream, equity, open_positions) VALUES (?, ?, ?)",
            (stream, equity, open_positions),
        )
        self.commit()

    def get_equity_history(self, stream: str | None = None,
                           since: datetime | None = None) -> list[dict]:
        sql = "SELECT * FROM equity_snapshots WHERE 1=1"
        params: list[Any] = []
        if stream:
            sql += " AND stream = ?"
            params.append(stream)
        if since:
            sql += " AND recorded_at >= ?"
            params.append(since.isoformat())
        sql += " ORDER BY recorded_at ASC"
        rows = self.execute(sql, tuple(params)).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def get_stream_equity(self, stream: str) -> float:
        """Get latest equity for a stream, or default capital."""
        row = self.execute(
            "SELECT equity FROM equity_snapshots WHERE stream = ? ORDER BY recorded_at DESC LIMIT 1",
            (stream,),
        ).fetchone()
        if row:
            return row["equity"]
        return 33333.0  # default capital allocation

    # ── News ─────────────────────────────────────────────

    def insert_news_item(self, **kwargs) -> int:
        mapped = kwargs.get("mapped_instruments")
        if isinstance(mapped, list):
            kwargs["mapped_instruments"] = json.dumps(mapped)
        cols = ", ".join(kwargs.keys())
        placeholders = ", ".join(["?"] * len(kwargs))
        cur = self.execute(
            f"INSERT INTO news_items ({cols}) VALUES ({placeholders})",
            tuple(kwargs.values()),
        )
        self.commit()
        return cur.lastrowid

    def get_recent_news(self, hours: int = 4) -> list[dict]:
        sql = """SELECT * FROM news_items
                 WHERE fetched_at >= datetime('now', ?)
                 ORDER BY fetched_at DESC"""
        rows = self.execute(sql, (f"-{hours} hours",)).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def headline_exists(self, headline: str) -> bool:
        row = self.execute(
            "SELECT 1 FROM news_items WHERE headline = ? LIMIT 1",
            (headline,),
        ).fetchone()
        return row is not None

    # ── Hybrid Configs ───────────────────────────────────

    def insert_hybrid_config(self, **kwargs) -> int:
        for key in ("modules", "instruments"):
            if key in kwargs and isinstance(kwargs[key], list):
                kwargs[key] = json.dumps(kwargs[key])
        cols = ", ".join(kwargs.keys())
        placeholders = ", ".join(["?"] * len(kwargs))
        cur = self.execute(
            f"INSERT INTO hybrid_configs ({cols}) VALUES ({placeholders})",
            tuple(kwargs.values()),
        )
        self.commit()
        return cur.lastrowid

    def update_hybrid_config(self, config_id: int, **kwargs):
        for key in ("modules", "instruments"):
            if key in kwargs and isinstance(kwargs[key], list):
                kwargs[key] = json.dumps(kwargs[key])
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        self.execute(
            f"UPDATE hybrid_configs SET {sets} WHERE id = ?",
            (*kwargs.values(), config_id),
        )
        self.commit()

    def get_active_hybrids(self) -> list[dict]:
        rows = self.execute(
            "SELECT * FROM hybrid_configs WHERE is_active = 1"
        ).fetchall()
        result = []
        for r in rows:
            d = self._row_to_dict(r)
            if isinstance(d.get("modules"), str):
                d["modules"] = json.loads(d["modules"])
            if isinstance(d.get("instruments"), str):
                d["instruments"] = json.loads(d["instruments"])
            result.append(d)
        return result

    def get_all_hybrids(self) -> list[dict]:
        rows = self.execute(
            "SELECT * FROM hybrid_configs ORDER BY created_at DESC"
        ).fetchall()
        result = []
        for r in rows:
            d = self._row_to_dict(r)
            if isinstance(d.get("modules"), str):
                d["modules"] = json.loads(d["modules"])
            if isinstance(d.get("instruments"), str):
                d["instruments"] = json.loads(d["instruments"])
            result.append(d)
        return result

    def delete_hybrid_config(self, config_id: int):
        self.execute("DELETE FROM hybrid_configs WHERE id = ?", (config_id,))
        self.commit()

    # ── Helpers ──────────────────────────────────────────

    def get_daily_pnl(self, stream: str) -> float:
        """Sum of P&L for trades closed today."""
        row = self.execute(
            """SELECT COALESCE(SUM(pnl), 0) as total
               FROM trades
               WHERE stream = ? AND closed_at >= date('now')""",
            (stream,),
        ).fetchone()
        return row["total"] if row else 0.0

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict:
        return dict(row)
