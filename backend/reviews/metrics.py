"""Performance metric computation for reviews."""

from __future__ import annotations

import statistics
from datetime import datetime, timedelta, timezone


def compute_stream_metrics(db, stream_id: str, since: datetime) -> dict:
    """Compute comprehensive metrics for a stream over a period."""
    from backend.analytics import pnl as _pnl

    signals = db.get_signals(stream_id, limit=10000, since=since)
    equity_history = db.get_equity_history(stream_id, since=since)
    open_trades = db.get_open_trades(stream_id)

    closed = _pnl.list_closed_trades(db, stream=stream_id, since=since)
    agg = _pnl.aggregate_pnl(db, stream=stream_id, since=since)

    total_pnl = agg.total_pnl
    wins = [t for t in closed if t["pnl"] > 0]
    losses = [t for t in closed if t["pnl"] < 0]

    win_rate = agg.win_rate
    avg_win = statistics.mean([t["pnl"] for t in wins]) if wins else 0
    avg_loss = statistics.mean([t["pnl"] for t in losses]) if losses else 0
    profit_factor = abs(sum(t["pnl"] for t in wins) / sum(t["pnl"] for t in losses)) if losses else 0

    # Sharpe from equity
    if len(equity_history) >= 2:
        equities = [h["equity"] for h in equity_history]
        returns = [(equities[i] / equities[i - 1]) - 1 for i in range(1, len(equities))]
        std_r = statistics.stdev(returns) if len(returns) > 1 else 1e-10
        if std_r == 0:
            sharpe = 0.0
        else:
            sharpe = (statistics.mean(returns) / std_r) * (252 ** 0.5)
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
        "trade_count": len(closed) + len(open_trades),
        "closed_count": agg.trade_count,
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
    """Per-instrument P&L across all streams (over a period)."""
    from backend.analytics import pnl as _pnl

    closed = _pnl.list_closed_trades(db, since=since)
    instruments: dict[str, dict] = {}
    for t in closed:
        inst = t["instrument"]
        bucket = instruments.setdefault(inst, {"total_pnl": 0.0, "count": 0, "wins": 0})
        bucket["count"] += 1
        bucket["total_pnl"] += t["pnl"]
        if t["pnl"] > 0:
            bucket["wins"] += 1

    return [
        {
            "instrument": inst,
            "total_pnl": round(d["total_pnl"], 2),
            "trade_count": d["count"],
            "win_rate": round(d["wins"] / d["count"], 3) if d["count"] else 0,
        }
        for inst, d in sorted(instruments.items(), key=lambda x: x[1]["total_pnl"], reverse=True)
    ]


def compute_strategy_metrics(db, since: datetime) -> list[dict]:
    """Per-strategy metrics within the strategy stream (over a period)."""
    from backend.analytics import pnl as _pnl

    results: list[dict] = []
    for name in _pnl.STRATEGY_NAMES:
        source = f"strategy:{name}"
        agg = _pnl.aggregate_pnl(db, source=source, since=since)
        signal_rows = db.execute(
            "SELECT COUNT(*) AS c FROM signals WHERE source = ? AND created_at >= ?",
            (source, since.isoformat()),
        ).fetchone()
        signal_count = int(signal_rows["c"] or 0) if signal_rows else 0
        results.append({
            "name": name,
            "signal_count": signal_count,
            "trade_count": agg.trade_count,
            "total_pnl": round(agg.total_pnl, 2),
            "win_rate": round(agg.win_rate, 3),
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
        "entry_price": trade.get("entry_price"),
        "exit_price": trade.get("exit_price"),
        "stop_loss": trade.get("stop_loss"),
        "take_profit": trade.get("take_profit"),
        "position_size": trade.get("position_size"),
        "signal_ids": trade.get("signal_ids"),
        "opened_at": trade.get("opened_at"),
        "closed_at": trade.get("closed_at"),
    }
