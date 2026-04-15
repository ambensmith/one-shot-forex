"""SQLite database — schema, queries, and prompt seeding."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ── Schema ──────────────────────────────────────────────────

CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS headlines (
    id TEXT PRIMARY KEY,
    headline TEXT NOT NULL,
    summary TEXT,
    content TEXT,
    source TEXT NOT NULL,
    source_url TEXT,
    image_url TEXT,
    category TEXT,
    published_at TIMESTAMP,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sentiment_score REAL,
    source_metadata JSON
);

CREATE TABLE IF NOT EXISTS relevance_assessments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    headline_id TEXT NOT NULL REFERENCES headlines(id),
    instrument TEXT NOT NULL,
    relevance_reasoning TEXT,
    prompt_version TEXT,
    model TEXT,
    run_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS signals (
    id TEXT PRIMARY KEY,
    run_id TEXT,
    source TEXT NOT NULL,
    instrument TEXT NOT NULL,
    direction TEXT NOT NULL,
    confidence REAL NOT NULL,
    reasoning TEXT,
    key_factors JSON,
    risk_factors JSON,
    headlines_used JSON,
    prompt_version TEXT,
    model TEXT,
    price_context JSON,
    challenge_output JSON,
    bias_check JSON,
    risk_check JSON,
    was_traded INTEGER DEFAULT 0,
    trade_id TEXT,
    status TEXT DEFAULT 'pending',
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS trades (
    id TEXT PRIMARY KEY,
    broker_deal_id TEXT,
    instrument TEXT NOT NULL,
    direction TEXT NOT NULL,
    size REAL,
    entry_price REAL NOT NULL,
    stop_loss REAL,
    take_profit REAL,
    exit_price REAL,
    pnl REAL,
    pnl_pips REAL,
    status TEXT DEFAULT 'open',
    source TEXT,
    signal_id TEXT,
    opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP,
    close_reason TEXT
);

CREATE TABLE IF NOT EXISTS trade_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_id TEXT NOT NULL UNIQUE REFERENCES trades(id),
    record JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS bias_state (
    instrument TEXT PRIMARY KEY,
    current_bias TEXT,
    bias_strength REAL,
    bias_since TIMESTAMP,
    contributing_signals JSON,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS prompts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    template TEXT NOT NULL,
    version TEXT NOT NULL,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS equity_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stream TEXT NOT NULL,
    equity REAL NOT NULL,
    open_positions INTEGER DEFAULT 0,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    market_open INTEGER DEFAULT 1,
    stages_run JSON,
    signals_generated JSON,
    trades_opened JSON,
    status TEXT DEFAULT 'running'
);

CREATE TABLE IF NOT EXISTS config_overrides (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NOT NULL UNIQUE,
    value JSON NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS trade_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    data JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS candles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    instrument TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    volume INTEGER DEFAULT 0,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(instrument, timestamp)
);

CREATE TABLE IF NOT EXISTS price_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    instrument TEXT NOT NULL,
    bid REAL NOT NULL,
    ask REAL NOT NULL,
    mid REAL NOT NULL,
    daily_change_pct REAL,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_headlines_published ON headlines(published_at);
CREATE INDEX IF NOT EXISTS idx_headlines_source ON headlines(source);
CREATE INDEX IF NOT EXISTS idx_relevance_headline ON relevance_assessments(headline_id);
CREATE INDEX IF NOT EXISTS idx_relevance_instrument ON relevance_assessments(instrument, created_at);
CREATE INDEX IF NOT EXISTS idx_signals_instrument ON signals(instrument, created_at);
CREATE INDEX IF NOT EXISTS idx_signals_run ON signals(run_id);
CREATE INDEX IF NOT EXISTS idx_signals_status ON signals(status);
CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status);
CREATE INDEX IF NOT EXISTS idx_trades_instrument ON trades(instrument, opened_at);
CREATE INDEX IF NOT EXISTS idx_trades_deal ON trades(broker_deal_id);
CREATE INDEX IF NOT EXISTS idx_equity_stream ON equity_snapshots(stream, recorded_at);
CREATE INDEX IF NOT EXISTS idx_trade_events_trade ON trade_events(trade_id, created_at);
CREATE INDEX IF NOT EXISTS idx_runs_started ON runs(started_at);
CREATE INDEX IF NOT EXISTS idx_candles_instrument_ts ON candles(instrument, timestamp);
CREATE INDEX IF NOT EXISTS idx_price_snapshots_instrument ON price_snapshots(instrument, fetched_at);
"""

# Tables that get dropped on fresh init (config_overrides and trade_events are preserved)
DROPPABLE_TABLES = [
    "headlines", "relevance_assessments", "signals", "trades",
    "trade_records", "bias_state", "prompts", "equity_snapshots", "runs",
    "candles", "price_snapshots",
]

# ── Seed prompts ────────────────────────────────────────────

SEED_PROMPTS = [
    {
        "name": "relevance_v1",
        "version": "v1",
        "template": (
            "You are a forex market analyst. Given these recent headlines, identify which\n"
            "of our instruments each headline is relevant to, and why.\n"
            "\n"
            "Instruments: EUR/USD, GBP/USD, USD/JPY, USD/CHF, AUD/USD, USD/CAD, EUR/GBP, XAU/USD\n"
            "\n"
            "News items (headline + summary/content where available):\n"
            "{news_items_formatted}\n"
            "\n"
            "For each item, respond with:\n"
            "- relevant_instruments: list of instrument codes\n"
            "- relevance_reasoning: why this affects each instrument\n"
            "- Skip items that are not relevant to any instrument.\n"
            "\n"
            "[Respond in valid JSON format as an object with key \"assessments\" containing an array]"
        ),
    },
    {
        "name": "signal_v1",
        "version": "v1",
        "template": (
            "You are a forex trading analyst. Based on the following recent news and market\n"
            "context for {instrument}, provide a trading signal.\n"
            "\n"
            "Recent relevant news (headlines, summaries, and content where available):\n"
            "{relevant_news_with_reasoning}\n"
            "\n"
            "Market context:\n"
            "- Current price: {current_price}\n"
            "- 24h change: {daily_change_pct}%\n"
            "- Recent trend: {trend_description}\n"
            "\n"
            "Reason through:\n"
            "1. What fundamental factors are these headlines affecting?\n"
            "2. What is the likely directional impact on {instrument}?\n"
            "3. How strong is the evidence (multiple confirming sources, or single ambiguous headline)?\n"
            "4. What could go wrong with this view?\n"
            "\n"
            "Respond with:\n"
            "- direction: \"long\" | \"short\" | \"neutral\"\n"
            "- confidence: 0.0-1.0 (how strong is the evidence, not how certain you are)\n"
            "- reasoning: your full analysis\n"
            "- key_factors: list of the main drivers\n"
            "- risk_factors: what could invalidate this signal\n"
            "\n"
            "[Respond in valid JSON format]"
        ),
    },
    {
        "name": "challenge_v1",
        "version": "v1",
        "template": (
            "You are a senior risk analyst reviewing a proposed trade. Your job is to argue\n"
            "against this position and find weaknesses in the reasoning.\n"
            "\n"
            "Proposed trade: {direction} {instrument}\n"
            "Signal reasoning: {reasoning}\n"
            "Key factors cited: {key_factors}\n"
            "Risk factors already identified: {risk_factors}\n"
            "\n"
            "Market context:\n"
            "- Current price: {current_price}\n"
            "- 24h change: {daily_change_pct}%\n"
            "- Recent trend: {trend_description}\n"
            "\n"
            "Challenge this trade:\n"
            "1. What is the strongest argument against this direction?\n"
            "2. Are there alternative interpretations of the same news?\n"
            "3. What market conditions could make this trade fail quickly?\n"
            "4. How convincing is the original reasoning on a scale of 0.0-1.0?\n"
            "\n"
            "Respond with:\n"
            "- counter_argument: your strongest case against the trade\n"
            "- alternative_interpretation: a different reading of the same evidence\n"
            "- conviction_after_challenge: 0.0-1.0 (how strong does the original signal look after scrutiny?)\n"
            "- recommendation: \"proceed\" | \"reduce_size\" | \"reject\"\n"
            "\n"
            "[Respond in valid JSON format]"
        ),
    },
]


# ── Database class ──────────────────────────────────────────


class Database:
    def __init__(self, db_path: str = "data/sentinel.db"):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._ensure_tables()

    def _ensure_tables(self):
        """Create tables and indexes if they don't exist. Safe for every startup."""
        self.conn.executescript(CREATE_TABLES)
        # Indexes may fail if old tables have different columns; ignore safely
        for line in CREATE_INDEXES.strip().split(";"):
            line = line.strip()
            if line:
                try:
                    self.conn.execute(line)
                except sqlite3.OperationalError:
                    pass
        self.conn.commit()

    def init_db(self, fresh: bool = False):
        """Initialize database. If fresh=True, drop and recreate rebuilt tables."""
        if fresh:
            for table in DROPPABLE_TABLES:
                self.conn.execute(f"DROP TABLE IF EXISTS {table}")
            self.conn.commit()
            # Recreate tables and indexes on the fresh schema
            self.conn.executescript(CREATE_TABLES)
            self.conn.executescript(CREATE_INDEXES)
            self.conn.commit()
        else:
            self._ensure_tables()
        self._seed_prompts()

    def _seed_prompts(self):
        """Insert seed prompts using INSERT OR IGNORE (idempotent)."""
        for p in SEED_PROMPTS:
            self.conn.execute(
                "INSERT OR IGNORE INTO prompts (name, template, version) VALUES (?, ?, ?)",
                (p["name"], p["template"], p["version"]),
            )
        self.conn.commit()

    # ── Generic helpers ─────────────────────────────────────

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        return self.conn.execute(sql, params)

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()

    def insert(self, table: str, data: dict[str, Any]) -> sqlite3.Cursor:
        """Generic insert. JSON-serializes dict/list values."""
        prepared = {}
        for k, v in data.items():
            if isinstance(v, (dict, list)):
                prepared[k] = json.dumps(v)
            elif isinstance(v, bool):
                prepared[k] = int(v)
            else:
                prepared[k] = v
        cols = ", ".join(prepared.keys())
        placeholders = ", ".join(["?"] * len(prepared))
        return self.conn.execute(
            f"INSERT INTO {table} ({cols}) VALUES ({placeholders})",
            tuple(prepared.values()),
        )

    def query(self, sql: str, params: tuple = ()) -> list[dict]:
        rows = self.conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict:
        return dict(row)

    # ── Headlines ───────────────────────────────────────────

    def insert_headline(self, headline) -> str:
        """Insert a Headline model. Returns the headline id."""
        data = headline.to_db_dict()
        self.insert("headlines", data)
        self.commit()
        return data["id"]

    def headline_exists(self, headline_text: str) -> bool:
        row = self.execute(
            "SELECT 1 FROM headlines WHERE headline = ? LIMIT 1",
            (headline_text,),
        ).fetchone()
        return row is not None

    def get_recent_headlines(self, hours: int = 4) -> list[dict]:
        rows = self.execute(
            "SELECT * FROM headlines WHERE ingested_at >= datetime('now', ?) ORDER BY ingested_at DESC",
            (f"-{hours} hours",),
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Relevance assessments ───────────────────────────────

    def insert_relevance(self, assessment) -> int:
        """Insert a RelevanceAssessment model. Returns the row id."""
        data = assessment.to_db_dict()
        data.pop("id", None)
        cur = self.insert("relevance_assessments", data)
        self.commit()
        return cur.lastrowid

    def get_relevance_assessments(self, run_id: str | None = None,
                                  instrument: str | None = None,
                                  limit: int = 50) -> list[dict]:
        """Query relevance assessments with optional filters."""
        sql = "SELECT * FROM relevance_assessments WHERE 1=1"
        params: list[Any] = []
        if run_id:
            sql += " AND run_id = ?"
            params.append(run_id)
        if instrument:
            sql += " AND instrument = ?"
            params.append(instrument)
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        return self.query(sql, tuple(params))

    def get_relevant_headlines_by_instrument(self, hours: int = 4) -> dict[str, list[dict]]:
        """Get recent relevant headlines grouped by instrument.

        JOINs relevance_assessments with headlines to return full headline
        data alongside the relevance reasoning, grouped by instrument.
        """
        sql = """
            SELECT r.instrument, r.relevance_reasoning,
                   h.id AS headline_id, h.headline, h.summary, h.content,
                   h.source, h.published_at
            FROM relevance_assessments r
            JOIN headlines h ON r.headline_id = h.id
            WHERE r.created_at >= datetime('now', ?)
            ORDER BY r.instrument, h.published_at DESC
        """
        rows = self.query(sql, (f"-{hours} hours",))
        grouped: dict[str, list[dict]] = {}
        for row in rows:
            inst = row["instrument"]
            grouped.setdefault(inst, []).append(dict(row))
        return grouped

    # ── Signals ─────────────────────────────────────────────

    def insert_signal(self, signal=None, **kwargs) -> str | int:
        """Insert a signal. Accepts a Signal model or keyword args (legacy)."""
        if signal is not None:
            data = signal.to_db_dict()
            self.insert("signals", data)
            self.commit()
            return data["id"]
        # Legacy kwargs path (used by base_stream.record_signal)
        for k, v in kwargs.items():
            if isinstance(v, (dict, list)):
                kwargs[k] = json.dumps(v)
        cols = ", ".join(kwargs.keys())
        placeholders = ", ".join(["?"] * len(kwargs))
        cur = self.execute(
            f"INSERT INTO signals ({cols}) VALUES ({placeholders})",
            tuple(kwargs.values()),
        )
        self.commit()
        return cur.lastrowid

    def get_recent_llm_signal_instruments(self, hours: int = 4) -> set[str]:
        """Return instruments that already have an LLM signal within the lookback window."""
        sql = """
            SELECT DISTINCT instrument FROM signals
            WHERE source = 'llm' AND created_at >= datetime('now', ?)
        """
        rows = self.query(sql, (f"-{hours} hours",))
        return {r["instrument"] for r in rows}

    def update_signal(self, signal_id: str, **kwargs):
        for k, v in kwargs.items():
            if isinstance(v, (dict, list)):
                kwargs[k] = json.dumps(v)
            elif isinstance(v, bool):
                kwargs[k] = int(v)
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        self.execute(f"UPDATE signals SET {sets} WHERE id = ?", (*kwargs.values(), signal_id))
        self.commit()

    def get_signals(self, stream: str | None = None, *, instrument: str | None = None,
                    run_id: str | None = None, status: str | None = None,
                    source: str | None = None, since: Any = None,
                    limit: int = 50) -> list[dict]:
        """Query signals.

        First positional arg ``stream`` is the legacy stream filter that maps
        to the source column: 'news' → source='llm', 'strategy' → source LIKE 'strategy:%'.
        Use keyword args for all other filters.
        """
        sql = "SELECT * FROM signals WHERE 1=1"
        params: list[Any] = []
        # Resolve stream alias to source filter
        effective_source = source
        if stream and not effective_source:
            if stream == "news":
                effective_source = "llm"
            elif stream == "strategy":
                effective_source = "strategy:*"
            else:
                effective_source = stream
        if instrument:
            sql += " AND instrument = ?"
            params.append(instrument)
        if run_id:
            sql += " AND run_id = ?"
            params.append(run_id)
        if status:
            sql += " AND status = ?"
            params.append(status)
        if effective_source:
            if effective_source.endswith(":*"):
                sql += " AND source LIKE ?"
                params.append(effective_source[:-1] + "%")
            else:
                sql += " AND source = ?"
                params.append(effective_source)
        if since:
            ts = since.isoformat() if hasattr(since, "isoformat") else str(since)
            sql += " AND created_at >= ?"
            params.append(ts)
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        return self.query(sql, tuple(params))

    # ── Trades ──────────────────────────────────────────────

    def insert_trade(self, trade) -> str:
        """Insert a Trade model. Returns the trade id."""
        data = trade.to_db_dict()
        self.insert("trades", data)
        self.commit()
        return data["id"]

    def update_trade(self, trade_id: str, **kwargs):
        for k, v in kwargs.items():
            if isinstance(v, (dict, list)):
                kwargs[k] = json.dumps(v)
            elif isinstance(v, bool):
                kwargs[k] = int(v)
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        self.execute(f"UPDATE trades SET {sets} WHERE id = ?", (*kwargs.values(), trade_id))
        self.commit()

    def get_open_trades(self, stream_or_instrument: str | None = None) -> list[dict]:
        """Get open trades. If the argument looks like a stream id (e.g. 'news',
        'strategy', 'hybrid:X'), filter by source. Otherwise filter by instrument."""
        sql = "SELECT * FROM trades WHERE status = 'open'"
        params: list[Any] = []
        if stream_or_instrument:
            if stream_or_instrument in ("news", "strategy") or ":" in stream_or_instrument:
                # Stream id → filter by source column
                sql += " AND source = ?"
                params.append(stream_or_instrument)
            else:
                # Instrument → filter by instrument column
                sql += " AND instrument = ?"
                params.append(stream_or_instrument)
        sql += " ORDER BY opened_at DESC"
        return self.query(sql, tuple(params))

    def get_open_trades_by_source(self, source: str | None = None) -> list[dict]:
        """Get open trades filtered by source (stream)."""
        sql = "SELECT * FROM trades WHERE status = 'open'"
        params: list[Any] = []
        if source:
            sql += " AND source = ?"
            params.append(source)
        sql += " ORDER BY opened_at DESC"
        return self.query(sql, tuple(params))

    def get_trades(self, stream: str | None = None, limit: int = 100,
                   since: Any = None) -> list[dict]:
        """Get trades. ``stream`` filters by the source column (trades store
        stream_id as source: 'news', 'strategy', 'hybrid:X')."""
        sql = "SELECT * FROM trades WHERE 1=1"
        params: list[Any] = []
        if stream:
            sql += " AND source = ?"
            params.append(stream)
        if since:
            ts = since.isoformat() if hasattr(since, "isoformat") else str(since)
            sql += " AND opened_at >= ?"
            params.append(ts)
        sql += " ORDER BY opened_at DESC LIMIT ?"
        params.append(limit)
        return self.query(sql, tuple(params))

    def get_trade_by_deal_id(self, broker_deal_id: str) -> dict | None:
        row = self.execute(
            "SELECT * FROM trades WHERE broker_deal_id = ? LIMIT 1",
            (broker_deal_id,),
        ).fetchone()
        return dict(row) if row else None

    def get_closed_trades(self, outcome: str | None = None,
                          instrument: str | None = None,
                          source: str | None = None,
                          days: int | None = None,
                          limit: int = 50) -> list[dict]:
        """Get closed trades with optional filters."""
        sql = "SELECT * FROM trades WHERE status != 'open'"
        params: list[Any] = []
        if outcome == "won":
            sql += " AND pnl > 0"
        elif outcome == "lost":
            sql += " AND pnl <= 0"
        if instrument:
            sql += " AND instrument = ?"
            params.append(instrument)
        if source:
            sql += " AND source = ?"
            params.append(source)
        if days:
            sql += " AND closed_at >= datetime('now', ?)"
            params.append(f"-{days} days")
        sql += " ORDER BY closed_at DESC LIMIT ?"
        params.append(limit)
        return self.query(sql, tuple(params))

    def get_latest_prices(self) -> dict[str, dict]:
        """Get the most recent price snapshot for each instrument."""
        sql = """
            SELECT p.* FROM price_snapshots p
            INNER JOIN (
                SELECT instrument, MAX(fetched_at) as max_fetched
                FROM price_snapshots GROUP BY instrument
            ) latest ON p.instrument = latest.instrument
                    AND p.fetched_at = latest.max_fetched
        """
        rows = self.query(sql)
        return {r["instrument"]: r for r in rows}

    def get_relevance_with_headlines(self, hours: int = 4, limit: int = 200) -> list[dict]:
        """Get relevance assessments joined with headline text."""
        sql = """
            SELECT r.id, r.headline_id, r.instrument, r.relevance_reasoning,
                   r.prompt_version, r.model, r.run_id, r.created_at,
                   h.headline, h.summary, h.source AS headline_source
            FROM relevance_assessments r
            JOIN headlines h ON r.headline_id = h.id
            WHERE r.created_at >= datetime('now', ?)
            ORDER BY r.created_at DESC LIMIT ?
        """
        return self.query(sql, (f"-{hours} hours", limit))

    def count_open_positions(self, source: str | None = None) -> int:
        if source:
            row = self.execute(
                "SELECT COUNT(*) as cnt FROM trades WHERE status = 'open' AND source = ?",
                (source,),
            ).fetchone()
        else:
            row = self.execute("SELECT COUNT(*) as cnt FROM trades WHERE status = 'open'").fetchone()
        return row["cnt"] if row else 0

    # ── Trade records ───────────────────────────────────────

    def insert_trade_record(self, trade_record) -> int:
        data = trade_record.to_db_dict()
        data.pop("id", None)
        cur = self.insert("trade_records", data)
        self.commit()
        return cur.lastrowid

    def get_trade_record(self, trade_id: str) -> dict | None:
        row = self.execute(
            "SELECT * FROM trade_records WHERE trade_id = ? LIMIT 1",
            (trade_id,),
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        if isinstance(d.get("record"), str):
            d["record"] = json.loads(d["record"])
        return d

    # ── Bias state ──────────────────────────────────────────

    def upsert_bias_state(self, bias) -> str:
        """Insert or update bias state for an instrument."""
        data = bias.to_db_dict()
        self.execute(
            """INSERT INTO bias_state (instrument, current_bias, bias_strength, bias_since, contributing_signals, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(instrument) DO UPDATE SET
                 current_bias = excluded.current_bias,
                 bias_strength = excluded.bias_strength,
                 bias_since = excluded.bias_since,
                 contributing_signals = excluded.contributing_signals,
                 updated_at = excluded.updated_at""",
            (
                data["instrument"],
                data.get("current_bias"),
                data.get("bias_strength"),
                data.get("bias_since"),
                data.get("contributing_signals"),
                data.get("updated_at"),
            ),
        )
        self.commit()
        return data["instrument"]

    def get_bias_state(self, instrument: str | None = None) -> list[dict]:
        if instrument:
            return self.query("SELECT * FROM bias_state WHERE instrument = ?", (instrument,))
        return self.query("SELECT * FROM bias_state ORDER BY instrument")

    # ── Prompts ─────────────────────────────────────────────

    def get_active_prompt(self, name: str) -> dict | None:
        row = self.execute(
            "SELECT * FROM prompts WHERE name = ? AND is_active = 1 LIMIT 1",
            (name,),
        ).fetchone()
        return dict(row) if row else None

    def get_all_prompts(self) -> list[dict]:
        return self.query("SELECT * FROM prompts ORDER BY name")

    def update_prompt(self, name: str, template: str, version: str):
        now = datetime.now(timezone.utc).isoformat()
        self.execute(
            "UPDATE prompts SET template = ?, version = ?, updated_at = ? WHERE name = ?",
            (template, version, now, name),
        )
        self.commit()

    # ── Equity snapshots ────────────────────────────────────

    def insert_equity_snapshot(self, snapshot_or_stream, equity: float | None = None,
                               open_positions: int | None = None) -> int:
        """Insert equity snapshot. Accepts an EquitySnapshot model or positional args (legacy)."""
        if equity is not None:
            # Legacy positional path: insert_equity_snapshot(stream, equity, open_positions)
            self.execute(
                "INSERT INTO equity_snapshots (stream, equity, open_positions) VALUES (?, ?, ?)",
                (snapshot_or_stream, equity, open_positions or 0),
            )
            self.commit()
            return self.execute("SELECT last_insert_rowid()").fetchone()[0]
        # Model path
        data = snapshot_or_stream.to_db_dict()
        data.pop("id", None)
        cur = self.insert("equity_snapshots", data)
        self.commit()
        return cur.lastrowid

    def get_equity_history(self, stream: str | None = None,
                           since: Any = None) -> list[dict]:
        sql = "SELECT * FROM equity_snapshots WHERE 1=1"
        params: list[Any] = []
        if stream:
            sql += " AND stream = ?"
            params.append(stream)
        if since:
            ts = since.isoformat() if hasattr(since, "isoformat") else str(since)
            sql += " AND recorded_at >= ?"
            params.append(ts)
        sql += " ORDER BY recorded_at ASC"
        return self.query(sql, tuple(params))

    def get_stream_equity(self, source: str) -> float:
        """Get the most recent equity value for a given stream/source."""
        row = self.execute(
            "SELECT equity FROM equity_snapshots WHERE stream = ? ORDER BY recorded_at DESC LIMIT 1",
            (source,),
        ).fetchone()
        return row["equity"] if row else 0.0

    # ── Runs ────────────────────────────────────────────────

    def insert_run(self, run) -> str:
        data = run.to_db_dict()
        self.insert("runs", data)
        self.commit()
        return data["id"]

    def update_run(self, run_id: str, **kwargs):
        for k, v in kwargs.items():
            if isinstance(v, (dict, list)):
                kwargs[k] = json.dumps(v)
            elif isinstance(v, bool):
                kwargs[k] = int(v)
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        self.execute(f"UPDATE runs SET {sets} WHERE id = ?", (*kwargs.values(), run_id))
        self.commit()

    def get_runs(self, limit: int = 24) -> list[dict]:
        rows = self.query("SELECT * FROM runs ORDER BY started_at DESC LIMIT ?", (limit,))
        for r in rows:
            for key in ("stages_run", "signals_generated", "trades_opened"):
                if isinstance(r.get(key), str):
                    try:
                        r[key] = json.loads(r[key])
                    except (json.JSONDecodeError, TypeError):
                        pass
        return rows

    # ── Config overrides ────────────────────────────────────

    def set_config_override(self, key: str, value: Any):
        self.execute(
            """INSERT INTO config_overrides (key, value, updated_at)
               VALUES (?, ?, CURRENT_TIMESTAMP)
               ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP""",
            (key, json.dumps(value)),
        )
        self.commit()

    def get_config_overrides(self) -> dict:
        rows = self.execute("SELECT key, value FROM config_overrides").fetchall()
        result = {}
        for r in rows:
            try:
                result[r["key"]] = json.loads(r["value"])
            except (json.JSONDecodeError, TypeError):
                result[r["key"]] = r["value"]
        return result

    def delete_config_override(self, key: str):
        self.execute("DELETE FROM config_overrides WHERE key = ?", (key,))
        self.commit()

    # ── Trade events ────────────────────────────────────────

    def insert_trade_event(self, trade_id: str, event_type: str, data: dict | None = None) -> int:
        data_json = json.dumps(data) if data else None
        cur = self.execute(
            "INSERT INTO trade_events (trade_id, event_type, data) VALUES (?, ?, ?)",
            (trade_id, event_type, data_json),
        )
        self.commit()
        return cur.lastrowid

    def get_trade_events(self, trade_id: str) -> list[dict]:
        rows = self.execute(
            "SELECT * FROM trade_events WHERE trade_id = ? ORDER BY created_at ASC",
            (trade_id,),
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            if isinstance(d.get("data"), str):
                try:
                    d["data"] = json.loads(d["data"])
                except (json.JSONDecodeError, TypeError):
                    pass
            result.append(d)
        return result

    # ── Hybrid configs (legacy tables) ───────────────────

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
            d = dict(r)
            for key in ("modules", "instruments"):
                if isinstance(d.get(key), str):
                    try:
                        d[key] = json.loads(d[key])
                    except (json.JSONDecodeError, TypeError):
                        pass
            result.append(d)
        return result

    def get_all_hybrids(self) -> list[dict]:
        rows = self.execute(
            "SELECT * FROM hybrid_configs ORDER BY created_at DESC"
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            for key in ("modules", "instruments"):
                if isinstance(d.get(key), str):
                    try:
                        d[key] = json.loads(d[key])
                    except (json.JSONDecodeError, TypeError):
                        pass
            result.append(d)
        return result

    def delete_hybrid_config(self, config_id: int):
        self.execute("DELETE FROM hybrid_configs WHERE id = ?", (config_id,))
        self.commit()

    # ── Run logs (legacy table) ────────────────────────

    def insert_run_log(self, **kwargs) -> int:
        _JSON_KEYS = ("config_snapshot", "streams_run", "signals_generated",
                      "trades_opened", "trades_closed", "trades_carried", "rejected_signals")
        for key in _JSON_KEYS:
            if key in kwargs and isinstance(kwargs[key], (list, dict)):
                kwargs[key] = json.dumps(kwargs[key])
        cols = ", ".join(kwargs.keys())
        placeholders = ", ".join(["?"] * len(kwargs))
        cur = self.execute(
            f"INSERT INTO run_logs ({cols}) VALUES ({placeholders})",
            tuple(kwargs.values()),
        )
        self.commit()
        return cur.lastrowid

    def update_run_log(self, run_id: str, **kwargs):
        _JSON_KEYS = ("config_snapshot", "streams_run", "signals_generated",
                      "trades_opened", "trades_closed", "trades_carried", "rejected_signals")
        for key in _JSON_KEYS:
            if key in kwargs and isinstance(kwargs[key], (list, dict)):
                kwargs[key] = json.dumps(kwargs[key])
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        self.execute(
            f"UPDATE run_logs SET {sets} WHERE run_id = ?",
            (*kwargs.values(), run_id),
        )
        self.commit()

    def get_run_logs(self, limit: int = 24) -> list[dict]:
        rows = self.execute(
            "SELECT * FROM run_logs ORDER BY started_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            for key in ("config_snapshot", "streams_run", "signals_generated",
                        "trades_opened", "trades_closed", "trades_carried", "rejected_signals"):
                if isinstance(d.get(key), str):
                    try:
                        d[key] = json.loads(d[key])
                    except (json.JSONDecodeError, TypeError):
                        pass
            result.append(d)
        return result

    # ── Candles ─────────────────────────────────────────

    def insert_candles(self, instrument: str, df) -> int:
        """Bulk insert candles from a pandas DataFrame. Uses INSERT OR IGNORE
        so re-runs with overlapping timestamps are safe. Returns rows inserted."""
        rows_before = self.execute(
            "SELECT COUNT(*) as cnt FROM candles WHERE instrument = ?", (instrument,)
        ).fetchone()["cnt"]
        now = datetime.now(timezone.utc).isoformat()
        for ts, row in df.iterrows():
            self.execute(
                """INSERT OR IGNORE INTO candles
                   (instrument, timestamp, open, high, low, close, volume, fetched_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    instrument,
                    ts.isoformat() if hasattr(ts, "isoformat") else str(ts),
                    float(row["Open"]),
                    float(row["High"]),
                    float(row["Low"]),
                    float(row["Close"]),
                    int(row.get("Volume", 0)),
                    now,
                ),
            )
        self.commit()
        rows_after = self.execute(
            "SELECT COUNT(*) as cnt FROM candles WHERE instrument = ?", (instrument,)
        ).fetchone()["cnt"]
        return rows_after - rows_before

    def insert_price_snapshot(self, instrument: str, bid: float, ask: float,
                              mid: float, daily_change_pct: float | None = None) -> int:
        """Insert a current price snapshot. Returns the row id."""
        cur = self.execute(
            """INSERT INTO price_snapshots (instrument, bid, ask, mid, daily_change_pct)
               VALUES (?, ?, ?, ?, ?)""",
            (instrument, bid, ask, mid, daily_change_pct),
        )
        self.commit()
        return cur.lastrowid

    def get_candles(self, instrument: str, limit: int = 200) -> list[dict]:
        """Get the most recent candles for an instrument, ordered oldest-first."""
        return self.query(
            """SELECT * FROM candles WHERE instrument = ?
               ORDER BY timestamp DESC LIMIT ?""",
            (instrument, limit),
        )[::-1]  # reverse so oldest is first

    def get_latest_price(self, instrument: str) -> dict | None:
        """Get the most recent price snapshot for an instrument."""
        row = self.execute(
            "SELECT * FROM price_snapshots WHERE instrument = ? ORDER BY fetched_at DESC LIMIT 1",
            (instrument,),
        ).fetchone()
        return dict(row) if row else None

    # ── Helpers ─────────────────────────────────────────────

    def get_daily_pnl(self, source: str | None = None) -> float:
        if source:
            row = self.execute(
                "SELECT COALESCE(SUM(pnl), 0) as total FROM trades WHERE closed_at >= date('now') AND source = ?",
                (source,),
            ).fetchone()
        else:
            row = self.execute(
                "SELECT COALESCE(SUM(pnl), 0) as total FROM trades WHERE closed_at >= date('now')",
            ).fetchone()
        return row["total"] if row else 0.0

    def table_counts(self) -> dict[str, int]:
        """Return row counts for all tables. Useful for verification."""
        tables = self.query(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        counts = {}
        for t in tables:
            name = t["name"]
            row = self.execute(f"SELECT COUNT(*) as cnt FROM [{name}]").fetchone()
            counts[name] = row["cnt"] if row else 0
        return counts
