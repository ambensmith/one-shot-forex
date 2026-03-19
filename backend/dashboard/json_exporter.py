"""Export SQLite data to static JSON files for the frontend dashboard."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

logger = logging.getLogger("forex_sentinel.dashboard")

OUTPUT_DIR = Path("frontend/public/data")


def export_all(db_path: str = "data/sentinel.db"):
    """Export all dashboard JSON files."""
    from backend.core.database import Database
    from backend.core.config import load_config

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    db = Database(db_path)
    config = load_config(db=db)

    export_dashboard_summary(db, config)
    export_trades(db)
    export_equity(db)
    export_signals(db)
    export_models(db, config)
    export_review(db, config)
    export_hybrids(db)
    export_config(config)
    export_run_reviews(db)

    db.close()
    logger.info(f"Dashboard JSON exported to {OUTPUT_DIR}")


def export_dashboard_summary(db, config):
    """Export main dashboard summary."""
    streams_data = []
    streams_cfg = config.get("streams", {})

    for stream_id, stream_name, cfg_key in [
        ("news", "News Stream", "news_stream"),
        ("strategy", "Strategy Stream", "strategy_stream"),
    ]:
        stream_cfg = streams_cfg.get(cfg_key, {})
        trades = db.get_trades(stream_id, limit=1000)
        # Exclude phantom/failed trades from all metrics
        real_trades = [t for t in trades if t.get("status") != "failed"]
        open_trades = db.get_open_trades(stream_id)
        equity = db.get_stream_equity(stream_id)
        capital_allocation = stream_cfg.get("capital_allocation", 100)

        closed = [t for t in real_trades if t.get("pnl") is not None]
        total_pnl = sum(t["pnl"] for t in closed)
        wins = sum(1 for t in closed if t["pnl"] > 0)
        win_rate = wins / len(closed) if closed else 0

        # Daily P&L — trades closed today
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        daily_pnl = sum(
            t["pnl"] for t in closed
            if t.get("closed_at", "").startswith(today_str)
        )

        # Signal count
        signals = db.get_signals(stream=stream_id, limit=10000)
        signal_count = len(signals)

        # Compute Sharpe from equity history
        eq_history = db.get_equity_history(stream_id)
        sharpe = _compute_sharpe(eq_history)

        # Max drawdown
        max_dd = _compute_max_drawdown(eq_history)

        streams_data.append({
            "id": stream_id,
            "name": stream_name,
            "equity": equity,
            "capital_allocation": capital_allocation,
            "total_pnl": round(total_pnl, 2),
            "daily_pnl": round(daily_pnl, 2),
            "trade_count": len(real_trades),
            "signal_count": signal_count,
            "open_positions": len(open_trades),
            "win_rate": round(win_rate, 3),
            "sharpe_ratio": round(sharpe, 2),
            "max_drawdown": round(max_dd, 4),
        })

    # Add hybrid streams
    for hybrid in db.get_active_hybrids():
        hid = f"hybrid:{hybrid['name']}"
        trades = db.get_trades(hid, limit=1000)
        real_trades = [t for t in trades if t.get("status") != "failed"]
        open_trades = db.get_open_trades(hid)
        equity = db.get_stream_equity(hid)
        capital_allocation = hybrid.get("capital_allocation", 100)
        closed = [t for t in real_trades if t.get("pnl") is not None]
        total_pnl = sum(t["pnl"] for t in closed)
        wins = sum(1 for t in closed if t["pnl"] > 0)

        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        daily_pnl = sum(
            t["pnl"] for t in closed
            if t.get("closed_at", "").startswith(today_str)
        )

        signals = db.get_signals(stream=hid, limit=10000)

        streams_data.append({
            "id": hid,
            "name": hybrid["name"],
            "equity": equity,
            "capital_allocation": capital_allocation,
            "total_pnl": round(total_pnl, 2),
            "daily_pnl": round(daily_pnl, 2),
            "trade_count": len(real_trades),
            "signal_count": len(signals),
            "open_positions": len(open_trades),
            "win_rate": round(wins / len(closed), 3) if closed else 0,
            "sharpe_ratio": 0,
            "max_drawdown": 0,
        })

    # Strategy breakdown
    strategy_breakdown = _get_strategy_breakdown(db)

    # Instrument breakdown
    instrument_breakdown = _get_instrument_breakdown(db)

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "streams": streams_data,
        "strategy_breakdown": strategy_breakdown,
        "instrument_breakdown": instrument_breakdown,
    }

    _write_json("dashboard.json", summary)


def export_trades(db):
    """Export recent trades."""
    trades = db.get_trades(limit=200)
    trade_list = []
    for t in trades:
        trade_list.append({
            "id": t["id"],
            "stream": t["stream"],
            "instrument": t["instrument"],
            "direction": t["direction"],
            "entry_price": t["entry_price"],
            "exit_price": t.get("exit_price"),
            "stop_loss": t["stop_loss"],
            "take_profit": t["take_profit"],
            "position_size": t["position_size"],
            "pnl": t.get("pnl"),
            "pnl_pips": t.get("pnl_pips"),
            "status": t["status"],
            "opened_at": t.get("opened_at"),
            "closed_at": t.get("closed_at"),
        })

    _write_json("trades.json", {"trades": trade_list})


def export_equity(db):
    """Export equity curves for all streams."""
    curves = {}
    for stream_id in ["news", "strategy"]:
        history = db.get_equity_history(stream_id)
        curves[stream_id] = [
            {"time": h["recorded_at"], "equity": h["equity"], "positions": h["open_positions"]}
            for h in history
        ]

    for hybrid in db.get_active_hybrids():
        hid = f"hybrid:{hybrid['name']}"
        history = db.get_equity_history(hid)
        curves[hid] = [
            {"time": h["recorded_at"], "equity": h["equity"], "positions": h["open_positions"]}
            for h in history
        ]

    _write_json("equity.json", {"curves": curves})


def export_signals(db):
    """Export recent signals."""
    signals = db.get_signals(limit=200)
    signal_list = []
    for s in signals:
        metadata = s.get("metadata")
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except (json.JSONDecodeError, TypeError):
                pass

        signal_list.append({
            "id": s["id"],
            "stream": s["stream"],
            "source": s["source"],
            "instrument": s["instrument"],
            "direction": s["direction"],
            "confidence": s["confidence"],
            "reasoning": s.get("reasoning"),
            "was_traded": bool(s.get("was_traded")),
            "rejection_reason": s.get("rejection_reason"),
            "is_comparison": bool(s.get("is_comparison")),
            "metadata": metadata,
            "created_at": s.get("created_at"),
        })

    _write_json("signals.json", {"signals": signal_list})


def export_models(db, config):
    """Export model comparison data."""
    from backend.signals.model_registry import get_all_models

    models = get_all_models()
    model_data = []

    for model_key, info in models.items():
        # Get signals from this model
        signals = db.execute(
            "SELECT * FROM signals WHERE source = ? ORDER BY created_at DESC LIMIT 100",
            (model_key,),
        ).fetchall()

        total = len(signals)
        if total == 0:
            model_data.append({
                "key": model_key,
                "provider": info["provider"],
                "model": info["model"],
                "cost": info["cost_per_1m_tokens"],
                "rate_limit": info["rate_limit"],
                "notes": info["notes"],
                "signal_count": 0,
            })
            continue

        directions = {"long": 0, "short": 0, "neutral": 0}
        for s in signals:
            d = dict(s)
            directions[d.get("direction", "neutral")] = directions.get(d.get("direction", "neutral"), 0) + 1

        model_data.append({
            "key": model_key,
            "provider": info["provider"],
            "model": info["model"],
            "cost": info["cost_per_1m_tokens"],
            "rate_limit": info["rate_limit"],
            "notes": info["notes"],
            "signal_count": total,
            "direction_breakdown": directions,
        })

    _write_json("models.json", {"models": model_data})


def export_review(db, config):
    """Export latest review data as JSON for the frontend."""
    from datetime import timedelta
    from pathlib import Path as P

    review_data = {"has_review": False}

    # Try to read latest REVIEW.md
    latest_dir = P(config.get("reviews", {}).get("output_dir", "reviews")) / "latest"
    if latest_dir.exists():
        review_md = latest_dir / "REVIEW.md"
        if review_md.exists():
            review_data["has_review"] = True
            review_data["review_md"] = review_md.read_text()

        # Read SYSTEM_CONTEXT.md
        ctx_path = P(config.get("reviews", {}).get("output_dir", "reviews")) / "SYSTEM_CONTEXT.md"
        if ctx_path.exists():
            review_data["system_context"] = ctx_path.read_text()

        # Read CSVs as strings
        for csv_name in ["trades.csv", "signals.csv", "equity_curves.csv", "open_positions.csv"]:
            csv_path = latest_dir / csv_name
            if csv_path.exists():
                review_data[csv_name.replace(".csv", "_csv")] = csv_path.read_text()

    _write_json("review.json", review_data)


def export_hybrids(db):
    """Export hybrid configs for the frontend."""
    hybrids = db.get_all_hybrids()
    _write_json("hybrids.json", {"hybrids": hybrids})


def export_config(config: dict):
    """Export effective config as JSON for the frontend Settings page."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    # Strip sensitive fields
    safe_config = {k: v for k, v in config.items() if k not in ("execution",)}
    _write_json("config.json", {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "config": safe_config,
    })


def export_run_reviews(db):
    """Export recent run logs for the frontend Run History page."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    run_logs = db.get_run_logs(limit=48)
    _write_json("run_reviews.json", {"runs": run_logs})


def _get_strategy_breakdown(db) -> list[dict]:
    """Get per-strategy performance metrics."""
    strategies = ["momentum", "carry", "breakout", "mean_reversion", "volatility_breakout"]
    breakdown = []

    for strat_name in strategies:
        signals = db.execute(
            "SELECT * FROM signals WHERE stream = 'strategy' AND source = ?",
            (strat_name,),
        ).fetchall()

        traded_signal_ids = [dict(s)["trade_id"] for s in signals if dict(s).get("was_traded")]
        trades = []
        for tid in traded_signal_ids:
            if tid:
                t = db.execute("SELECT * FROM trades WHERE id = ?", (tid,)).fetchone()
                if t:
                    trades.append(dict(t))

        closed = [t for t in trades if t.get("pnl") is not None]
        total_pnl = sum(t["pnl"] for t in closed)
        wins = sum(1 for t in closed if t["pnl"] > 0)

        breakdown.append({
            "name": strat_name,
            "signal_count": len(signals),
            "trade_count": len(trades),
            "total_pnl": round(total_pnl, 2),
            "win_rate": round(wins / len(closed), 3) if closed else 0,
        })

    return breakdown


def _get_instrument_breakdown(db) -> list[dict]:
    """Get per-instrument P&L across all streams."""
    rows = db.execute(
        """SELECT instrument, COUNT(*) as count, COALESCE(SUM(pnl), 0) as total_pnl
           FROM trades GROUP BY instrument ORDER BY total_pnl DESC"""
    ).fetchall()

    return [{"instrument": dict(r)["instrument"], "count": dict(r)["count"],
             "total_pnl": round(dict(r)["total_pnl"], 2)} for r in rows]


def _compute_sharpe(equity_history: list[dict]) -> float:
    """Compute annualized Sharpe ratio from equity snapshots."""
    if len(equity_history) < 2:
        return 0.0
    equities = [h["equity"] for h in equity_history]
    returns = [(equities[i] / equities[i - 1]) - 1 for i in range(1, len(equities))]
    if not returns:
        return 0.0
    import statistics
    mean_r = statistics.mean(returns)
    std_r = statistics.stdev(returns) if len(returns) > 1 else 1e-10
    if std_r == 0:
        return 0.0
    return (mean_r / std_r) * (252 ** 0.5)


def _compute_max_drawdown(equity_history: list[dict]) -> float:
    """Compute maximum drawdown from equity snapshots."""
    if len(equity_history) < 2:
        return 0.0
    peak = 0
    max_dd = 0
    for h in equity_history:
        eq = h["equity"]
        if eq > peak:
            peak = eq
        if peak > 0:
            dd = (eq - peak) / peak
            if dd < max_dd:
                max_dd = dd
    return max_dd


def _write_json(filename: str, data: dict):
    path = OUTPUT_DIR / filename
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)
    logger.debug(f"Wrote {path}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    export_all()
