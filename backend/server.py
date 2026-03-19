"""FastAPI server — exposes endpoints to trigger trading streams from the frontend."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
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
    oanda = create_data_provider(config)
    risk = RiskManager(config, oanda, db)
    executor = Executor(config, oanda, db)
    return config, db, oanda, risk, executor


def _export_json(db, config):
    """Re-export all dashboard JSON files."""
    from backend.dashboard.json_exporter import (
        export_dashboard_summary,
        export_trades,
        export_equity,
        export_signals,
        export_models,
        OUTPUT_DIR,
    )
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    export_dashboard_summary(db, config)
    export_trades(db)
    export_equity(db)
    export_signals(db)
    export_models(db, config)


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
    config, db, oanda, risk, executor = _get_components()

    before_signals = len(db.get_signals(stream="news", limit=10000))
    before_trades = len(db.get_trades(stream="news", limit=10000))

    try:
        from backend.streams.news_stream import NewsStream
        stream = NewsStream(config=config, db=db, oanda=oanda, risk=risk, executor=executor)
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
    config, db, oanda, risk, executor = _get_components()

    before_signals = len(db.get_signals(stream="strategy", limit=10000))
    before_trades = len(db.get_trades(stream="strategy", limit=10000))

    try:
        from backend.streams.strategy_stream import StrategyStream
        stream = StrategyStream(config=config, db=db, oanda=oanda, risk=risk, executor=executor)
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
    config, db, oanda, risk, executor = _get_components()

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
                config=config, db=db, oanda=oanda,
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
    config, db, oanda, risk, executor = _get_components()

    results = {}
    try:
        streams_cfg = config.get("streams", {})

        # News stream
        if streams_cfg.get("news_stream", {}).get("enabled", False):
            from backend.streams.news_stream import NewsStream
            before_s = len(db.get_signals(stream="news", limit=10000))
            before_t = len(db.get_trades(stream="news", limit=10000))
            stream = NewsStream(config=config, db=db, oanda=oanda, risk=risk, executor=executor)
            await stream.tick()
            results["news"] = _count_results(db, "news", before_s, before_t)

        # Strategy stream
        if streams_cfg.get("strategy_stream", {}).get("enabled", False):
            from backend.streams.strategy_stream import StrategyStream
            before_s = len(db.get_signals(stream="strategy", limit=10000))
            before_t = len(db.get_trades(stream="strategy", limit=10000))
            stream = StrategyStream(config=config, db=db, oanda=oanda, risk=risk, executor=executor)
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
                config=config, db=db, oanda=oanda,
                risk=risk, executor=executor,
            )
            await hybrid.tick()
            hybrid_results.append(_count_results(db, hid, before_s, before_t))
        if hybrid_results:
            results["hybrid"] = hybrid_results

        # Record equity for all streams
        from backend.main import _record_all_equity
        _record_all_equity(db, oanda)

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
