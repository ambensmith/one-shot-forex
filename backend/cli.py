"""Forex Sentinel CLI — pipeline entry point.

Usage:
    python -m backend <command>

Commands:
    init-db      Initialize database schema and seed prompts
    ingest       Fetch news + prices, store in DB
    relevance    Run Stage 2a: LLM relevance assessment
    signals      Run Stage 2b: LLM signal generation
    challenge    Run Stage 2c: counter-argument challenge
    strategies   Run all strategies on price data
    bias         Update directional bias tracker
    risk         Run risk checks on pending signals
    execute      Execute approved trades
    tick         Run full pipeline (all stages in order)
    reconcile    Sync with broker positions
"""

import argparse
import json
import logging
import sys
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


# ── Commands ────────────────────────────────────────────────


def cmd_init_db(fresh: bool = False):
    """Initialize database schema and seed prompts."""
    from backend.core.database import Database

    db = Database("data/sentinel.db")
    db.init_db(fresh=fresh)

    # Verification
    counts = db.table_counts()
    prompts = db.get_all_prompts()
    db.close()

    logger.info(f"Database initialized (fresh={fresh})")
    logger.info(f"Tables: {len(counts)}")
    for name, count in sorted(counts.items()):
        logger.info(f"  {name}: {count} rows")
    logger.info(f"Prompts seeded: {len(prompts)}")
    for p in prompts:
        logger.info(f"  {p['name']} ({p['version']}) active={p['is_active']}")

    print(json.dumps({
        "status": "ok",
        "command": "init-db",
        "fresh": fresh,
        "tables": len(counts),
        "prompts_seeded": len(prompts),
    }))


def cmd_prompts():
    """Show every prompt in the DB and which one is in use per stage."""
    from backend.core.database import Database, STAGE_TARGETS

    db = Database("data/sentinel.db")
    try:
        rows = db.get_all_prompts()
        by_stage: dict[str, list[dict]] = {}
        for r in rows:
            stage = r["name"].rsplit("_v", 1)[0] if "_v" in r["name"] else r["name"]
            by_stage.setdefault(stage, []).append(r)

        out = {"stages": {}}
        for stage, target in STAGE_TARGETS.items():
            stage_rows = []
            in_use_name = None
            for r in by_stage.get(stage, []):
                stage_rows.append({
                    "name": r["name"],
                    "version": r["version"],
                    "in_use": bool(r.get("in_use", 0)),
                    "is_active": bool(r.get("is_active", 0)),
                    "updated_at": r.get("updated_at"),
                    "preview": (r.get("template") or "")[:80],
                })
                if r.get("in_use"):
                    in_use_name = r["name"]
            out["stages"][stage] = {
                "target": target,
                "in_use": in_use_name,
                "matches_target": in_use_name == target,
                "prompts": stage_rows,
            }

        # Pretty log for humans
        logger.info("Prompt configuration:")
        for stage, info in out["stages"].items():
            marker = "OK" if info["matches_target"] else "MISMATCH"
            logger.info(f"  [{marker}] {stage}: in_use={info['in_use']} target={info['target']}")
            for p in info["prompts"]:
                flag = "*" if p["in_use"] else " "
                logger.info(f"      {flag} {p['name']} (active={p['is_active']}) — {p['preview']}...")

        print(json.dumps({"status": "ok", "command": "prompts", **out}, indent=2))
    finally:
        db.close()


def cmd_ingest():
    """Fetch news + prices from all configured sources, store in DB."""
    import asyncio
    from backend.core.config import load_config
    from backend.core.database import Database
    from backend.data.news_ingestor import ingest_pipeline
    from backend.data.price_ingestor import ingest_prices

    config = load_config()
    db = Database("data/sentinel.db")

    try:
        # News ingestion
        news_result = asyncio.run(ingest_pipeline(config, db))
        logger.info(f"News ingest complete: {news_result}")

        # Price ingestion
        price_result = ingest_prices(config, db)
        logger.info(f"Price ingest complete: {price_result}")

        print(json.dumps({
            "status": "ok",
            "command": "ingest",
            "news": news_result,
            "prices": price_result,
        }))
    finally:
        db.close()


def cmd_relevance():
    """Run Stage 2a: LLM relevance assessment on recent headlines."""
    from backend.core.config import load_config
    from backend.core.database import Database
    from backend.signals.relevance import run_relevance

    config = load_config()
    db = Database("data/sentinel.db")

    try:
        result = run_relevance(db, config)
        logger.info(f"Relevance assessment complete: {result}")

        # Show sample assessments for verification
        assessments = db.get_relevance_assessments(limit=10)
        if assessments:
            logger.info(f"Sample assessments (latest {len(assessments)}):")
            for a in assessments:
                reasoning = a.get('relevance_reasoning') or 'N/A'
                logger.info(f"  {a['instrument']}: {reasoning[:80]}...")

        print(json.dumps({
            "status": "ok",
            "command": "relevance",
            **result,
        }))
    finally:
        db.close()


def cmd_signals():
    """Run Stage 2b: LLM signal generation for instruments with relevant news."""
    from backend.core.config import load_config
    from backend.core.database import Database
    from backend.signals.signal_generator import run_signals

    config = load_config()
    db = Database("data/sentinel.db")

    try:
        result = run_signals(db, config)
        logger.info(f"Signal generation complete: {result}")

        # Show sample signals for verification
        signals = db.get_signals(status="pending", limit=10)
        llm_signals = [s for s in signals if s.get("source") == "llm"]
        if llm_signals:
            logger.info(f"Sample LLM signals (latest {len(llm_signals)}):")
            for s in llm_signals:
                reasoning = s.get("reasoning") or "N/A"
                logger.info(
                    f"  {s['instrument']} | {s['direction']} | "
                    f"conf={s['confidence']:.2f} | {reasoning[:80]}..."
                )

        print(json.dumps({
            "status": "ok",
            "command": "signals",
            **result,
        }))
    finally:
        db.close()


def cmd_challenge():
    """Run Stage 2c: counter-argument challenge on pending LLM signals."""
    from backend.core.config import load_config
    from backend.core.database import Database
    from backend.signals.challenge import run_challenge

    config = load_config()
    db = Database("data/sentinel.db")

    try:
        result = run_challenge(db, config)
        logger.info(f"Challenge complete: {result}")

        print(json.dumps({
            "status": "ok",
            "command": "challenge",
            **result,
        }))
    finally:
        db.close()


def cmd_strategies():
    """Run all enabled strategies on stored candle data, write signals to DB."""
    import pandas as pd
    from backend.core.config import load_config
    from backend.core.database import Database
    from backend.core.models import Signal
    from backend.strategies.registry import get_strategy

    config = load_config()
    db = Database("data/sentinel.db")
    stream_cfg = config.get("streams", {}).get("strategy_stream", {})
    strategies_cfg = stream_cfg.get("strategies", [])
    instruments = stream_cfg.get("instruments", [])

    results = {"signals_generated": 0, "errors": [], "by_strategy": {}}

    try:
        for strat_cfg in strategies_cfg:
            if not strat_cfg.get("enabled", True):
                continue

            strat_name = strat_cfg["name"]
            try:
                strategy = get_strategy(strat_name, strat_cfg.get("params"))
            except ValueError as e:
                logger.warning(str(e))
                results["errors"].append(str(e))
                continue

            strat_signals = 0
            for instrument in instruments:
                try:
                    candle_rows = db.get_candles(instrument, limit=200)
                    if not candle_rows:
                        logger.info(f"No candles for {instrument}, skipping {strat_name}")
                        continue

                    df = _candles_to_dataframe(candle_rows)
                    if len(df) < 20:
                        logger.info(f"Insufficient candles for {instrument} ({len(df)}), skipping")
                        continue

                    tech_signal = strategy.analyze(df, instrument)
                    if tech_signal.direction == "neutral" or tech_signal.confidence <= 0.0:
                        continue

                    signal = _tech_to_signal(tech_signal, strategy)
                    db.insert_signal(signal)
                    strat_signals += 1
                    logger.info(
                        f"{strat_name} | {instrument} | {tech_signal.direction} | "
                        f"conf={tech_signal.confidence:.3f}"
                    )
                except Exception as e:
                    msg = f"Error running {strat_name} on {instrument}: {e}"
                    logger.error(msg)
                    results["errors"].append(msg)

            results["by_strategy"][strat_name] = strat_signals
            results["signals_generated"] += strat_signals

        logger.info(f"Strategy engine complete: {results['signals_generated']} signals")
        print(json.dumps({
            "status": "ok",
            "command": "strategies",
            **results,
        }))
    finally:
        db.close()


def _candles_to_dataframe(candle_rows: list[dict]):
    """Convert DB candle rows to the DataFrame format strategies expect."""
    import pandas as pd
    df = pd.DataFrame(candle_rows)
    df = df.rename(columns={
        "open": "Open", "high": "High", "low": "Low",
        "close": "Close", "volume": "Volume",
    })
    df.index = pd.DatetimeIndex(pd.to_datetime(df["timestamp"], utc=True, format="mixed"))
    return df[["Open", "High", "Low", "Close", "Volume"]]


def _tech_to_signal(tech_signal, strategy):
    """Convert a TechnicalSignal to a Signal model for DB storage."""
    from backend.core.models import Signal

    reasoning = strategy.description
    if "reason" in tech_signal.metadata:
        reasoning += f". {tech_signal.metadata['reason']}"
    else:
        indicators = {k: v for k, v in tech_signal.metadata.items() if k != "reason"}
        if indicators:
            parts = [f"{k}={v}" for k, v in indicators.items()]
            reasoning += f". Indicators: {', '.join(parts)}"

    metadata = {
        "parameters": strategy.get_parameters(),
        "indicators": tech_signal.metadata,
    }
    if tech_signal.entry_price is not None:
        metadata["entry_price"] = tech_signal.entry_price
    if tech_signal.stop_loss is not None:
        metadata["suggested_stop"] = tech_signal.stop_loss
    if tech_signal.take_profit is not None:
        metadata["suggested_tp"] = tech_signal.take_profit

    return Signal(
        source=f"strategy:{tech_signal.strategy_name}",
        instrument=tech_signal.instrument,
        direction=tech_signal.direction,
        confidence=tech_signal.confidence,
        reasoning=reasoning,
        metadata=metadata,
        status="pending",
    )


def cmd_bias():
    """Run Stage 3: update directional bias tracker and check pending signals."""
    from backend.core.config import load_config
    from backend.core.database import Database
    from backend.signals.bias import run_bias

    config = load_config()
    db = Database("data/sentinel.db")

    try:
        result = run_bias(db, config)
        logger.info(f"Bias tracker complete: {result}")

        # Show current bias state for verification
        bias_states = db.get_bias_state()
        if bias_states:
            logger.info(f"Current bias state ({len(bias_states)} instruments):")
            for bs in bias_states:
                logger.info(
                    f"  {bs['instrument']}: {bs.get('current_bias', 'N/A')} "
                    f"(strength={bs.get('bias_strength', 0):.2f})"
                )

        print(json.dumps({
            "status": "ok",
            "command": "bias",
            **result,
        }))
    finally:
        db.close()


def cmd_risk():
    """Run Stage 4: risk checks on bias-approved signals."""
    from backend.core.config import load_config
    from backend.core.database import Database
    from backend.main import create_data_provider
    from backend.risk.risk_manager import RiskManager

    config = load_config()
    db = Database("data/sentinel.db")
    broker = create_data_provider(config)
    risk = RiskManager(config, broker, db)

    try:
        pending = db.get_signals(status="pending", limit=200)
        to_check = []
        for s in pending:
            bc = s.get("bias_check")
            if isinstance(bc, str):
                bc = json.loads(bc)
            rc = s.get("risk_check")
            if isinstance(rc, str):
                rc = json.loads(rc)
            if not (bc and bc.get("approved_by_bias") and not rc):
                continue
            if s["direction"] not in ("long", "short"):
                # Defensive: signal generator already rejects neutrals at insert.
                db.update_signal(s["id"], status="rejected",
                                 rejection_reason=f"Invalid direction: {s['direction']}",
                                 risk_check={
                                     "approved": False,
                                     "rejection_reason": f"Invalid direction: {s['direction']}",
                                 })
                continue
            # Every LLM signal must have been counter-argued before risk.
            if s.get("source") == "llm" and not s.get("challenge_output"):
                db.update_signal(s["id"], status="rejected",
                                 rejection_reason="LLM signal not challenged",
                                 risk_check={
                                     "approved": False,
                                     "rejection_reason": "LLM signal not challenged",
                                 })
                continue
            to_check.append(s)

        # Track batch-level state so risk limits apply across the batch
        from backend.risk.risk_manager import CORRELATION_GROUPS
        risk_cfg = config.get("risk", {})
        max_open_per_stream = risk_cfg.get("max_open_positions_per_stream", 5)
        max_correlated = risk_cfg.get("max_correlated_positions", 2)

        # Pre-load existing open positions into batch counters
        existing_open = db.get_open_trades_by_source()
        batch_stream_counts = {}  # stream_group -> count
        batch_instruments = set()  # instruments with open/approved positions
        for t in existing_open:
            sg = "strategy" if (t.get("source") or "").startswith("strategy:") else (t.get("source") or "unknown")
            batch_stream_counts[sg] = batch_stream_counts.get(sg, 0) + 1
            batch_instruments.add(t["instrument"])

        approved = 0
        rejected = 0
        for s in to_check:
            source = s["source"]
            instrument = s["instrument"]
            direction = s["direction"]
            stream_group = "strategy" if source.startswith("strategy:") else source

            # Batch-level max positions check
            current_count = batch_stream_counts.get(stream_group, 0)
            if current_count >= max_open_per_stream:
                risk_check = {
                    "approved": False,
                    "position_size": 0,
                    "rejection_reason": f"Max open positions ({max_open_per_stream}) for {stream_group}",
                    "entry_price": None,
                    "stop_loss": None,
                    "take_profit": None,
                }
                db.update_signal(s["id"], risk_check=risk_check, status="rejected")
                rejected += 1
                logger.info(f"Risk REJECTED {instrument} {direction}: max positions for {stream_group}")
                continue

            # Batch-level correlation check
            corr_rejected = False
            for group in CORRELATION_GROUPS:
                if instrument in group:
                    correlated_open = len(batch_instruments & group)
                    if correlated_open >= max_correlated:
                        risk_check = {
                            "approved": False,
                            "position_size": 0,
                            "rejection_reason": f"Max correlated positions ({max_correlated}) for group",
                            "entry_price": None,
                            "stop_loss": None,
                            "take_profit": None,
                        }
                        db.update_signal(s["id"], risk_check=risk_check, status="rejected")
                        rejected += 1
                        logger.info(f"Risk REJECTED {instrument} {direction}: correlated group limit")
                        corr_rejected = True
                        break
            if corr_rejected:
                continue

            # Always use live broker price as entry — signal metadata prices may be stale
            try:
                price_data = broker.get_current_price(instrument)
                entry_price = price_data["mid"]
            except Exception as e:
                logger.warning(f"Cannot get price for {instrument}: {e}")
                continue

            # Calculate stop loss using candle data
            candle_rows = db.get_candles(instrument, limit=200)
            df = None
            if candle_rows:
                df = _candles_to_dataframe(candle_rows)
            stop_loss = risk.calculate_stop_loss(instrument, entry_price, direction, df)

            # Run remaining risk checks (market hours, daily loss, position sizing)
            result = risk.check_trade(source, instrument, direction, entry_price, stop_loss)

            # Calculate take profit for approved trades
            take_profit = None
            if result.approved:
                take_profit = risk.calculate_take_profit(entry_price, stop_loss, direction)

            risk_check = {
                "approved": result.approved,
                "position_size": result.position_size,
                "rejection_reason": result.rejection_reason,
                "entry_price": entry_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
            }

            update_kwargs = {"risk_check": risk_check}
            if not result.approved:
                update_kwargs["status"] = "rejected"
                rejected += 1
                logger.info(
                    f"Risk REJECTED {instrument} {direction}: {result.rejection_reason}"
                )
            else:
                # Update batch counters for next iteration
                batch_stream_counts[stream_group] = current_count + 1
                batch_instruments.add(instrument)
                approved += 1
                logger.info(
                    f"Risk APPROVED {instrument} {direction}: "
                    f"size={result.position_size} SL={stop_loss:.5f} TP={take_profit:.5f}"
                )

            db.update_signal(s["id"], **update_kwargs)

        logger.info(f"Risk check complete: {approved} approved, {rejected} rejected")
        print(json.dumps({
            "status": "ok",
            "command": "risk",
            "signals_checked": len(to_check),
            "approved": approved,
            "rejected": rejected,
        }))
    finally:
        db.close()


def cmd_execute():
    """Run Stage 5: execute risk-approved signals on broker."""
    from backend.core.config import load_config
    from backend.core.database import Database
    from backend.core.models import TradeRecord
    from backend.main import create_data_provider
    from backend.execution.executor import Executor

    config = load_config()
    db = Database("data/sentinel.db")
    broker = create_data_provider(config)
    executor = Executor(config, broker, db)

    try:
        pending = db.get_signals(status="pending", limit=200)
        to_execute = []
        for s in pending:
            rc = s.get("risk_check")
            if isinstance(rc, str):
                rc = json.loads(rc)
            if rc and rc.get("approved"):
                to_execute.append((s, rc))

        executed = 0
        failed = 0
        for s, rc in to_execute:
            trade_id = executor.execute_trade(
                stream_id=s["source"],
                instrument=s["instrument"],
                direction=s["direction"],
                entry_price=rc["entry_price"],
                stop_loss=rc["stop_loss"],
                take_profit=rc["take_profit"],
                position_size=rc["position_size"],
                signal_ids=[s["id"]],
            )

            if trade_id:
                # Build and store the full trade record (audit trail)
                record = _build_trade_record(db, s, rc, trade_id)
                tr = TradeRecord(trade_id=trade_id, record=record)
                db.insert_trade_record(tr)
                db.update_signal(s["id"], status="approved", was_traded=True, trade_id=trade_id)
                executed += 1
                logger.info(f"Executed trade {trade_id}: {s['direction']} {s['instrument']}")
            else:
                db.update_signal(
                    s["id"], status="rejected",
                    risk_check={**rc, "execution_failed": True},
                )
                failed += 1
                logger.warning(f"Execution failed for {s['instrument']} {s['direction']}")

        logger.info(f"Execution complete: {executed} traded, {failed} failed")
        print(json.dumps({
            "status": "ok",
            "command": "execute",
            "signals_processed": len(to_execute),
            "executed": executed,
            "failed": failed,
        }))
    finally:
        db.close()


def cmd_backfill_broker_history(since: str, repair: bool = False):
    """Import closed trades from Capital.com history for diagnostic inspection.

    Useful when trades opened and closed between reconcile ticks and are missing
    from the local DB. Idempotent — skips deals already present in `trades`.
    With --repair, also overwrites `pnl` on already-present closed trades when
    the broker's realized EUR PnL differs from what's stored locally (fixes
    mis-denominated PnL from the old quote-currency bug).
    """
    from backend.core.config import load_config
    from backend.core.database import Database
    from backend.core.models import Trade
    from backend.data.capitalcom_client import CapitalComClient
    from backend.data.provider import pip_value

    config = load_config()
    db = Database("data/sentinel.db")
    broker = CapitalComClient(config)

    if not broker.is_connected:
        logger.error("Broker not connected — cannot backfill history")
        print(json.dumps({"status": "error", "command": "backfill-broker-history",
                          "error": "broker not connected"}))
        db.close()
        return

    try:
        closed = broker.get_closed_trades_since(since)
        logger.info(f"Broker returned {len(closed)} closed deals since {since}")

        imported = 0
        skipped = 0
        repaired = 0
        total_pnl = 0.0
        rows_for_print: list[dict] = []
        repair_log: list[dict] = []

        for deal in closed:
            deal_id = deal.get("broker_deal_id") or ""
            if not deal_id:
                continue

            existing = db.get_trade_by_deal_id(deal_id)
            if existing:
                broker_pnl = deal.get("pnl")
                local_pnl = existing.get("pnl")
                if (
                    repair
                    and broker_pnl is not None
                    and (local_pnl is None or abs(float(local_pnl) - float(broker_pnl)) > 0.01)
                ):
                    update_kwargs = {"pnl": broker_pnl}
                    # If broker says closed but DB says open, also flip status
                    if existing.get("status") == "open":
                        update_kwargs["status"] = "closed"
                        update_kwargs["close_reason"] = "broker_backfill_repair"
                        if deal.get("closed_at"):
                            update_kwargs["closed_at"] = deal["closed_at"]
                        if deal.get("exit_price"):
                            update_kwargs["exit_price"] = deal["exit_price"]
                    db.update_trade(existing["id"], **update_kwargs)
                    db.insert_trade_event(existing["id"], "pnl_repaired", {
                        "source": "broker_backfill_repair",
                        "old_pnl": local_pnl,
                        "new_pnl": broker_pnl,
                        "broker_currency": deal.get("pnl_currency"),
                        "status_flip": existing.get("status") == "open",
                    })
                    repaired += 1
                    repair_log.append({
                        "deal_id": deal_id,
                        "instrument": deal.get("instrument"),
                        "old_pnl": local_pnl,
                        "new_pnl": broker_pnl,
                        "status_flipped_to_closed": existing.get("status") == "open",
                    })
                    logger.info(
                        f"Repaired trade {existing['id']} ({deal.get('instrument')}): "
                        f"{local_pnl} → {broker_pnl} EUR"
                    )
                skipped += 1
                continue

            # Derive pip-based PnL when the broker gave us a numeric PnL
            pnl = deal.get("pnl")
            entry = deal.get("entry_price")
            exit_p = deal.get("exit_price")
            pnl_pips = None
            instrument = deal.get("instrument", "")
            if entry and exit_p and instrument:
                try:
                    pv = pip_value(instrument)
                    if deal.get("direction") == "long":
                        pnl_pips = round((exit_p - entry) / pv, 1)
                    elif deal.get("direction") == "short":
                        pnl_pips = round((entry - exit_p) / pv, 1)
                except Exception:
                    pass

            # Fall back to the close timestamp (or now) if the broker didn't
            # return an explicit opened_at — per-deal activity lookup often
            # returns empty for older settled deals.
            opened_at = deal.get("opened_at") or deal.get("closed_at")
            closed_at = deal.get("closed_at") or deal.get("opened_at")

            trade_kwargs = dict(
                instrument=instrument,
                direction=deal.get("direction", "") or "long",
                size=deal.get("size") or 0.0,
                entry_price=entry or 0.0,
                stop_loss=deal.get("stop_loss"),
                take_profit=deal.get("take_profit"),
                exit_price=exit_p,
                pnl=pnl,
                pnl_pips=pnl_pips,
                status="closed",
                source="broker_backfill",
                broker_deal_id=deal_id,
                closed_at=closed_at,
                close_reason="broker_backfill",
            )
            if opened_at:
                trade_kwargs["opened_at"] = opened_at
            trade = Trade(**trade_kwargs)
            trade_id = db.insert_trade(trade)

            db.insert_trade_event(trade_id, "broker_backfill", {
                "source": "capitalcom_history",
                "deal": {
                    "broker_deal_id": deal_id,
                    "instrument": instrument,
                    "epic": deal.get("epic"),
                    "direction": deal.get("direction"),
                    "size": deal.get("size"),
                    "entry_price": entry,
                    "exit_price": exit_p,
                    "stop_loss": deal.get("stop_loss"),
                    "take_profit": deal.get("take_profit"),
                    "pnl": pnl,
                    "opened_at": deal.get("opened_at"),
                    "closed_at": deal.get("closed_at"),
                },
                "raw_activities": deal.get("raw_activities"),
                "raw_transaction": deal.get("raw_transaction"),
            })

            if isinstance(pnl, (int, float)):
                total_pnl += pnl
            imported += 1

            rows_for_print.append({
                "deal_id": deal_id,
                "instrument": instrument,
                "direction": deal.get("direction"),
                "size": deal.get("size"),
                "entry": entry,
                "exit": exit_p,
                "pnl": pnl,
                "opened_at": deal.get("opened_at"),
                "closed_at": deal.get("closed_at"),
            })

        logger.info(
            f"Backfill complete: {imported} imported, {skipped} skipped, "
            f"{repaired} repaired, total_pnl={total_pnl:.2f}"
        )
        print(json.dumps({
            "status": "ok",
            "command": "backfill-broker-history",
            "since": since,
            "broker_deals_returned": len(closed),
            "imported": imported,
            "skipped": skipped,
            "repaired": repaired,
            "repair_log": repair_log,
            "total_pnl": round(total_pnl, 2),
            "trades": rows_for_print,
        }, indent=2))
    finally:
        db.close()


def cmd_reconcile():
    """Sync local trade state with broker positions."""
    from datetime import datetime, timedelta, timezone
    from backend.core.config import load_config
    from backend.core.database import Database
    from backend.main import create_data_provider
    from backend.execution.executor import Executor

    config = load_config()
    db = Database("data/sentinel.db")
    broker = create_data_provider(config)
    executor = Executor(config, broker, db)

    try:
        closed_ids = executor.reconcile_positions()
        untracked = executor.get_untracked_positions()

        # Catch trades that opened and closed between ticks — those never show up
        # in /positions, so the bidirectional sync above misses them entirely.
        # Look back 2h by default; backfill is idempotent per broker_deal_id.
        # repair=True auto-fixes any mismatched PnL on already-imported trades.
        history_since = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        bf = executor.backfill_closed_history(history_since, repair=True)
        backfilled = bf.get("imported", [])
        repaired = bf.get("repaired", [])

        if closed_ids:
            logger.info(f"Reconciled {len(closed_ids)} closed trades: {closed_ids}")
        if untracked:
            logger.info(f"Imported {len(untracked)} untracked broker positions")
        if backfilled:
            logger.info(f"Backfilled {len(backfilled)} closed trades from broker history")
        if repaired:
            logger.info(f"Repaired PnL on {len(repaired)} existing trades")

        print(json.dumps({
            "status": "ok",
            "command": "reconcile",
            "trades_closed": len(closed_ids),
            "untracked_imported": len(untracked),
            "history_backfilled": len(backfilled),
            "pnl_repaired": len(repaired),
            "closed_trade_ids": closed_ids,
        }))
    finally:
        db.close()


async def _run_llm_pipeline(db, config, broker, risk, executor):
    """Run the LLM news pipeline end-to-end against an existing DB connection.

    Used by the FastAPI server endpoints in place of the deleted NewsStream
    class. Goes through the full orchestrated flow: ingest → relevance →
    signals → challenge → bias → risk → execute. Bias/risk/execute are
    stream-agnostic, so any pending strategy signals will also be processed.
    """
    from backend.data.news_ingestor import ingest_pipeline
    from backend.data.price_ingestor import ingest_prices
    from backend.signals.relevance import run_relevance
    from backend.signals.signal_generator import run_signals
    from backend.signals.challenge import run_challenge
    from backend.signals.bias import run_bias

    await ingest_pipeline(config, db)
    ingest_prices(config, db)
    run_relevance(db, config)
    run_signals(db, config)
    run_challenge(db, config)
    run_bias(db, config)
    # Risk + execute reuse the same logic as cmd_risk/cmd_execute. Calling
    # the cli command functions directly is simplest — they manage their own
    # DB lifecycle but operate on the shared sentinel.db file.
    cmd_risk()
    cmd_execute()


def cmd_tick(force_market_open: bool = False):
    """Run full pipeline: ingest → relevance → signals → challenge → strategies → bias → risk → execute → reconcile."""
    from backend.main import is_market_open

    if force_market_open:
        import backend.main
        backend.main._force_market_open = True

    if not force_market_open and not is_market_open():
        logger.info("Market closed — skipping tick")
        print(json.dumps({"status": "ok", "command": "tick", "skipped": "market_closed"}))
        return

    stages = [
        ("ingest", cmd_ingest),
        ("relevance", cmd_relevance),
        ("signals", cmd_signals),
        ("challenge", cmd_challenge),
        ("strategies", cmd_strategies),
        ("bias", cmd_bias),
        ("risk", cmd_risk),
        ("execute", cmd_execute),
        ("reconcile", cmd_reconcile),
    ]

    import io
    results = {}
    for name, func in stages:
        logger.info(f"── tick: running stage '{name}' ──")
        try:
            # Suppress per-stage stdout prints; logs still go to stderr/file
            old_stdout = sys.stdout
            sys.stdout = io.StringIO()
            try:
                func()
            finally:
                captured = sys.stdout.getvalue()
                sys.stdout = old_stdout
            # Parse the stage's JSON output if available
            for line in captured.strip().splitlines():
                try:
                    results[name] = json.loads(line)
                except json.JSONDecodeError:
                    pass
            if name not in results:
                results[name] = "ok"
        except Exception as e:
            logger.error(f"Stage '{name}' failed: {e}")
            results[name] = {"status": "error", "error": str(e)}

    # Record equity snapshots and export dashboard JSON
    try:
        from backend.core.config import load_config
        from backend.core.database import Database

        config = load_config()
        db = Database("data/sentinel.db")

        # Equity snapshots for each stream
        streams_cfg = config.get("streams", {})
        for stream_id, cfg_key in [("news", "news_stream"), ("strategy", "strategy_stream")]:
            capital = streams_cfg.get(cfg_key, {}).get("capital_allocation", 100)
            trades = db.get_trades(stream_id, limit=10000)
            realized_pnl = sum(t["pnl"] for t in trades if t.get("pnl") is not None)
            equity = capital + realized_pnl
            open_count = db.count_open_positions(stream_id)
            db.insert_equity_snapshot(stream_id, round(equity, 2), open_count)

        # Account-level equity from live broker balance
        try:
            from backend.data.capitalcom_client import CapitalComClient
            broker = CapitalComClient(config)
            if broker.is_connected:
                summary = broker.get_account_summary()
                account_equity = summary.get("balance", 0) + summary.get("unrealizedPL", 0)
                total_open = sum(db.count_open_positions(s) for s in ["news", "strategy"])
                db.insert_equity_snapshot("account", round(account_equity, 2), total_open)
        except Exception as e:
            logger.warning(f"Failed to record account equity: {e}")

        # Export dashboard JSON
        from backend.dashboard.json_exporter import export_all
        export_all(db_path="data/sentinel.db")

        db.close()
        logger.info("Equity snapshots recorded and dashboard JSON exported")
    except Exception as e:
        logger.error(f"Post-tick export failed: {e}")

    print(json.dumps({"status": "ok", "command": "tick", "stages": results}))


def _build_trade_record(db, signal: dict, risk_check: dict, trade_id: str) -> dict:
    """Assemble the full audit trail for a trade from all pipeline stages."""
    # Parse JSON string fields
    parsed = {}
    for field in ("bias_check", "risk_check", "metadata", "challenge_output",
                  "price_context", "key_factors", "risk_factors", "headlines_used"):
        val = signal.get(field)
        if isinstance(val, str):
            try:
                parsed[field] = json.loads(val)
            except (json.JSONDecodeError, TypeError):
                parsed[field] = val
        else:
            parsed[field] = val

    # Get bias state at trade time
    bias_states = db.get_bias_state(signal["instrument"])
    bias_at_trade = None
    if bias_states:
        bs = bias_states[0]
        bias_at_trade = {
            "direction": bs.get("current_bias"),
            "strength": bs.get("bias_strength"),
            "bias_since": bs.get("bias_since"),
        }

    record = {
        "trade_id": trade_id,
        "signal_id": signal["id"],
        "instrument": signal["instrument"],
        "direction": signal["direction"],
        "source": signal["source"],
        "signal": {
            "confidence": signal["confidence"],
            "reasoning": signal.get("reasoning"),
            "key_factors": parsed.get("key_factors"),
            "risk_factors": parsed.get("risk_factors"),
            "prompt_version": signal.get("prompt_version"),
            "model": signal.get("model"),
        },
        "challenge": parsed.get("challenge_output"),
        "headlines_used": parsed.get("headlines_used"),
        "price_context": parsed.get("price_context"),
        "bias_at_trade": bias_at_trade,
        "risk_decision": risk_check,
        "metadata": parsed.get("metadata"),
    }

    return record


# ── Entry point ─────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        prog="python -m backend",
        description="Forex Sentinel — autonomous forex trading pipeline",
    )
    subparsers = parser.add_subparsers(dest="command")

    # init-db
    sub = subparsers.add_parser("init-db", help="Initialize database and seed prompts")
    sub.add_argument("--fresh", action="store_true", help="Drop and recreate all tables")

    # Pipeline stage stubs
    for cmd, help_text in [
        ("ingest", "Fetch news + prices, store in DB"),
        ("relevance", "Run Stage 2a: LLM relevance assessment"),
        ("signals", "Run Stage 2b: LLM signal generation"),
        ("challenge", "Run Stage 2c: counter-argument challenge"),
        ("strategies", "Run all strategies on price data"),
        ("bias", "Update directional bias tracker"),
        ("risk", "Run risk checks on pending signals"),
        ("execute", "Execute approved trades"),
        ("reconcile", "Sync with broker positions"),
        ("prompts", "Show prompts in DB and which one is live per stage"),
    ]:
        subparsers.add_parser(cmd, help=help_text)

    # tick (full pipeline)
    sub = subparsers.add_parser("tick", help="Run full pipeline (all stages in order)")
    sub.add_argument("--force-market-open", action="store_true", help="Bypass market hours check")

    # backfill-broker-history
    sub = subparsers.add_parser(
        "backfill-broker-history",
        help="Import closed trades from Capital.com history since a given timestamp",
    )
    sub.add_argument("--since", required=True,
                     help="ISO timestamp to start from (e.g. 2026-04-15T14:57:00Z)")
    sub.add_argument("--repair", action="store_true",
                     help="Also overwrite pnl on already-imported trades when the "
                          "broker's realized EUR PnL differs from what's stored locally")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "init-db":
        cmd_init_db(fresh=args.fresh)
    elif args.command == "ingest":
        cmd_ingest()
    elif args.command == "relevance":
        cmd_relevance()
    elif args.command == "signals":
        cmd_signals()
    elif args.command == "challenge":
        cmd_challenge()
    elif args.command == "strategies":
        cmd_strategies()
    elif args.command == "bias":
        cmd_bias()
    elif args.command == "risk":
        cmd_risk()
    elif args.command == "execute":
        cmd_execute()
    elif args.command == "reconcile":
        cmd_reconcile()
    elif args.command == "tick":
        cmd_tick(force_market_open=args.force_market_open)
    elif args.command == "prompts":
        cmd_prompts()
    elif args.command == "backfill-broker-history":
        cmd_backfill_broker_history(since=args.since, repair=args.repair)


if __name__ == "__main__":
    main()
