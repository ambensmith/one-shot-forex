"""Forex Sentinel — CLI entry point."""

import argparse
import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

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
logger = logging.getLogger("forex_sentinel")


def is_market_open() -> bool:
    """Returns True if forex market is currently open.
    Open: Sunday 22:00 UTC through Friday 22:00 UTC."""
    now = datetime.now(timezone.utc)
    weekday = now.weekday()  # 0=Mon, 6=Sun
    hour = now.hour

    if weekday == 5:  # Saturday
        return False
    if weekday == 6 and hour < 22:  # Sunday before 22:00
        return False
    if weekday == 4 and hour >= 22:  # Friday after 22:00
        return False
    return True


def should_generate_review(config) -> bool:
    """Check if a review should be generated this cycle."""
    if not config.get("reviews", {}).get("auto_generate", False):
        return False
    now = datetime.now(timezone.utc)
    review_time = config.get("reviews", {}).get("time", "22:00")
    hour, minute = map(int, review_time.split(":"))
    return now.hour == hour and now.minute < 5


def create_data_provider(config: dict):
    """Factory: instantiate the configured data provider."""
    provider = config.get("execution", {}).get("data_provider", "oanda")
    if provider == "capitalcom":
        from backend.data.capitalcom_client import CapitalComClient
        return CapitalComClient(config)
    else:
        from backend.data.oanda_client import OandaClient
        return OandaClient(config)


async def run_tick(stream_filter: str = "all", force_market_open: bool = False):
    """Execute one trading cycle across active streams.

    Args:
        stream_filter: "all", "news", "strategy", or "hybrid"
        force_market_open: bypass market hours check
    """
    from backend.core.config import load_config
    from backend.core.database import Database
    from backend.risk.risk_manager import RiskManager
    from backend.execution.executor import Executor

    if force_market_open:
        import backend.main
        backend.main.is_market_open = lambda: True

    config = load_config()
    db = Database("data/sentinel.db")
    oanda = create_data_provider(config)
    risk = RiskManager(config, oanda, db)
    executor = Executor(config, oanda, db)

    if not is_market_open():
        logger.info("Market closed. Skipping cycle.")
        return

    streams_cfg = config.get("streams", {})

    # Run News Stream
    if stream_filter in ("all", "news"):
        if streams_cfg.get("news_stream", {}).get("enabled", False):
            from backend.streams.news_stream import NewsStream
            news_stream = NewsStream(
                config=config, db=db, oanda=oanda,
                risk=risk, executor=executor,
            )
            await news_stream.tick()

    # Run Strategy Stream
    if stream_filter in ("all", "strategy"):
        if streams_cfg.get("strategy_stream", {}).get("enabled", False):
            from backend.streams.strategy_stream import StrategyStream
            strategy_stream = StrategyStream(
                config=config, db=db, oanda=oanda,
                risk=risk, executor=executor,
            )
            await strategy_stream.tick()

    # Run all active Hybrid Streams
    if stream_filter in ("all", "hybrid"):
        from backend.streams.hybrid_stream import HybridStream
        for hybrid_config in db.get_active_hybrids():
            hybrid = HybridStream(
                hybrid_config=hybrid_config,
                config=config, db=db, oanda=oanda,
                risk=risk, executor=executor,
            )
            await hybrid.tick()

    # Record equity snapshots
    _record_all_equity(db, oanda)

    # Generate review if due
    if stream_filter == "all" and should_generate_review(config):
        from backend.reviews.generator import ReviewGenerator
        ReviewGenerator(db, config).generate(trigger="scheduled")

    logger.info(f"Trading cycle complete (stream={stream_filter}).")


def _record_all_equity(db, oanda):
    """Record equity snapshots for all streams."""
    for stream_id in ["news", "strategy"]:
        equity = db.get_stream_equity(stream_id)
        open_count = db.count_open_positions(stream_id)
        db.insert_equity_snapshot(stream_id, equity, open_count)
    for hybrid in db.get_active_hybrids():
        sid = f"hybrid:{hybrid['name']}"
        equity = db.get_stream_equity(sid)
        open_count = db.count_open_positions(sid)
        db.insert_equity_snapshot(sid, equity, open_count)


def run_reset():
    """Clear all data for a clean slate."""
    from backend.core.config import load_config
    from backend.core.database import Database

    config = load_config()
    db = Database("data/sentinel.db")
    db.execute("DELETE FROM signals")
    db.execute("DELETE FROM trades")
    db.execute("DELETE FROM equity_snapshots")
    db.execute("DELETE FROM news_items")
    db.commit()
    db.close()
    logger.info("Database reset complete.")


def run_save_hybrid(hybrid_json: str):
    """Save a hybrid config from JSON string."""
    from backend.core.database import Database

    db = Database("data/sentinel.db")
    data = json.loads(hybrid_json)

    name = data["name"]

    # Check if hybrid with this name already exists
    existing = db.execute(
        "SELECT id FROM hybrid_configs WHERE name = ?", (name,)
    ).fetchone()

    if existing:
        db.update_hybrid_config(
            existing["id"],
            description=data.get("description", ""),
            modules=data.get("modules", []),
            combiner_mode=data.get("combiner_mode", "weighted"),
            instruments=data.get("instruments", []),
            interval=data.get("interval", "1h"),
            is_active=data.get("is_active", 1),
        )
        logger.info(f"Updated hybrid config: {name}")
    else:
        db.insert_hybrid_config(
            name=name,
            description=data.get("description", ""),
            modules=data.get("modules", []),
            combiner_mode=data.get("combiner_mode", "weighted"),
            instruments=data.get("instruments", []),
            interval=data.get("interval", "1h"),
            is_active=data.get("is_active", 1),
        )
        logger.info(f"Created hybrid config: {name}")

    db.close()


def main():
    parser = argparse.ArgumentParser(description="Forex Sentinel")
    parser.add_argument(
        "--mode",
        choices=["tick", "backtest", "review", "reset", "save-hybrid"],
        default="tick",
        help="tick: run trading cycle. reset: clear all data. review: generate Cowork review. save-hybrid: save a hybrid config.",
    )
    parser.add_argument(
        "--stream",
        choices=["all", "news", "strategy", "hybrid"],
        default="all",
        help="Which stream to run (tick mode only).",
    )
    parser.add_argument(
        "--force-market-open",
        action="store_true",
        help="Bypass market hours check.",
    )
    parser.add_argument("--strategy", help="Strategy name for backtest mode")
    parser.add_argument("--instrument", help="Instrument for backtest mode")
    parser.add_argument("--period", help="Period for review, e.g. '7d' or '30d'")
    parser.add_argument("--hybrid-json", help="Hybrid config as JSON string (save-hybrid mode)")
    args = parser.parse_args()

    if args.mode == "tick":
        asyncio.run(run_tick(
            stream_filter=args.stream,
            force_market_open=args.force_market_open,
        ))
    elif args.mode == "reset":
        run_reset()
    elif args.mode == "save-hybrid":
        if not args.hybrid_json:
            parser.error("--hybrid-json is required for save-hybrid mode")
        run_save_hybrid(args.hybrid_json)
    elif args.mode == "backtest":
        from backend.backtest.runner import run_backtest
        run_backtest(args.strategy, args.instrument)
    elif args.mode == "review":
        from backend.reviews.generator import ReviewGenerator
        ReviewGenerator.from_cli(args.period)


if __name__ == "__main__":
    main()
