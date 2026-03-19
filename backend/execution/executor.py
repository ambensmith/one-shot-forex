"""Trade execution — places and manages orders via the configured data provider."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("forex_sentinel.executor")


class Executor:
    def __init__(self, config: dict, broker, db):
        self.config = config
        self.broker = broker
        self.db = db
        self.mode = config.get("execution", {}).get("mode", "practice")

    def execute_trade(self, stream_id: str, instrument: str, direction: str,
                      entry_price: float, stop_loss: float, take_profit: float,
                      position_size: float, signal_ids: list[int] | None = None) -> int | None:
        """Place a trade and record it in the database."""
        logger.info(
            f"Executing {direction} {instrument} size={position_size} "
            f"entry={entry_price} SL={stop_loss} TP={take_profit} stream={stream_id}"
        )

        # Place order via broker
        result = self.broker.place_order(
            instrument=instrument,
            units=position_size,
            side=direction,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )

        # Check if order was rejected
        if result.get("status") == "REJECTED":
            logger.warning(
                f"Order REJECTED for {instrument}: {result.get('error', 'unknown')}"
            )
            return None

        # Record in database
        trade_id = self.db.insert_trade(
            stream=stream_id,
            instrument=instrument,
            direction=direction,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            position_size=position_size,
            signal_ids=signal_ids or [],
        )

        # Update signals with trade_id
        if signal_ids:
            for sid in signal_ids:
                self.db.execute(
                    "UPDATE signals SET was_traded = 1, trade_id = ? WHERE id = ?",
                    (trade_id, sid),
                )
            self.db.commit()

        return trade_id

    def reconcile_positions(self):
        """Close local DB trades that no longer exist as positions on the broker."""
        if not self.broker.is_connected:
            return

        try:
            broker_positions = self.broker.get_open_trades()
        except Exception as e:
            logger.warning(f"Reconciliation skipped — failed to fetch broker positions: {e}")
            return

        # Build set of (instrument, direction) from live broker positions
        broker_set = {(p["instrument"], p["direction"]) for p in broker_positions}

        # Find local open trades with no matching broker position
        local_open = self.db.get_open_trades()
        for trade in local_open:
            key = (trade["instrument"], trade["direction"])
            if key not in broker_set:
                logger.info(
                    f"Reconciliation: closing orphaned trade {trade['id']} "
                    f"({trade['instrument']} {trade['direction']}) — not found on broker"
                )
                self.db.update_trade(
                    trade["id"],
                    status="closed_reconciled",
                    closed_at=datetime.now(timezone.utc).isoformat(),
                )

    def check_and_close_trades(self, stream_id: str):
        """Check open trades for SL/TP hits and close them."""
        self.reconcile_positions()
        open_trades = self.db.get_open_trades(stream_id)
        for trade in open_trades:
            try:
                price_data = self.broker.get_current_price(trade["instrument"])
                current_price = price_data["mid"]
                self._check_trade_exit(trade, current_price)
            except Exception as e:
                logger.warning(f"Error checking trade {trade['id']}: {e}")

    def _check_trade_exit(self, trade: dict, current_price: float):
        """Check if a trade should be closed."""
        direction = trade["direction"]
        sl = trade["stop_loss"]
        tp = trade["take_profit"]
        entry = trade["entry_price"]

        closed = False
        status = ""

        if direction == "long":
            if current_price <= sl:
                closed, status = True, "closed_sl"
            elif current_price >= tp:
                closed, status = True, "closed_tp"
        else:  # short
            if current_price >= sl:
                closed, status = True, "closed_sl"
            elif current_price <= tp:
                closed, status = True, "closed_tp"

        if closed:
            from backend.data.provider import pip_value
            pip_val = pip_value(trade["instrument"])
            if direction == "long":
                pnl_pips = (current_price - entry) / pip_val
            else:
                pnl_pips = (entry - current_price) / pip_val
            pnl = pnl_pips * pip_val * trade["position_size"]

            self.db.update_trade(
                trade["id"],
                exit_price=current_price,
                pnl=pnl,
                pnl_pips=pnl_pips,
                status=status,
                closed_at=datetime.now(timezone.utc).isoformat(),
            )
            logger.info(f"Trade {trade['id']} {status}: PnL={pnl:.2f} ({pnl_pips:.1f} pips)")
