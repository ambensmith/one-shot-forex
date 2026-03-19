"""Forex Sentinel — CLI entry point."""

import argparse
import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path

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


async def run_tick():
    """Execute one trading cycle across all active streams."""
    from backend.core.config import load_config
    from backend.core.database import Database
    from backend.data.oanda_client import OandaClient
    from backend.risk.risk_manager import RiskManager
    from backend.execution.executor import Executor

    config = load_config()
    db = Database("data/sentinel.db")
    oanda = OandaClient(config)
    risk = RiskManager(config, oanda, db)
    executor = Executor(config, oanda, db)

    if not is_market_open():
        logger.info("Market closed. Skipping cycle.")
        return

    # Run News Stream
    streams_cfg = config.get("streams", {})
    if streams_cfg.get("news_stream", {}).get("enabled", False):
        from backend.streams.news_stream import NewsStream
        news_stream = NewsStream(
            config=config, db=db, oanda=oanda,
            risk=risk, executor=executor,
        )
        await news_stream.tick()

    # Run Strategy Stream
    if streams_cfg.get("strategy_stream", {}).get("enabled", False):
        from backend.streams.strategy_stream import StrategyStream
        strategy_stream = StrategyStream(
            config=config, db=db, oanda=oanda,
            risk=risk, executor=executor,
        )
        await strategy_stream.tick()

    # Run all active Hybrid Streams
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
    if should_generate_review(config):
        from backend.reviews.generator import ReviewGenerator
        ReviewGenerator(db, config).generate(trigger="scheduled")

    logger.info("Trading cycle complete.")


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


def main():
    parser = argparse.ArgumentParser(description="Forex Sentinel")
    parser.add_argument(
        "--mode",
        choices=["tick", "backtest", "review"],
        default="tick",
        help="tick: run one trading cycle. backtest: run backtests. review: generate Cowork review.",
    )
    parser.add_argument("--strategy", help="Strategy name for backtest mode")
    parser.add_argument("--instrument", help="Instrument for backtest mode")
    parser.add_argument("--period", help="Period for review, e.g. '7d' or '30d'")
    args = parser.parse_args()

    # Ensure data directories exist
    Path("data").mkdir(exist_ok=True)
    Path("logs").mkdir(exist_ok=True)

    if args.mode == "tick":
        asyncio.run(run_tick())
    elif args.mode == "backtest":
        from backend.backtest.runner import run_backtest
        run_backtest(args.strategy, args.instrument)
    elif args.mode == "review":
        from backend.reviews.generator import ReviewGenerator
        ReviewGenerator.from_cli(args.period)


if __name__ == "__main__":
    main()
