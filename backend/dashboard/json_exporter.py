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
    export_bias(db)
    export_llm_activity(db)
    export_strategies_detail(db)
    export_prompts(db)

    db.close()
    logger.info(f"Dashboard JSON exported to {OUTPUT_DIR}")


def export_dashboard_summary(db, config):
    """Export main dashboard summary. PnL figures all come from the unified
    analytics module, so every card on the dashboard agrees with every other.
    """
    from backend.analytics import pnl as _pnl

    streams_data: list[dict] = []
    streams_cfg = config.get("streams", {})
    today_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    stream_defs = [
        ("news", "News Stream", streams_cfg.get("news_stream", {}).get("capital_allocation", 100)),
        ("strategy", "Strategy Stream", streams_cfg.get("strategy_stream", {}).get("capital_allocation", 100)),
    ]
    for hybrid in db.get_active_hybrids():
        stream_defs.append((
            f"hybrid:{hybrid['name']}",
            hybrid["name"],
            hybrid.get("capital_allocation", 100),
        ))

    for stream_id, stream_name, capital_allocation in stream_defs:
        agg = _pnl.aggregate_pnl(db, stream=stream_id)
        daily = _pnl.aggregate_pnl(db, stream=stream_id, since=today_iso)
        open_trades = db.get_open_trades(stream_id)
        signals = db.get_signals(stream=stream_id, limit=10000)

        equity_points = _pnl.equity_curve(
            db, stream=stream_id, starting_capital=float(capital_allocation),
        )
        current_equity = equity_points[-1]["equity"] if equity_points else float(capital_allocation)

        # Sharpe / drawdown are historical time-series metrics; keep reading
        # from equity_snapshots so hybrids that still have history don't lose
        # them. For news/strategy (stream snapshots retired) these will now
        # default to 0 — acceptable until we rebuild these metrics on top of
        # the step-function curve.
        eq_history = db.get_equity_history(stream_id)
        sharpe = _compute_sharpe(eq_history) if eq_history else 0.0
        max_dd = _compute_max_drawdown(eq_history) if eq_history else 0.0

        streams_data.append({
            "id": stream_id,
            "name": stream_name,
            "equity": round(current_equity, 2),
            "capital_allocation": capital_allocation,
            "total_pnl": round(agg.total_pnl, 2),
            "daily_pnl": round(daily.total_pnl, 2),
            "trade_count": agg.trade_count,
            "signal_count": len(signals),
            "open_positions": len(open_trades),
            "win_rate": round(agg.win_rate, 3),
            "sharpe_ratio": round(sharpe, 2),
            "max_drawdown": round(max_dd, 4),
        })

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "streams": streams_data,
        "strategy_breakdown": _get_strategy_breakdown(db),
        "instrument_breakdown": _get_instrument_breakdown(db),
    }

    _write_json("dashboard.json", summary)


def export_trades(db):
    """Export recent trades with trade events timeline."""
    # Always include ALL open trades regardless of age
    open_trades = db.get_open_trades()
    open_ids = {t["id"] for t in open_trades}

    # Get recent trades (may overlap with open trades)
    recent_trades = db.get_trades(limit=200)

    # Merge: open trades first, then recent that aren't already included
    all_trades = list(open_trades)
    for t in recent_trades:
        if t["id"] not in open_ids:
            all_trades.append(t)

    trade_list = []
    for t in all_trades:
        events = db.get_trade_events(t["id"])

        # Extract close context from events if present
        close_context = None
        for e in events:
            if e.get("event_type") == "close_context":
                close_context = e.get("data")

        # Count snapshots for summary stats
        snapshots = [e for e in events if e.get("event_type") == "snapshot"]
        latest_snapshot = snapshots[-1] if snapshots else None

        trade_entry = {
            "id": t["id"],
            "stream": t.get("stream") or t.get("source"),
            "instrument": t["instrument"],
            "direction": t["direction"],
            "entry_price": t["entry_price"],
            "exit_price": t.get("exit_price"),
            "stop_loss": t["stop_loss"],
            "take_profit": t["take_profit"],
            "position_size": t.get("position_size") or t.get("size"),
            "pnl": t.get("pnl"),
            "pnl_pips": t.get("pnl_pips"),
            "status": t["status"],
            "opened_at": t.get("opened_at"),
            "closed_at": t.get("closed_at"),
            "broker_deal_id": t.get("broker_deal_id"),
            "events": events,
        }

        # Build narrative record for the drill-down timeline
        signal_id = t.get("signal_id")
        signal_data = None
        if signal_id:
            sig_row = db.execute(
                "SELECT * FROM signals WHERE id = ? LIMIT 1", (signal_id,)
            ).fetchone()
            if sig_row:
                signal_data = dict(sig_row)
                _parse_signal_json(signal_data)
                trade_entry["reasoning"] = signal_data.get("reasoning")
                trade_entry["source"] = signal_data.get("source")

        # Try trade_records table first, then build from signal data
        stored_record = db.get_trade_record(t["id"])
        if stored_record:
            rec = stored_record.get("record", {})
        elif signal_data:
            rec = {
                "signal": {
                    "direction": signal_data.get("direction"),
                    "confidence": signal_data.get("confidence"),
                    "reasoning": signal_data.get("reasoning"),
                    "key_factors": signal_data.get("key_factors"),
                    "risk_factors": signal_data.get("risk_factors"),
                    "parameters": signal_data.get("metadata", {}).get("parameters") if isinstance(signal_data.get("metadata"), dict) else None,
                },
                "headlines_analysed": signal_data.get("headlines_used"),
                "challenge": signal_data.get("challenge_output"),
                "price_context_at_signal": signal_data.get("price_context"),
                "bias_at_trade": signal_data.get("bias_check"),
                "risk_decision": signal_data.get("risk_check"),
            }
        else:
            rec = {}

        # Always attach entry info
        rec["entry"] = {
            "price": t.get("entry_price"),
            "time": t.get("opened_at"),
            "broker_deal_id": t.get("broker_deal_id"),
        }

        # Attach exit info if closed
        if t.get("status") != "open":
            rec["exit"] = {
                "price": t.get("exit_price"),
                "time": t.get("closed_at"),
                "pnl": t.get("pnl"),
                "pnl_pips": t.get("pnl_pips"),
                "close_reason": t.get("close_reason"),
            }

        trade_entry["record"] = rec

        if close_context:
            trade_entry["close_context"] = close_context

        if latest_snapshot and latest_snapshot.get("data"):
            trade_entry["latest_snapshot"] = latest_snapshot["data"]

        trade_list.append(trade_entry)

    _write_json("trades.json", {"trades": trade_list})


def export_equity(db):
    """Export equity curves for all streams.

    Stream curves are step functions derived directly from closed trades (via
    the unified analytics module) — every point maps to a real trade close,
    so the JSON cannot drift from the trade ledger.

    The ``account`` curve is still sourced from ``equity_snapshots`` because
    it's the only stream that captures live broker balance (incl. unrealized
    PnL) and can't be reconstructed from closed trades alone.
    """
    from backend.analytics import pnl as _pnl
    from backend.core.config import load_config

    config = load_config(db=db)
    curves: dict[str, list[dict]] = {}

    for stream_id in ("news", "strategy"):
        cap = _pnl.stream_capital(config, stream_id)
        curve = _pnl.equity_curve(db, stream=stream_id, starting_capital=cap)
        curves[stream_id] = [
            {"time": p["timestamp"], "equity": p["equity"], "positions": None}
            for p in curve
        ]

    account_history = db.get_equity_history("account")
    curves["account"] = [
        {"time": h["recorded_at"], "equity": h["equity"], "positions": h["open_positions"]}
        for h in account_history
    ]

    for hybrid in db.get_active_hybrids():
        hid = f"hybrid:{hybrid['name']}"
        cap = float(hybrid.get("capital_allocation", 100) or 100)
        curve = _pnl.equity_curve(db, stream=hid, starting_capital=cap)
        curves[hid] = [
            {"time": p["timestamp"], "equity": p["equity"], "positions": None}
            for p in curve
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
            "stream": s.get("stream") or s.get("source"),
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


def export_bias(db):
    """Export current directional bias per instrument, enriched with PnL.

    Mirrors ``/api/bias``: maps ``current_bias`` → ``direction`` /
    ``bias_strength`` → ``strength`` for the frontend, and joins in realized
    PnL + trade count from the unified analytics module.
    """
    from backend.analytics import pnl as _pnl

    states = db.get_bias_state()
    for s in states:
        val = s.get("contributing_signals")
        if isinstance(val, str):
            try:
                s["contributing_signals"] = json.loads(val)
            except (json.JSONDecodeError, TypeError):
                pass

    pnl_by_inst = {r["instrument"]: r for r in _pnl.per_instrument_breakdown(db)}
    bias_by_inst = {s.get("instrument"): s for s in states}
    all_instruments = set(bias_by_inst) | set(pnl_by_inst)

    enriched: list[dict] = []
    for inst in all_instruments:
        s = bias_by_inst.get(inst, {})
        p = pnl_by_inst.get(inst, {})
        enriched.append({
            **s,
            "instrument": inst,
            "direction": s.get("current_bias") or "neutral",
            "strength": s.get("bias_strength") or 0.0,
            "total_pnl": p.get("total_pnl", 0.0),
            "trade_count": p.get("trade_count", 0),
        })
    _write_json("bias.json", {"bias": enriched})


def export_llm_activity(db):
    """Export LLM pipeline activity. Matches /api/llm/activity shape."""
    # Headlines grouped by source (last 24h for static export)
    headlines = db.get_recent_headlines(hours=24)
    for h in headlines:
        val = h.get("source_metadata")
        if isinstance(val, str):
            try:
                h["source_metadata"] = json.loads(val)
            except (json.JSONDecodeError, TypeError):
                pass
    headlines_by_source: dict[str, list] = {}
    for h in headlines:
        src = h.get("source", "unknown")
        headlines_by_source.setdefault(src, []).append(h)

    # Relevance assessments with headline text
    assessments = db.get_relevance_with_headlines(hours=24, limit=200)

    # LLM signals
    signals = db.get_signals(source="llm", limit=100)
    json_cols = [
        "key_factors", "risk_factors", "headlines_used", "price_context",
        "challenge_output", "bias_check", "risk_check", "metadata",
    ]
    for s in signals:
        for col in json_cols:
            val = s.get(col)
            if isinstance(val, str):
                try:
                    s[col] = json.loads(val)
                except (json.JSONDecodeError, TypeError):
                    pass

    _write_json("llm_activity.json", {
        "headlines_by_source": headlines_by_source,
        "relevance_assessments": assessments,
        "signals": signals,
        "summary": {
            "headlines_count": len(headlines),
            "assessments_count": len(assessments),
            "signals_count": len(signals),
            "hours_lookback": 24,
        },
    })


def export_strategies_detail(db):
    """Export strategy definitions + signals + trade stats. Matches /api/strategies shape."""
    json_cols = [
        "key_factors", "risk_factors", "headlines_used", "price_context",
        "challenge_output", "bias_check", "risk_check", "metadata",
    ]

    # Try to load strategy classes for descriptions/parameters.
    # Falls back to DB-only approach if dependencies (e.g. pandas) are missing.
    strategy_info = {}
    try:
        from backend.strategies.registry import discover_strategies
        for name, cls in discover_strategies().items():
            instance = cls()
            strategy_info[name] = {
                "name": instance.name,
                "description": instance.description,
                "parameters": instance.get_parameters(),
            }
    except ImportError:
        logger.warning("Strategy classes unavailable (missing deps), using DB-only export")

    # Discover strategy names from signals if registry failed
    if not strategy_info:
        rows = db.execute(
            "SELECT DISTINCT source FROM signals WHERE source LIKE 'strategy:%'"
        ).fetchall()
        for r in rows:
            name = dict(r)["source"].replace("strategy:", "")
            strategy_info[name] = {"name": name, "description": "", "parameters": {}}

    result = []
    for name, info in strategy_info.items():
        source_key = f"strategy:{name}"

        recent_signals = db.get_signals(source=source_key, limit=10)
        for s in recent_signals:
            for col in json_cols:
                val = s.get(col)
                if isinstance(val, str):
                    try:
                        s[col] = json.loads(val)
                    except (json.JSONDecodeError, TypeError):
                        pass

        all_trades = db.query(
            "SELECT * FROM trades WHERE source = ? ORDER BY opened_at DESC",
            (source_key,),
        )
        closed = [t for t in all_trades if t.get("pnl") is not None]
        wins = sum(1 for t in closed if t["pnl"] > 0)
        total_pnl = sum(t["pnl"] for t in closed)

        result.append({
            "name": info["name"],
            "description": info["description"],
            "parameters": info["parameters"],
            "recent_signals": [
                {
                    "instrument": s["instrument"],
                    "direction": s["direction"],
                    "confidence": s["confidence"],
                    "created_at": s["created_at"],
                }
                for s in recent_signals
            ],
            "trade_stats": {
                "total": len(all_trades),
                "won": wins,
                "lost": len(closed) - wins,
                "net_pnl": round(total_pnl, 2),
                "win_rate": round(wins / len(closed), 3) if closed else 0,
            },
        })

    _write_json("strategies.json", {"strategies": result})


def export_prompts(db):
    """Export current prompts with versions. Matches /api/prompts shape."""
    prompts = db.get_all_prompts()
    _write_json("prompts.json", {"prompts": prompts})


def _get_strategy_breakdown(db) -> list[dict]:
    """Per-strategy performance metrics (delegates to unified analytics)."""
    from backend.analytics import pnl as _pnl
    return _pnl.per_strategy_breakdown(db)


def _get_instrument_breakdown(db) -> list[dict]:
    """Per-instrument P&L across all streams (delegates to unified analytics).

    Preserves the legacy ``count`` field alongside the unified ``trade_count``
    for consumers that already rely on the old name.
    """
    from backend.analytics import pnl as _pnl
    rows = _pnl.per_instrument_breakdown(db)
    return [
        {
            "instrument": r["instrument"],
            "count": r["trade_count"],
            "trade_count": r["trade_count"],
            "total_pnl": r["total_pnl"],
            "win_rate": r["win_rate"],
        }
        for r in rows
    ]


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


_SIGNAL_JSON_COLS = [
    "key_factors", "risk_factors", "headlines_used", "price_context",
    "challenge_output", "bias_check", "risk_check", "metadata",
]


def _parse_signal_json(row: dict):
    """Parse JSON-string columns on a signal row in place."""
    for col in _SIGNAL_JSON_COLS:
        val = row.get(col)
        if isinstance(val, str):
            try:
                row[col] = json.loads(val)
            except (json.JSONDecodeError, TypeError):
                pass


def _write_json(filename: str, data: dict):
    path = OUTPUT_DIR / filename
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)
    logger.debug(f"Wrote {path}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    export_all()
