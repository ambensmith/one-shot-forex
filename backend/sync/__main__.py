"""Position sync — lightweight 5-minute reconciliation with Capital.com.

Does NOT generate signals or place trades. Only:
1. Reconciles positions (detects broker-closed trades)
2. Records position snapshots (unrealized P&L)
3. Captures rich context for newly closed trades
4. Re-exports dashboard JSON
"""

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
        logging.FileHandler(Path("logs/sync.log"), mode="a"),
    ],
)
logger = logging.getLogger("forex_sentinel.sync")


def run_sync():
    """Execute one position sync cycle."""
    from backend.core.config import load_config
    from backend.core.database import Database
    from backend.data.capitalcom_client import CapitalComClient
    from backend.execution.executor import Executor
    from backend.sync.context_capture import capture_position_snapshot, capture_close_context

    db = Database("data/sentinel.db")
    config = load_config(db=db)
    broker = CapitalComClient(config)

    if not broker.is_connected:
        logger.warning("Sync skipped — broker not connected")
        db.close()
        return

    executor = Executor(config, broker, db)

    logger.info("Position sync starting")

    # Reconcile all streams (no stream filter = check everything)
    newly_closed = executor.reconcile_positions(stream_id=None)

    # Also pull broker history so trades that opened and closed between ticks
    # don't vanish, and any PnL mismatches (e.g. from the old quote-currency
    # bug) get corrected using the broker's realized EUR numbers.
    from datetime import timedelta
    history_since = (datetime.now(timezone.utc) - timedelta(hours=72)).isoformat()
    try:
        bf = executor.backfill_closed_history(history_since, repair=True)
        if bf.get("imported") or bf.get("repaired"):
            logger.info(
                f"History backfill: {len(bf.get('imported', []))} imported, "
                f"{len(bf.get('repaired', []))} PnL-repaired"
            )
    except Exception as e:
        logger.warning(f"History backfill failed: {e}")

    # Capture rich context for newly closed trades
    for trade_id in newly_closed:
        try:
            trade = db.execute("SELECT * FROM trades WHERE id = ?", (trade_id,)).fetchone()
            if trade:
                trade_dict = dict(trade)
                context = capture_close_context(trade_dict, broker, db)
                if context:
                    db.insert_trade_event(trade_id, "close_context", context)
                    logger.info(f"Captured close context for trade {trade_id}")
        except Exception as e:
            logger.warning(f"Failed to capture close context for trade {trade_id}: {e}")

    # Record position snapshots for all open trades
    open_trades = db.get_open_trades()
    snapshot_count = 0
    for trade in open_trades:
        try:
            snapshot = capture_position_snapshot(trade, broker)
            if snapshot:
                db.insert_trade_event(trade["id"], "snapshot", snapshot)
                snapshot_count += 1
        except Exception as e:
            logger.warning(f"Failed to snapshot trade {trade['id']}: {e}")

    # Log untracked positions (broker positions not in our DB)
    untracked = executor.get_untracked_positions()
    if untracked:
        logger.warning(f"Found {len(untracked)} untracked broker positions")

    # Record account-level equity from live broker balance
    try:
        summary = broker.get_account_summary()
        account_equity = summary.get("balance", 0) + summary.get("unrealizedPL", 0)
        total_open = len(open_trades)
        db.insert_equity_snapshot("account", round(account_equity, 2), total_open)
        logger.info(f"Account equity recorded: €{account_equity:.2f}")
    except Exception as e:
        logger.warning(f"Failed to record account equity: {e}")

    logger.info(
        f"Sync complete: {len(newly_closed)} closed, "
        f"{snapshot_count} snapshots, {len(untracked)} untracked"
    )

    # Re-export dashboard JSON
    try:
        from backend.dashboard.json_exporter import (
            export_dashboard_summary,
            export_trades,
            export_equity,
            export_signals,
            export_config,
            export_review,
            export_hybrids,
            export_run_reviews,
            export_models,
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
        logger.info("Dashboard JSON re-exported")
    except Exception as e:
        logger.warning(f"JSON export failed: {e}")

    db.close()


if __name__ == "__main__":
    run_sync()
