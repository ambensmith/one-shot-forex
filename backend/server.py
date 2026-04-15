"""FastAPI server — exposes endpoints to trigger trading streams and serve data to the frontend."""

from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

logger = logging.getLogger("forex_sentinel.server")

Path("data").mkdir(exist_ok=True)
Path("logs").mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(Path("logs/app.log"), mode="a"),
    ],
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Forex Sentinel API server starting")
    yield
    logger.info("Forex Sentinel API server shutting down")


app = FastAPI(title="Forex Sentinel", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _get_components():
    """Create fresh DB, data provider, risk manager, executor."""
    from backend.core.config import load_config
    from backend.core.database import Database
    from backend.main import create_data_provider
    from backend.risk.risk_manager import RiskManager
    from backend.execution.executor import Executor

    config = load_config()
    db = Database("data/sentinel.db")
    broker = create_data_provider(config)
    risk = RiskManager(config, broker, db)
    executor = Executor(config, broker, db)
    return config, db, broker, risk, executor


def _export_json(db, config):
    """Re-export all dashboard JSON files."""
    from backend.dashboard.json_exporter import (
        export_dashboard_summary,
        export_trades,
        export_equity,
        export_signals,
        export_models,
        export_config,
        export_review,
        export_hybrids,
        export_run_reviews,
        OUTPUT_DIR,
    )
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    export_dashboard_summary(db, config)
    export_trades(db)
    export_equity(db)
    export_signals(db)
    export_models(db, config)
    export_config(config)
    export_review(db, config)
    export_hybrids(db)
    export_run_reviews(db)


def _count_results(db, stream_id: str, before_signals: int, before_trades: int) -> dict:
    """Count new signals and trades since the stream ran."""
    all_signals = db.get_signals(stream=stream_id, limit=1000)
    all_trades = db.get_trades(stream=stream_id, limit=1000)
    open_trades = db.get_open_trades(stream_id)

    new_signals = len(all_signals) - before_signals
    new_trades = len(all_trades) - before_trades

    rejected = [s for s in all_signals[:new_signals] if s.get("rejection_reason")]

    return {
        "stream": stream_id,
        "new_signals": new_signals,
        "new_trades": new_trades,
        "open_positions": len(open_trades),
        "total_signals": len(all_signals),
        "total_trades": len(all_trades),
        "rejections": [
            {"instrument": s["instrument"], "reason": s["rejection_reason"]}
            for s in rejected[:10]
        ],
    }


def _force_market_open():
    """Monkey-patch is_market_open to always return True for testing."""
    import backend.main
    backend.main.is_market_open = lambda: True


@app.post("/api/run-stream/news")
async def run_news_stream():
    """Run the news stream: fetch news, LLM analysis, risk check, trade."""
    _force_market_open()
    config, db, broker, risk, executor = _get_components()

    before_signals = len(db.get_signals(stream="news", limit=10000))
    before_trades = len(db.get_trades(stream="news", limit=10000))

    try:
        from backend.streams.news_stream import NewsStream
        stream = NewsStream(config=config, db=db, broker=broker, risk=risk, executor=executor)
        signals = await stream.tick()

        _export_json(db, config)
        result = _count_results(db, "news", before_signals, before_trades)
        result["signals_detail"] = [
            {
                "instrument": s.instrument,
                "direction": s.direction,
                "confidence": s.confidence,
                "reasoning": s.reasoning[:200] if s.reasoning else "",
            }
            for s in signals[:10]
        ]
        return JSONResponse({"status": "ok", **result})
    except Exception as e:
        logger.exception("News stream failed")
        return JSONResponse({"status": "error", "error": str(e)}, status_code=500)
    finally:
        db.close()


@app.post("/api/run-stream/strategy")
async def run_strategy_stream():
    """Run the strategy stream: all 5 mechanical strategies."""
    _force_market_open()
    config, db, broker, risk, executor = _get_components()

    before_signals = len(db.get_signals(stream="strategy", limit=10000))
    before_trades = len(db.get_trades(stream="strategy", limit=10000))

    try:
        from backend.streams.strategy_stream import StrategyStream
        stream = StrategyStream(config=config, db=db, broker=broker, risk=risk, executor=executor)
        signals = await stream.tick()

        _export_json(db, config)
        result = _count_results(db, "strategy", before_signals, before_trades)
        result["signals_detail"] = [
            {
                "instrument": s.instrument,
                "direction": s.direction,
                "confidence": s.confidence,
                "source": s.sources[0] if s.sources else "",
            }
            for s in signals[:30]
        ]
        return JSONResponse({"status": "ok", **result})
    except Exception as e:
        logger.exception("Strategy stream failed")
        return JSONResponse({"status": "error", "error": str(e)}, status_code=500)
    finally:
        db.close()


@app.post("/api/run-stream/hybrid")
async def run_hybrid_stream():
    """Run all active hybrid streams."""
    _force_market_open()
    config, db, broker, risk, executor = _get_components()

    results = []
    try:
        from backend.streams.hybrid_stream import HybridStream
        active_hybrids = db.get_active_hybrids()

        if not active_hybrids:
            _export_json(db, config)
            return JSONResponse({
                "status": "ok",
                "message": "No active hybrid configs found. Create one first.",
                "results": [],
            })

        for hybrid_config in active_hybrids:
            hid = f"hybrid:{hybrid_config['name']}"
            before_signals = len(db.get_signals(stream=hid, limit=10000))
            before_trades = len(db.get_trades(stream=hid, limit=10000))

            hybrid = HybridStream(
                hybrid_config=hybrid_config,
                config=config, db=db, broker=broker,
                risk=risk, executor=executor,
            )
            await hybrid.tick()
            results.append(_count_results(db, hid, before_signals, before_trades))

        _export_json(db, config)
        return JSONResponse({"status": "ok", "results": results})
    except Exception as e:
        logger.exception("Hybrid stream failed")
        return JSONResponse({"status": "error", "error": str(e)}, status_code=500)
    finally:
        db.close()


@app.post("/api/run-all")
async def run_all_streams():
    """Run all enabled streams sequentially."""
    _force_market_open()
    config, db, broker, risk, executor = _get_components()

    results = {}
    try:
        streams_cfg = config.get("streams", {})

        # News stream
        if streams_cfg.get("news_stream", {}).get("enabled", False):
            from backend.streams.news_stream import NewsStream
            before_s = len(db.get_signals(stream="news", limit=10000))
            before_t = len(db.get_trades(stream="news", limit=10000))
            stream = NewsStream(config=config, db=db, broker=broker, risk=risk, executor=executor)
            await stream.tick()
            results["news"] = _count_results(db, "news", before_s, before_t)

        # Strategy stream
        if streams_cfg.get("strategy_stream", {}).get("enabled", False):
            from backend.streams.strategy_stream import StrategyStream
            before_s = len(db.get_signals(stream="strategy", limit=10000))
            before_t = len(db.get_trades(stream="strategy", limit=10000))
            stream = StrategyStream(config=config, db=db, broker=broker, risk=risk, executor=executor)
            await stream.tick()
            results["strategy"] = _count_results(db, "strategy", before_s, before_t)

        # Hybrid streams
        from backend.streams.hybrid_stream import HybridStream
        hybrid_results = []
        for hybrid_config in db.get_active_hybrids():
            hid = f"hybrid:{hybrid_config['name']}"
            before_s = len(db.get_signals(stream=hid, limit=10000))
            before_t = len(db.get_trades(stream=hid, limit=10000))
            hybrid = HybridStream(
                hybrid_config=hybrid_config,
                config=config, db=db, broker=broker,
                risk=risk, executor=executor,
            )
            await hybrid.tick()
            hybrid_results.append(_count_results(db, hid, before_s, before_t))
        if hybrid_results:
            results["hybrid"] = hybrid_results

        # Record equity for all streams
        from backend.main import _record_all_equity
        _record_all_equity(db, broker)

        _export_json(db, config)
        return JSONResponse({"status": "ok", "results": results})
    except Exception as e:
        logger.exception("Run all failed")
        return JSONResponse({"status": "error", "error": str(e)}, status_code=500)
    finally:
        db.close()


@app.post("/api/reset")
async def reset_data():
    """Clear all data for a clean slate."""
    from backend.core.config import load_config
    from backend.core.database import Database

    config = load_config()
    db = Database("data/sentinel.db")
    try:
        db.execute("DELETE FROM signals")
        db.execute("DELETE FROM trades")
        db.execute("DELETE FROM equity_snapshots")
        db.execute("DELETE FROM news_items")
        db.commit()

        _export_json(db, config)
        logger.info("Database reset complete")
        return JSONResponse({"status": "ok", "message": "All data cleared"})
    except Exception as e:
        logger.exception("Reset failed")
        return JSONResponse({"status": "error", "error": str(e)}, status_code=500)
    finally:
        db.close()


@app.post("/api/refresh-data")
async def refresh_data():
    """Re-export all dashboard JSON files from the database without running any trading."""
    from backend.core.config import load_config
    from backend.core.database import Database

    config = load_config()
    db = Database("data/sentinel.db")
    try:
        _export_json(db, config)
        return JSONResponse({"status": "ok", "message": "Dashboard data refreshed"})
    except Exception as e:
        logger.exception("Refresh data failed")
        return JSONResponse({"status": "error", "error": str(e)}, status_code=500)
    finally:
        db.close()



@app.post("/api/hybrid/{config_id}/toggle")
async def toggle_hybrid(config_id: int, request: Request):
    """Toggle a hybrid config's is_active status."""
    from backend.core.config import load_config
    from backend.core.database import Database

    config = load_config()
    db = Database("data/sentinel.db")
    try:
        body = await request.json()
        is_active = int(bool(body.get("is_active", False)))
        db.update_hybrid_config(config_id, is_active=is_active)
        _export_json(db, config)
        logger.info("Toggled hybrid %d → is_active=%d", config_id, is_active)
        return JSONResponse({"status": "ok", "is_active": bool(is_active)})
    except Exception as e:
        logger.exception("Toggle hybrid failed")
        return JSONResponse({"status": "error", "error": str(e)}, status_code=500)
    finally:
        db.close()


@app.post("/api/hybrid/toggle-all")
async def toggle_all_hybrids(request: Request):
    """Toggle all hybrid configs on or off."""
    from backend.core.config import load_config
    from backend.core.database import Database

    config = load_config()
    db = Database("data/sentinel.db")
    try:
        body = await request.json()
        is_active = int(bool(body.get("is_active", False)))
        for hybrid in db.get_all_hybrids():
            db.update_hybrid_config(hybrid["id"], is_active=is_active)
        _export_json(db, config)
        logger.info("Toggled all hybrids → is_active=%d", is_active)
        return JSONResponse({"status": "ok", "is_active": bool(is_active)})
    except Exception as e:
        logger.exception("Toggle all hybrids failed")
        return JSONResponse({"status": "error", "error": str(e)}, status_code=500)
    finally:
        db.close()


@app.delete("/api/hybrid/{config_id}")
async def delete_hybrid(config_id: int):
    """Delete a hybrid config."""
    from backend.core.config import load_config
    from backend.core.database import Database

    config = load_config()
    db = Database("data/sentinel.db")
    try:
        db.delete_hybrid_config(config_id)
        _export_json(db, config)
        logger.info("Deleted hybrid config %d", config_id)
        return JSONResponse({"status": "ok", "message": f"Hybrid {config_id} deleted"})
    except Exception as e:
        logger.exception("Delete hybrid failed")
        return JSONResponse({"status": "error", "error": str(e)}, status_code=500)
    finally:
        db.close()


@app.get("/api/status")
async def get_status():
    """Return current system status."""
    from backend.core.database import Database

    db = Database("data/sentinel.db")
    try:
        streams = {}
        for sid in ["news", "strategy"]:
            signals = db.get_signals(stream=sid, limit=10000)
            trades = db.get_trades(stream=sid, limit=10000)
            open_trades = db.get_open_trades(sid)
            equity = db.get_stream_equity(sid)
            streams[sid] = {
                "signals": len(signals),
                "trades": len(trades),
                "open_positions": len(open_trades),
                "equity": equity,
            }

        for hybrid in db.get_active_hybrids():
            hid = f"hybrid:{hybrid['name']}"
            signals = db.get_signals(stream=hid, limit=10000)
            trades = db.get_trades(stream=hid, limit=10000)
            open_trades = db.get_open_trades(hid)
            equity = db.get_stream_equity(hid)
            streams[hid] = {
                "signals": len(signals),
                "trades": len(trades),
                "open_positions": len(open_trades),
                "equity": equity,
            }

        return JSONResponse({"status": "ok", "streams": streams})
    finally:
        db.close()


# ── Helpers for data endpoints ─────────────────────────────────


_SIGNAL_JSON_COLS = [
    "key_factors", "risk_factors", "headlines_used", "price_context",
    "challenge_output", "bias_check", "risk_check", "metadata",
]
_BIAS_JSON_COLS = ["contributing_signals"]


def _parse_json_fields(row: dict, columns: list[str]) -> dict:
    """Parse JSON-string columns back to Python objects in place."""
    for col in columns:
        val = row.get(col)
        if isinstance(val, str):
            try:
                row[col] = json.loads(val)
            except (json.JSONDecodeError, TypeError):
                pass
    return row


def _duration_seconds(start: str | None, end: str | None = None) -> int | None:
    """Compute duration in seconds between two ISO timestamps. If end is None, use now."""
    if not start:
        return None
    try:
        t0 = datetime.fromisoformat(start)
        if t0.tzinfo is None:
            t0 = t0.replace(tzinfo=timezone.utc)
        t1 = datetime.now(timezone.utc)
        if end:
            t1 = datetime.fromisoformat(end)
            if t1.tzinfo is None:
                t1 = t1.replace(tzinfo=timezone.utc)
        return max(0, int((t1 - t0).total_seconds()))
    except (ValueError, TypeError):
        return None


def _get_db():
    """Shorthand for creating a Database connection."""
    from backend.core.database import Database
    return Database("data/sentinel.db")


# ── Session 10: Data-serving endpoints ─────────────────────────


@app.get("/api/trades/open")
async def api_trades_open():
    """Open trades enriched with current prices and unrealized P&L."""
    from backend.data.provider import pip_value

    db = _get_db()
    try:
        trades = db.get_open_trades()
        prices = db.get_latest_prices()

        result = []
        for t in trades:
            price_info = prices.get(t["instrument"])
            current_price = price_info["mid"] if price_info else None

            unrealized_pnl = None
            unrealized_pnl_pips = None
            if current_price and t.get("entry_price"):
                diff = current_price - t["entry_price"]
                if t["direction"] == "short":
                    diff = -diff
                pip_val = pip_value(t["instrument"])
                unrealized_pnl_pips = round(diff / pip_val, 1)
                size = t.get("size") or 1
                unrealized_pnl = round(diff * size, 4)

            result.append({
                **t,
                "current_price": current_price,
                "unrealized_pnl": unrealized_pnl,
                "unrealized_pnl_pips": unrealized_pnl_pips,
                "duration_seconds": _duration_seconds(t.get("opened_at")),
            })

        return JSONResponse({"trades": result})
    finally:
        db.close()


@app.get("/api/trades/closed")
async def api_trades_closed(
    filter: str | None = None,
    instrument: str | None = None,
    source: str | None = None,
    days: int | None = None,
    limit: int = 20,
):
    """Closed trades with optional filters for outcome, instrument, source, recency."""
    db = _get_db()
    try:
        trades = db.get_closed_trades(
            outcome=filter, instrument=instrument, source=source,
            days=days, limit=limit,
        )
        for t in trades:
            t["duration_seconds"] = _duration_seconds(t.get("opened_at"), t.get("closed_at"))
        return JSONResponse({"trades": trades, "count": len(trades)})
    finally:
        db.close()


@app.get("/api/trades/{trade_id}")
async def api_trade_detail(trade_id: str):
    """Full trade record for the narrative timeline drill-down."""
    db = _get_db()
    try:
        record = db.get_trade_record(trade_id)
        if record:
            # Ensure all DESIGN.md Section 8 chapter keys are present
            chapter_keys = [
                "headlines_analysed", "signal", "challenge",
                "price_context_at_signal", "bias_at_trade",
                "risk_decision", "entry", "exit",
            ]
            rec = record.get("record", {})
            for key in chapter_keys:
                if key not in rec:
                    rec[key] = None
            record["record"] = rec
            return JSONResponse({"trade": record})

        # Fallback: construct basic record from trades + signals tables
        rows = db.query("SELECT * FROM trades WHERE id = ? LIMIT 1", (trade_id,))
        if not rows:
            return JSONResponse({"error": "Trade not found"}, status_code=404)

        trade = rows[0]
        signal_data = None
        if trade.get("signal_id"):
            sig_rows = db.query(
                "SELECT * FROM signals WHERE id = ? LIMIT 1", (trade["signal_id"],)
            )
            if sig_rows:
                signal_data = _parse_json_fields(sig_rows[0], _SIGNAL_JSON_COLS)

        fallback_record = {
            "headlines_analysed": None,
            "signal": signal_data,
            "challenge": signal_data.get("challenge_output") if signal_data else None,
            "price_context_at_signal": signal_data.get("price_context") if signal_data else None,
            "bias_at_trade": signal_data.get("bias_check") if signal_data else None,
            "risk_decision": signal_data.get("risk_check") if signal_data else None,
            "entry": {
                "price": trade.get("entry_price"),
                "time": trade.get("opened_at"),
                "broker_deal_id": trade.get("broker_deal_id"),
            },
            "exit": {
                "price": trade.get("exit_price"),
                "time": trade.get("closed_at"),
                "pnl": trade.get("pnl"),
                "pnl_pips": trade.get("pnl_pips"),
                "close_reason": trade.get("close_reason"),
            } if trade.get("status") != "open" else None,
        }
        return JSONResponse({
            "trade": {
                "trade_id": trade["id"],
                "record": fallback_record,
                "created_at": trade.get("opened_at"),
            }
        })
    finally:
        db.close()


@app.get("/api/signals/recent")
async def api_signals_recent(limit: int = 50, source: str | None = None):
    """Recent signals from both streams, optionally filtered by source."""
    db = _get_db()
    try:
        signals = db.get_signals(source=source, limit=limit)
        for s in signals:
            _parse_json_fields(s, _SIGNAL_JSON_COLS)
        return JSONResponse({"signals": signals})
    finally:
        db.close()


@app.get("/api/llm/activity")
async def api_llm_activity(hours: int = 4):
    """LLM pipeline activity: headlines grouped by source, relevance assessments, signals."""
    db = _get_db()
    try:
        # Headlines grouped by source
        headlines = db.get_recent_headlines(hours=hours)
        for h in headlines:
            _parse_json_fields(h, ["source_metadata"])
        headlines_by_source: dict[str, list] = {}
        for h in headlines:
            src = h.get("source", "unknown")
            headlines_by_source.setdefault(src, []).append(h)

        # Relevance assessments with headline text
        assessments = db.get_relevance_with_headlines(hours=hours, limit=200)

        # LLM signals
        signals = db.get_signals(source="llm", limit=100)
        for s in signals:
            _parse_json_fields(s, _SIGNAL_JSON_COLS)

        return JSONResponse({
            "headlines_by_source": headlines_by_source,
            "relevance_assessments": assessments,
            "signals": signals,
            "summary": {
                "headlines_count": len(headlines),
                "assessments_count": len(assessments),
                "signals_count": len(signals),
                "hours_lookback": hours,
            },
        })
    finally:
        db.close()


@app.get("/api/strategies")
async def api_strategies():
    """Strategy definitions with recent signals and trade stats."""
    from backend.strategies.registry import discover_strategies

    db = _get_db()
    try:
        strategy_classes = discover_strategies()
        result = []

        for name, cls in strategy_classes.items():
            instance = cls()
            source_key = f"strategy:{name}"

            # Recent signals for this strategy
            recent_signals = db.get_signals(source=source_key, limit=10)
            for s in recent_signals:
                _parse_json_fields(s, _SIGNAL_JSON_COLS)

            # Trade stats: query trades with this source
            all_trades = db.query(
                "SELECT * FROM trades WHERE source = ? ORDER BY opened_at DESC",
                (source_key,),
            )
            closed = [t for t in all_trades if t.get("pnl") is not None]
            wins = sum(1 for t in closed if t["pnl"] > 0)
            total_pnl = sum(t["pnl"] for t in closed)

            result.append({
                "name": instance.name,
                "description": instance.description,
                "parameters": instance.get_parameters(),
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

        return JSONResponse({"strategies": result})
    finally:
        db.close()


@app.get("/api/prompts")
async def api_prompts():
    """All prompts with versions."""
    db = _get_db()
    try:
        prompts = db.get_all_prompts()
        return JSONResponse({"prompts": prompts})
    finally:
        db.close()


@app.put("/api/prompts/{name}")
async def api_update_prompt(name: str, request: Request):
    """Update a prompt's template and version."""
    db = _get_db()
    try:
        existing = db.get_active_prompt(name)
        if not existing:
            return JSONResponse({"error": f"Prompt '{name}' not found"}, status_code=404)

        body = await request.json()
        template = body.get("template")
        version = body.get("version")
        if not template or not version:
            return JSONResponse(
                {"error": "Both 'template' and 'version' are required"},
                status_code=400,
            )

        db.update_prompt(name, template, version)
        return JSONResponse({"status": "ok", "name": name, "version": version})
    finally:
        db.close()


@app.get("/api/bias")
async def api_bias():
    """Current directional bias per instrument."""
    db = _get_db()
    try:
        states = db.get_bias_state()
        for s in states:
            _parse_json_fields(s, _BIAS_JSON_COLS)
        return JSONResponse({"bias": states})
    finally:
        db.close()


@app.get("/api/equity")
async def api_equity(stream: str | None = None):
    """Equity snapshots over time, optionally filtered by stream."""
    db = _get_db()
    try:
        history = db.get_equity_history(stream=stream)
        return JSONResponse({"equity": history, "count": len(history)})
    finally:
        db.close()
