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


_force_market_open = False


def is_market_open() -> bool:
    """Returns True if forex market is currently open.
    Open: Sunday 22:00 UTC through Friday 22:00 UTC."""
    if _force_market_open:
        return True
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
    from backend.data.capitalcom_client import CapitalComClient
    return CapitalComClient(config)


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

    run_start = datetime.now(timezone.utc)
    run_id = run_start.strftime("%Y-%m-%dT%H:%M:%SZ")

    db = Database("data/sentinel.db")
    config = load_config(db=db)

    # Check if paused via config override
    if config.get("scheduler", {}).get("paused", False):
        logger.info("Scheduler paused via config. Skipping cycle.")
        db.insert_run_log(
            run_id=run_id, started_at=run_start.isoformat(),
            completed_at=datetime.now(timezone.utc).isoformat(),
            market_open=1, skipped_reason="paused", status="skipped",
            review_md="# Run skipped — scheduler paused",
        )
        return

    market_open = is_market_open()
    if not market_open:
        logger.info("Market closed. Skipping cycle.")
        db.insert_run_log(
            run_id=run_id, started_at=run_start.isoformat(),
            completed_at=datetime.now(timezone.utc).isoformat(),
            market_open=0, skipped_reason="market_closed", status="skipped",
            review_md="# Run skipped — market closed",
        )
        return

    broker = create_data_provider(config)
    risk = RiskManager(config, broker, db)
    executor = Executor(config, broker, db)

    # Snapshot open trades before the tick (these are carried-over)
    pre_open_trades = {t["id"] for t in db.get_open_trades()}

    streams_cfg = config.get("streams", {})
    streams_run = []

    # Run News Stream
    if stream_filter in ("all", "news"):
        if streams_cfg.get("news_stream", {}).get("enabled", False):
            from backend.streams.news_stream import NewsStream
            news_stream = NewsStream(
                config=config, db=db, broker=broker,
                risk=risk, executor=executor,
            )
            await news_stream.tick()
            streams_run.append("news")

    # Run Strategy Stream
    if stream_filter in ("all", "strategy"):
        if streams_cfg.get("strategy_stream", {}).get("enabled", False):
            from backend.streams.strategy_stream import StrategyStream
            strategy_stream = StrategyStream(
                config=config, db=db, broker=broker,
                risk=risk, executor=executor,
            )
            await strategy_stream.tick()
            streams_run.append("strategy")

    # Run all active Hybrid Streams
    if stream_filter in ("all", "hybrid"):
        from backend.streams.hybrid_stream import HybridStream
        for hybrid_config in db.get_active_hybrids():
            hybrid = HybridStream(
                hybrid_config=hybrid_config,
                config=config, db=db, broker=broker,
                risk=risk, executor=executor,
            )
            await hybrid.tick()
            streams_run.append(f"hybrid:{hybrid_config['name']}")

    # Record equity snapshots
    _record_all_equity(db, broker, config)

    # Generate review if due
    if stream_filter == "all" and should_generate_review(config):
        from backend.reviews.generator import ReviewGenerator
        ReviewGenerator(db, config).generate(trigger="scheduled")

    # ── Run context tracking ──────────────────────────────
    # Identify signals and trades created during this tick
    signals_this_run = db.get_signals(since=run_start, limit=500)
    trades_this_run = db.get_trades(since=run_start, limit=500)

    signal_ids = [s["id"] for s in signals_this_run]
    rejected_ids = [s["id"] for s in signals_this_run if s.get("rejection_reason")]

    post_open_trades = {t["id"] for t in db.get_open_trades()}
    new_trade_ids = [t["id"] for t in trades_this_run if t["id"] not in pre_open_trades]
    closed_trade_ids = [tid for tid in pre_open_trades if tid not in post_open_trades]
    carried_trade_ids = list(post_open_trades & pre_open_trades)

    run_context = {
        "run_id": run_id,
        "started_at": run_start.isoformat(),
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "market_open": True,
        "config_snapshot": config,
        "streams_run": streams_run,
        "signals_generated": signal_ids,
        "trades_opened": new_trade_ids,
        "trades_closed": closed_trade_ids,
        "trades_carried": carried_trade_ids,
        "rejected_signals": rejected_ids,
        "skipped_reason": None,
    }

    # Generate per-run review
    from backend.reviews.run_review import RunReviewGenerator
    review_md = RunReviewGenerator(db, config).generate(run_context)

    # Store run log
    db.insert_run_log(
        run_id=run_id,
        started_at=run_context["started_at"],
        completed_at=run_context["completed_at"],
        market_open=1,
        config_snapshot=config,
        streams_run=streams_run,
        signals_generated=signal_ids,
        trades_opened=new_trade_ids,
        trades_closed=closed_trade_ids,
        trades_carried=carried_trade_ids,
        rejected_signals=rejected_ids,
        review_md=review_md,
        status="completed",
    )

    # Export all dashboard JSON data
    from backend.dashboard.json_exporter import (
        export_dashboard_summary, export_trades, export_equity,
        export_signals, export_models, export_config, export_review,
        export_hybrids, export_run_reviews, OUTPUT_DIR,
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

    logger.info(f"Trading cycle complete (stream={stream_filter}).")


def _record_all_equity(db, broker, config):
    """Record equity snapshots for all streams based on actual trade P&L."""
    streams_cfg = config.get("streams", {})

    stream_list = [
        ("news", streams_cfg.get("news_stream", {}).get("capital_allocation", 100)),
        ("strategy", streams_cfg.get("strategy_stream", {}).get("capital_allocation", 100)),
    ]
    for hybrid in db.get_active_hybrids():
        stream_list.append((f"hybrid:{hybrid['name']}", hybrid.get("capital_allocation", 100)))

    for stream_id, capital in stream_list:
        trades = db.get_trades(stream_id, limit=10000)
        realized_pnl = sum(t["pnl"] for t in trades if t.get("pnl") is not None)
        equity = capital + realized_pnl
        open_count = db.count_open_positions(stream_id)
        db.insert_equity_snapshot(stream_id, round(equity, 2), open_count)

    # Account-level equity from live broker balance
    try:
        if broker and broker.is_connected:
            summary = broker.get_account_summary()
            account_equity = summary.get("balance", 0) + summary.get("unrealizedPL", 0)
            total_open = sum(db.count_open_positions(s) for s, _ in stream_list)
            db.insert_equity_snapshot("account", round(account_equity, 2), total_open)
    except Exception as e:
        logging.getLogger(__name__).warning(f"Failed to record account equity: {e}")


def run_close_all():
    """Close all open positions on Capital.com.

    Fetches every live position from the broker and closes them one by one.
    Returns the number of positions successfully closed.
    """
    from backend.core.config import load_config
    from backend.core.database import Database

    db = Database("data/sentinel.db")
    config = load_config(db=db)
    broker = create_data_provider(config)

    if not broker.is_connected:
        logger.error("Cannot close positions: broker not connected. Set CAPITALCOM_* env vars.")
        db.close()
        return 0

    try:
        positions = broker.get_open_trades()
    except Exception as e:
        logger.error(f"Failed to fetch broker positions: {e}")
        db.close()
        return 0

    logger.info(f"Found {len(positions)} open position(s) on broker")

    closed = 0
    failed = 0
    for pos in positions:
        deal_id = pos.get("id", "")
        instrument = pos.get("instrument", "?")
        direction = pos.get("direction", "?")
        logger.info(f"Closing {instrument} {direction} deal_id={deal_id} ...")
        result = broker.close_trade(deal_id)
        if result.get("status") == "error":
            logger.error(f"  Failed to close {deal_id}: {result.get('error')}")
            failed += 1
        else:
            logger.info(f"  Closed {deal_id} OK")
            closed += 1

    db.close()
    logger.info(f"Close-all complete: {closed} closed, {failed} failed out of {len(positions)}")
    return closed


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
    db.execute("DELETE FROM run_logs")
    db.commit()

    # Re-export dashboard data (now empty)
    from backend.dashboard.json_exporter import export_all
    export_all(db_path="data/sentinel.db")

    db.close()
    logger.info("Database reset complete.")


def run_close_all_and_reset():
    """Close all broker positions then reset all local data."""
    logger.info("=== Step 1: Closing all broker positions ===")
    run_close_all()
    logger.info("=== Step 2: Resetting local database ===")
    run_reset()
    logger.info("=== Clean slate complete ===")


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


def run_save_config(config_json: str):
    """Save config overrides from a JSON string."""
    from backend.core.config import save_config_overrides, get_effective_config

    overrides = json.loads(config_json)
    save_config_overrides(overrides)

    # Re-export all dashboard data so config-dependent views update
    from backend.dashboard.json_exporter import export_all
    export_all()

    logger.info(f"Config overrides saved: {list(overrides.keys())}")


def run_get_config():
    """Export effective config and all dashboard data to JSON for frontend."""
    from backend.dashboard.json_exporter import export_all
    export_all()
    logger.info("All dashboard data exported.")


def run_fix_phantoms():
    """Mark phantom trades as failed.

    Phantom trades have status='closed_reconciled' but NULL exit_price and pnl,
    meaning they were never actually executed on the broker.
    """
    from backend.core.database import Database

    db = Database("data/sentinel.db")

    rows = db.execute(
        "SELECT id, instrument, direction, stream FROM trades "
        "WHERE status = 'closed_reconciled' AND exit_price IS NULL AND pnl IS NULL"
    ).fetchall()

    count = 0
    for row in rows:
        trade = dict(row)
        db.update_trade(
            trade["id"],
            status="failed",
            pnl=0.0,
            pnl_pips=0.0,
        )
        count += 1
        logger.info(
            f"Fixed phantom trade {trade['id']}: {trade['stream']} "
            f"{trade['instrument']} {trade['direction']} -> status=failed"
        )

    db.close()
    logger.info(f"Fixed {count} phantom trade(s).")


def run_reconcile_trades():
    """One-shot reconciliation: find open trades with no matching broker position.

    Connects to the broker and reconciles all open trades across all streams
    using broker_deal_id matching. Useful for cleaning up stuck/phantom trades.
    """
    from backend.core.database import Database
    from backend.core.config import load_config
    from backend.execution.executor import Executor

    db = Database("data/sentinel.db")
    config = load_config(db=db)
    broker = create_data_provider(config)
    executor = Executor(config, broker, db)

    if not broker.is_connected:
        logger.error("Cannot reconcile: broker not connected. Set CAPITALCOM_* env vars.")
        db.close()
        return

    # Show current open trades before reconciliation
    open_trades = db.get_open_trades()
    logger.info(f"Open trades before reconciliation: {len(open_trades)}")
    for t in open_trades:
        logger.info(
            f"  Trade {t['id']}: {t['stream']} {t['instrument']} {t['direction']} "
            f"deal_id={t.get('broker_deal_id', '')}"
        )

    # Run reconciliation across all streams (stream_id=None)
    executor.reconcile_positions(stream_id=None)

    # Show remaining open trades
    remaining = db.get_open_trades()
    logger.info(f"Open trades after reconciliation: {len(remaining)}")

    # Re-export dashboard data
    from backend.dashboard.json_exporter import export_all
    export_all(db_path="data/sentinel.db")

    db.close()
    logger.info("One-shot reconciliation complete.")


def run_sync_broker():
    """Import untracked broker positions into the local database.

    Fetches all open positions from Capital.com and creates DB records
    for any that don't already have a matching broker_deal_id.
    """
    from backend.core.database import Database
    from backend.core.config import load_config

    db = Database("data/sentinel.db")
    config = load_config(db=db)
    broker = create_data_provider(config)

    if not broker.is_connected:
        logger.error("Cannot sync: broker not connected. Set CAPITALCOM_* env vars.")
        db.close()
        return

    try:
        broker_positions = broker.get_open_trades()
    except Exception as e:
        logger.error(f"Failed to fetch broker positions: {e}")
        db.close()
        return

    logger.info(f"Broker has {len(broker_positions)} open positions")

    # Find which positions are already tracked
    existing_deal_ids = set()
    for row in db.execute("SELECT broker_deal_id FROM trades WHERE broker_deal_id IS NOT NULL").fetchall():
        existing_deal_ids.add(dict(row)["broker_deal_id"])

    created = 0
    for pos in broker_positions:
        deal_id = pos.get("id", "")
        if deal_id in existing_deal_ids:
            logger.info(f"  Already tracked: {deal_id} ({pos['instrument']} {pos['direction']})")
            continue

        entry_price = pos.get("entry_price") or 0
        stop_loss = pos.get("stop_loss") or 0
        take_profit = pos.get("take_profit") or 0
        size = float(pos.get("currentUnits", 0))

        # Assign to a stream — untracked positions go to "news" as default
        stream = "news"

        trade_id = db.insert_trade(
            stream=stream,
            instrument=pos["instrument"],
            direction=pos["direction"],
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            position_size=size,
            signal_ids=[],
            broker_deal_id=deal_id,
        )
        created += 1
        logger.info(
            f"  Created trade {trade_id}: {pos['instrument']} {pos['direction']} "
            f"size={size} entry={entry_price} deal_id={deal_id}"
        )

    # Re-export dashboard data
    from backend.dashboard.json_exporter import export_all
    export_all(db_path="data/sentinel.db")

    db.close()
    logger.info(f"Sync complete: {created} new trade(s) imported from broker.")


def run_backfill_pnl():
    """Backfill null P&L on closed trades using SL as conservative exit estimate.

    Finds all closed trades with null pnl/exit_price and fills them in
    using the stop-loss price as a worst-case exit estimate.
    """
    from backend.core.database import Database
    from backend.execution.executor import Executor

    db = Database("data/sentinel.db")

    rows = db.execute(
        "SELECT * FROM trades "
        "WHERE status IN ('closed_reconciled', 'closed_sl', 'closed_tp') "
        "AND pnl IS NULL"
    ).fetchall()

    count = 0
    for row in rows:
        trade = dict(row)
        # Use existing exit_price if available, else SL, else entry
        exit_price = trade.get("exit_price") or trade.get("stop_loss") or trade["entry_price"]
        pnl_info = Executor.calc_pnl(trade, exit_price)
        db.update_trade(
            trade["id"],
            exit_price=pnl_info["exit_price"],
            pnl=pnl_info["pnl"],
            pnl_pips=pnl_info["pnl_pips"],
        )
        count += 1
        logger.info(
            f"Backfilled trade {trade['id']}: {trade['stream']} "
            f"{trade['instrument']} {trade['direction']} -> "
            f"exit={pnl_info['exit_price']}, pnl={pnl_info['pnl']}"
        )

    db.close()
    logger.info(f"Backfilled {count} trade(s) with estimated P&L.")


def main():
    parser = argparse.ArgumentParser(description="Forex Sentinel")
    parser.add_argument(
        "--mode",
        choices=["tick", "backtest", "review", "reset", "close-all", "close-all-and-reset", "save-hybrid", "save-config", "get-config", "fix-phantoms", "reconcile-trades", "sync-broker", "backfill-pnl"],
        default="tick",
        help="tick: run trading cycle. reset: clear all data. review: generate Cowork review. save-hybrid: save a hybrid config. save-config: save config overrides. get-config: export effective config.",
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
    parser.add_argument("--config-json", help="Config overrides as JSON string (save-config mode)")
    args = parser.parse_args()

    if args.mode == "tick":
        asyncio.run(run_tick(
            stream_filter=args.stream,
            force_market_open=args.force_market_open,
        ))
    elif args.mode == "reset":
        run_reset()
    elif args.mode == "close-all":
        run_close_all()
    elif args.mode == "close-all-and-reset":
        run_close_all_and_reset()
    elif args.mode == "save-hybrid":
        if not args.hybrid_json:
            parser.error("--hybrid-json is required for save-hybrid mode")
        run_save_hybrid(args.hybrid_json)
    elif args.mode == "save-config":
        if not args.config_json:
            parser.error("--config-json is required for save-config mode")
        run_save_config(args.config_json)
    elif args.mode == "get-config":
        run_get_config()
    elif args.mode == "fix-phantoms":
        run_fix_phantoms()
    elif args.mode == "reconcile-trades":
        run_reconcile_trades()
    elif args.mode == "sync-broker":
        run_sync_broker()
    elif args.mode == "backfill-pnl":
        run_backfill_pnl()
    elif args.mode == "backtest":
        from backend.backtest.runner import run_backtest
        run_backtest(args.strategy, args.instrument)
    elif args.mode == "review":
        from backend.reviews.generator import ReviewGenerator
        ReviewGenerator.from_cli(args.period)


if __name__ == "__main__":
    main()
