"""Performance metric computation for reviews."""

from __future__ import annotations

import statistics
from datetime import datetime, timedelta, timezone


def compute_stream_metrics(db, stream_id: str, since: datetime) -> dict:
    """Compute comprehensive metrics for a stream over a period."""
    trades = db.get_trades(stream_id, limit=10000, since=since)
    signals = db.get_signals(stream_id, limit=10000, since=since)
    equity_history = db.get_equity_history(stream_id, since=since)

    closed = [t for t in trades if t.get("pnl") is not None]
    open_trades = [t for t in trades if t["status"] == "open"]

    total_pnl = sum(t["pnl"] for t in closed)
    wins = [t for t in closed if t["pnl"] > 0]
    losses = [t for t in closed if t["pnl"] < 0]

    win_rate = len(wins) / len(closed) if closed else 0
    avg_win = statistics.mean([t["pnl"] for t in wins]) if wins else 0
    avg_loss = statistics.mean([t["pnl"] for t in losses]) if losses else 0
    profit_factor = abs(sum(t["pnl"] for t in wins) / sum(t["pnl"] for t in losses)) if losses else 0

    # Sharpe from equity
    if len(equity_history) >= 2:
        equities = [h["equity"] for h in equity_history]
        returns = [(equities[i] / equities[i - 1]) - 1 for i in range(1, len(equities))]
        sharpe = (statistics.mean(returns) / (statistics.stdev(returns) if len(returns) > 1 else 1e-10)) * (252 ** 0.5)
    else:
        sharpe = 0.0

    # Max drawdown
    max_dd = 0.0
    if equity_history:
        peak = equity_history[0]["equity"]
        for h in equity_history:
            if h["equity"] > peak:
                peak = h["equity"]
            dd = (h["equity"] - peak) / peak if peak > 0 else 0
            max_dd = min(max_dd, dd)

    # Best/worst trades
    best_trade = max(closed, key=lambda t: t["pnl"]) if closed else None
    worst_trade = min(closed, key=lambda t: t["pnl"]) if closed else None

    return {
        "stream_id": stream_id,
        "total_pnl": round(total_pnl, 2),
        "trade_count": len(trades),
        "closed_count": len(closed),
        "open_count": len(open_trades),
        "win_rate": round(win_rate, 3),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "profit_factor": round(profit_factor, 2),
        "sharpe_ratio": round(sharpe, 2),
        "max_drawdown": round(max_dd, 4),
        "signal_count": len(signals),
        "best_trade": _trade_summary(best_trade),
        "worst_trade": _trade_summary(worst_trade),
    }


def compute_instrument_metrics(db, since: datetime) -> list[dict]:
    """P&L per instrument across all streams."""
    trades = db.get_trades(limit=10000, since=since)
    instruments: dict[str, dict] = {}

    for t in trades:
        inst = t["instrument"]
        if inst not in instruments:
            instruments[inst] = {"total_pnl": 0, "count": 0, "wins": 0}
        instruments[inst]["count"] += 1
        if t.get("pnl") is not None:
            instruments[inst]["total_pnl"] += t["pnl"]
            if t["pnl"] > 0:
                instruments[inst]["wins"] += 1

    return [
        {
            "instrument": inst,
            "total_pnl": round(data["total_pnl"], 2),
            "trade_count": data["count"],
            "win_rate": round(data["wins"] / data["count"], 3) if data["count"] > 0 else 0,
        }
        for inst, data in sorted(instruments.items(), key=lambda x: x[1]["total_pnl"], reverse=True)
    ]


def compute_strategy_metrics(db, since: datetime) -> list[dict]:
    """Per-strategy metrics within the strategy stream."""
    strategies = ["momentum", "carry", "breakout", "mean_reversion", "volatility_breakout"]
    results = []

    for name in strategies:
        rows = db.execute(
            "SELECT * FROM signals WHERE stream = 'strategy' AND source = ? AND created_at >= ?",
            (name, since.isoformat()),
        ).fetchall()
        signals = [dict(r) for r in rows]

        traded = [s for s in signals if s.get("was_traded")]
        trade_ids = [s["trade_id"] for s in traded if s.get("trade_id")]

        pnl = 0
        wins = 0
        total = 0
        for tid in trade_ids:
            t = db.execute("SELECT * FROM trades WHERE id = ?", (tid,)).fetchone()
            if t:
                t = dict(t)
                if t.get("pnl") is not None:
                    pnl += t["pnl"]
                    total += 1
                    if t["pnl"] > 0:
                        wins += 1

        results.append({
            "name": name,
            "signal_count": len(signals),
            "trade_count": len(trade_ids),
            "total_pnl": round(pnl, 2),
            "win_rate": round(wins / total, 3) if total > 0 else 0,
        })

    return results


def _trade_summary(trade: dict | None) -> dict | None:
    if not trade:
        return None
    return {
        "instrument": trade["instrument"],
        "direction": trade["direction"],
        "pnl": trade.get("pnl"),
        "pnl_pips": trade.get("pnl_pips"),
        "opened_at": trade.get("opened_at"),
        "closed_at": trade.get("closed_at"),
    }
