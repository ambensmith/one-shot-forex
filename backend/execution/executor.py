"""Trade execution — places and manages orders via the configured data provider."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("forex_sentinel.executor")

# Only these statuses from place_order() mean the order actually went through
CONFIRMED_STATUSES = {"ACCEPTED", "OPEN", "AMENDED"}


class Executor:
    def __init__(self, config: dict, broker, db):
        self.config = config
        self.broker = broker
        self.db = db
        self.mode = config.get("execution", {}).get("mode", "practice")

    def execute_trade(self, stream_id: str, instrument: str, direction: str,
                      entry_price: float, stop_loss: float, take_profit: float,
                      position_size: float, signal_ids: list[int] | None = None) -> int | None:
        """Place a trade and record it in the database.

        Only records the trade if the broker confirms the order was accepted.
        Returns the trade_id on success, or None if the order failed.
        """
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

        status = result.get("status", "UNKNOWN")
        broker_deal_id = result.get("id", "")

        # Check if order was rejected
        if status == "REJECTED":
            logger.warning(
                f"Order REJECTED for {instrument}: {result.get('error', 'unknown')}"
            )
            return None

        # Only record trade if the broker confirmed the order
        if status not in CONFIRMED_STATUSES:
            logger.warning(
                f"Order status '{status}' is not confirmed for {instrument}. "
                f"NOT recording trade. deal_id={broker_deal_id}"
            )
            return None

        # Record in database with broker_deal_id for later reconciliation
        trade_id = self.db.insert_trade(
            stream=stream_id,
            instrument=instrument,
            direction=direction,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            position_size=position_size,
            signal_ids=signal_ids or [],
            broker_deal_id=broker_deal_id,
        )

        # Update signals with trade_id
        if signal_ids:
            for sid in signal_ids:
                self.db.execute(
                    "UPDATE signals SET was_traded = 1, trade_id = ? WHERE id = ?",
                    (trade_id, sid),
                )
            self.db.commit()

        logger.info(f"Trade {trade_id} recorded: {direction} {instrument} deal_id={broker_deal_id}")
        return trade_id

    def reconcile_positions(self, stream_id: str = None):
        """Close local DB trades that no longer exist as positions on the broker.

        Distinguishes between:
        - Phantom trades (no broker_deal_id): marked as 'failed' with pnl=0
        - Real closures (has broker_deal_id): marked as 'closed_reconciled' with exit price
        """
        if not self.broker.is_connected:
            return

        try:
            broker_positions = self.broker.get_open_trades()
        except Exception as e:
            logger.warning(f"Reconciliation skipped — failed to fetch broker positions: {e}")
            return

        # Build set of (instrument, direction) from live broker positions
        broker_set = {(p["instrument"], p["direction"]) for p in broker_positions}

        # Find local open trades with no matching broker position (stream-scoped)
        local_open = self.db.get_open_trades(stream_id)
        for trade in local_open:
            key = (trade["instrument"], trade["direction"])
            if key not in broker_set:
                broker_deal_id = trade.get("broker_deal_id") or ""

                if not broker_deal_id or broker_deal_id.startswith("offline-"):
                    # Phantom trade — never actually executed on broker
                    logger.info(
                        f"Reconciliation: trade {trade['id']} ({trade['instrument']} "
                        f"{trade['direction']}) is phantom — marking as failed"
                    )
                    self.db.update_trade(
                        trade["id"],
                        status="failed",
                        pnl=0.0,
                        pnl_pips=0.0,
                        closed_at=datetime.now(timezone.utc).isoformat(),
                    )
                else:
                    # Real trade closed by broker (SL/TP hit between runs)
                    exit_info = self._fetch_exit_details(trade)
                    logger.info(
                        f"Reconciliation: trade {trade['id']} ({trade['instrument']} "
                        f"{trade['direction']}) closed by broker — "
                        f"exit={exit_info['exit_price']}, pnl={exit_info['pnl']}"
                    )
                    self.db.update_trade(
                        trade["id"],
                        status="closed_reconciled",
                        exit_price=exit_info["exit_price"],
                        pnl=exit_info["pnl"],
                        pnl_pips=exit_info["pnl_pips"],
                        closed_at=datetime.now(timezone.utc).isoformat(),
                    )

    def _fetch_exit_details(self, trade: dict) -> dict:
        """Get exit price/pnl for a reconciled trade. Always returns real numbers.

        Priority: broker deal activity → current market price → SL price → entry price.
        """
        # Try broker deal activity
        deal_id = trade.get("broker_deal_id", "")
        if deal_id:
            try:
                activity = self.broker.get_deal_activity(deal_id)
                if activity:
                    # Capital.com activity has 'details' with 'level' (exit price)
                    actions = activity.get("actions", [])
                    close_action = next(
                        (a for a in actions if a.get("actionType") in
                         ("POSITION_CLOSED", "POSITION_PARTIALLY_CLOSED")),
                        None,
                    )
                    if close_action:
                        exit_price = float(close_action.get("level", 0))
                        if exit_price > 0:
                            return self._calc_pnl(trade, exit_price)
            except Exception as e:
                logger.warning(f"Deal activity lookup failed for {deal_id}: {e}")

        # Fallback 1: use current market price as estimate
        try:
            price_data = self.broker.get_current_price(trade["instrument"])
            return self._calc_pnl(trade, price_data["mid"])
        except Exception as e:
            logger.warning(f"Market price fallback failed for trade {trade['id']}: {e}")

        # Fallback 2: estimate from SL (conservative — assumes worst case)
        sl = trade.get("stop_loss")
        if sl:
            logger.warning(f"Using SL as exit estimate for trade {trade['id']}")
            return self._calc_pnl(trade, sl)

        # Fallback 3: use entry price (P&L = 0, better than null)
        logger.error(f"No exit price available for trade {trade['id']} — using entry price")
        return self._calc_pnl(trade, trade["entry_price"])

    def _calc_pnl(self, trade: dict, exit_price: float) -> dict:
        """Calculate P&L from entry and exit price."""
        return Executor.calc_pnl(trade, exit_price)

    @staticmethod
    def calc_pnl(trade: dict, exit_price: float) -> dict:
        """Calculate P&L from entry and exit price (static, no Executor instance needed)."""
        from backend.data.provider import pip_value
        pip_val = pip_value(trade["instrument"])
        entry = trade["entry_price"]
        if trade["direction"] == "long":
            pnl_pips = (exit_price - entry) / pip_val
        else:
            pnl_pips = (entry - exit_price) / pip_val
        pnl = pnl_pips * pip_val * trade["position_size"]
        return {"exit_price": exit_price, "pnl": round(pnl, 2), "pnl_pips": round(pnl_pips, 1)}

    def check_and_close_trades(self, stream_id: str):
        """Check open trades for SL/TP hits and close them."""
        self.reconcile_positions(stream_id=stream_id)
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
