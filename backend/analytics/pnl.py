"""Unified PnL aggregation — the one module that queries ``trades`` for totals.

All dashboards, APIs, exports, and reviews call into this module so every
number on the product agrees with every other number. The canonical PnL value
is ``trades.pnl`` (EUR, set at close time by ``Executor.calc_pnl``).

A ``stream`` filter is the high-level identifier used in configs and URLs
("news", "strategy", "hybrid:<name>"). Trade rows store a finer-grained
``source`` — e.g. ``llm``, ``strategy:momentum``, ``hybrid:alpha``. This module
resolves the stream → source mapping in one place so callers never need to
know the convention.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any


STRATEGY_NAMES: tuple[str, ...] = (
    "momentum",
    "carry",
    "breakout",
    "mean_reversion",
    "volatility_breakout",
)


@dataclass(frozen=True)
class PnLAggregate:
    total_pnl: float
    trade_count: int
    wins: int
    losses: int
    win_rate: float

    def as_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["total_pnl"] = round(d["total_pnl"], 2)
        d["win_rate"] = round(d["win_rate"], 3)
        return d


def _stream_source_clause(stream: str | None) -> tuple[str, list[Any]]:
    """Map a stream id to a SQL predicate on ``trades.source``.

    Returns ("", []) when ``stream`` is None (no filter).
    """
    if not stream:
        return "", []
    if stream == "news":
        return " AND (source = 'news' OR source = 'llm')", []
    if stream == "strategy":
        return " AND source LIKE 'strategy%'", []
    # hybrid:<name> or any explicit source literal
    return " AND source = ?", [stream]


def _build_where(
    *,
    stream: str | None,
    instrument: str | None,
    source: str | None,
    source_prefix: str | None,
    since: str | datetime | None,
    until: str | datetime | None,
) -> tuple[str, list[Any]]:
    sql = " WHERE status LIKE 'closed%' AND pnl IS NOT NULL"
    params: list[Any] = []

    stream_sql, stream_params = _stream_source_clause(stream)
    sql += stream_sql
    params.extend(stream_params)

    if instrument:
        sql += " AND instrument = ?"
        params.append(instrument)
    if source:
        sql += " AND source = ?"
        params.append(source)
    if source_prefix:
        sql += " AND source LIKE ?"
        params.append(source_prefix + "%")
    if since is not None:
        ts = since.isoformat() if hasattr(since, "isoformat") else str(since)
        sql += " AND closed_at >= ?"
        params.append(ts)
    if until is not None:
        ts = until.isoformat() if hasattr(until, "isoformat") else str(until)
        sql += " AND closed_at < ?"
        params.append(ts)
    return sql, params


def aggregate_pnl(
    db,
    *,
    stream: str | None = None,
    instrument: str | None = None,
    source: str | None = None,
    source_prefix: str | None = None,
    since: str | datetime | None = None,
    until: str | datetime | None = None,
) -> PnLAggregate:
    """Single-query aggregate over closed trades.

    ``stream`` is the high-level id (news / strategy / hybrid:X). ``source`` and
    ``source_prefix`` let callers target more specific values on trades.source,
    such as ``strategy:momentum`` or ``strategy:``.
    """
    where, params = _build_where(
        stream=stream, instrument=instrument,
        source=source, source_prefix=source_prefix,
        since=since, until=until,
    )
    sql = (
        "SELECT COALESCE(SUM(pnl), 0) AS total_pnl, "
        "COUNT(*) AS trade_count, "
        "SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) AS wins, "
        "SUM(CASE WHEN pnl <= 0 THEN 1 ELSE 0 END) AS losses "
        "FROM trades" + where
    )
    row = db.execute(sql, tuple(params)).fetchone()
    if not row:
        return PnLAggregate(0.0, 0, 0, 0, 0.0)
    total = float(row["total_pnl"] or 0.0)
    count = int(row["trade_count"] or 0)
    wins = int(row["wins"] or 0)
    losses = int(row["losses"] or 0)
    win_rate = (wins / count) if count else 0.0
    return PnLAggregate(total, count, wins, losses, win_rate)


def list_closed_trades(
    db,
    *,
    stream: str | None = None,
    instrument: str | None = None,
    source: str | None = None,
    source_prefix: str | None = None,
    since: str | datetime | None = None,
    until: str | datetime | None = None,
) -> list[dict]:
    """Return the raw closed-trade rows that aggregate_pnl sums over.

    Useful for callers that need per-trade detail (best/worst, avg win/loss)
    while still reusing the unified filter semantics — especially the
    stream → source mapping.
    """
    where, params = _build_where(
        stream=stream, instrument=instrument,
        source=source, source_prefix=source_prefix,
        since=since, until=until,
    )
    sql = "SELECT * FROM trades" + where + " ORDER BY closed_at ASC"
    rows = db.execute(sql, tuple(params)).fetchall()
    return [dict(r) for r in rows]


def equity_curve(
    db,
    *,
    stream: str | None = None,
    starting_capital: float = 100.0,
) -> list[dict]:
    """Step-function equity curve derived from closed trades.

    Every point is bound to an immutable trade-close event, so the curve cannot
    drift from the trade ledger. The first point is a synthetic anchor one
    second before the first close so the chart opens flat at the capital line.
    """
    where, params = _build_where(
        stream=stream, instrument=None,
        source=None, source_prefix=None, since=None, until=None,
    )
    sql = "SELECT id, closed_at, pnl FROM trades" + where + " ORDER BY closed_at ASC"
    rows = db.execute(sql, tuple(params)).fetchall()

    if not rows:
        return []

    out: list[dict] = []
    running = float(starting_capital)
    first_close = rows[0]["closed_at"]
    out.append({
        "timestamp": _anchor_timestamp(first_close),
        "equity": round(running, 2),
        "trade_id": None,
        "delta_pnl": 0.0,
    })
    for r in rows:
        delta = float(r["pnl"] or 0.0)
        running += delta
        out.append({
            "timestamp": str(r["closed_at"]),
            "equity": round(running, 2),
            "trade_id": r["id"],
            "delta_pnl": round(delta, 2),
        })
    return out


def _anchor_timestamp(closed_at: Any) -> str:
    """Produce a synthetic anchor one second before the first close."""
    s = str(closed_at)
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        anchor = dt.fromtimestamp(dt.timestamp() - 1, tz=dt.tzinfo)
        return anchor.isoformat()
    except (ValueError, TypeError):
        return s


def per_instrument_breakdown(db, *, stream: str | None = None) -> list[dict]:
    """One row per instrument with closed-trade PnL and trade count.

    Sorted descending by total_pnl so the biggest movers surface first.
    """
    where, params = _build_where(
        stream=stream, instrument=None, source=None, source_prefix=None,
        since=None, until=None,
    )
    sql = (
        "SELECT instrument, COUNT(*) AS trade_count, "
        "COALESCE(SUM(pnl), 0) AS total_pnl, "
        "SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) AS wins "
        "FROM trades" + where + " GROUP BY instrument ORDER BY total_pnl DESC"
    )
    rows = db.execute(sql, tuple(params)).fetchall()
    out: list[dict] = []
    for r in rows:
        count = int(r["trade_count"] or 0)
        wins = int(r["wins"] or 0)
        out.append({
            "instrument": r["instrument"],
            "trade_count": count,
            "total_pnl": round(float(r["total_pnl"] or 0.0), 2),
            "win_rate": round(wins / count, 3) if count else 0.0,
        })
    return out


def per_strategy_breakdown(db) -> list[dict]:
    """One row per strategy, computed from trades whose signal source
    matches ``strategy:<name>`` (trades store the same prefix on close).
    """
    out: list[dict] = []
    for name in STRATEGY_NAMES:
        source = f"strategy:{name}"
        agg = aggregate_pnl(db, source=source)
        signal_count_row = db.execute(
            "SELECT COUNT(*) AS c FROM signals WHERE source = ?",
            (source,),
        ).fetchone()
        signal_count = int(signal_count_row["c"] or 0) if signal_count_row else 0
        out.append({
            "name": name,
            "signal_count": signal_count,
            "trade_count": agg.trade_count,
            "total_pnl": round(agg.total_pnl, 2),
            "win_rate": round(agg.win_rate, 3),
        })
    return out


def per_stream_breakdown(db, config: dict) -> list[dict]:
    """One row per configured stream (news, strategy, active hybrids).

    Capital allocation is pulled from config so the returned equity value
    matches what the dashboard and equity curve anchor to.
    """
    streams_cfg = (config or {}).get("streams", {})
    out: list[dict] = []
    for stream_id, cfg_key in (("news", "news_stream"), ("strategy", "strategy_stream")):
        capital = float(streams_cfg.get(cfg_key, {}).get("capital_allocation", 100) or 100)
        agg = aggregate_pnl(db, stream=stream_id)
        out.append({
            "stream": stream_id,
            "capital": capital,
            "equity": round(capital + agg.total_pnl, 2),
            **agg.as_dict(),
        })
    # Hybrids — read active hybrid configs from the DB
    try:
        hybrids = db.get_active_hybrids()
    except Exception:
        hybrids = []
    for h in hybrids or []:
        stream_id = f"hybrid:{h.get('name')}"
        capital = float(h.get("capital_allocation", 100) or 100)
        agg = aggregate_pnl(db, stream=stream_id)
        out.append({
            "stream": stream_id,
            "capital": capital,
            "equity": round(capital + agg.total_pnl, 2),
            **agg.as_dict(),
        })
    return out


def stream_capital(config: dict, stream: str | None) -> float:
    """Resolve a stream's capital allocation from config. Defaults to 100 EUR.

    Used by ``equity_curve`` callers that want the chart to start at the
    configured capital rather than the default.
    """
    if not stream:
        return 100.0
    streams_cfg = (config or {}).get("streams", {})
    if stream == "news":
        return float(streams_cfg.get("news_stream", {}).get("capital_allocation", 100) or 100)
    if stream == "strategy":
        return float(streams_cfg.get("strategy_stream", {}).get("capital_allocation", 100) or 100)
    if stream.startswith("hybrid:"):
        return float(
            streams_cfg.get("hybrid_defaults", {}).get("capital_allocation", 100) or 100
        )
    return 100.0
