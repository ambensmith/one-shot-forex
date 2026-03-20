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

        # Record trade open event
        self.db.insert_trade_event(trade_id, "opened", {
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "position_size": position_size,
            "broker_deal_id": broker_deal_id,
        })

        logger.info(f"Trade {trade_id} recorded: {direction} {instrument} deal_id={broker_deal_id}")
        return trade_id

    def reconcile_positions(self, stream_id: str = None) -> list[int]:
        """Full bidirectional reconciliation between local DB and broker.

        DB→Broker: Close local trades that no longer exist on the broker.
        Broker→DB: Detect unknown broker positions, verify SL/TP and sizes.

        Returns list of trade IDs that were just closed by reconciliation.
        """
        if not self.broker.is_connected:
            logger.warning("Reconciliation skipped — broker not connected")
            return []

        try:
            broker_positions = self.broker.get_open_trades()
        except Exception as e:
            logger.warning(f"Reconciliation skipped — failed to fetch broker positions: {e}")
            return []

        # Build maps for bidirectional matching
        broker_by_deal_id = {p["id"]: p for p in broker_positions if p.get("id")}
        broker_deal_ids = set(broker_by_deal_id.keys())

        newly_closed = []

        # ── DB→Broker: find local trades missing from broker ──
        local_open = self.db.get_open_trades(stream_id)
        for trade in local_open:
            broker_deal_id = trade.get("broker_deal_id") or ""

            if not broker_deal_id or broker_deal_id.startswith("offline-"):
                # Phantom trade — never actually executed on broker
                logger.info(
                    f"Reconciliation: trade {trade['id']} ({trade['instrument']} "
                    f"{trade['direction']}) has no broker_deal_id — marking as failed"
                )
                self.db.update_trade(
                    trade["id"],
                    status="failed",
                    pnl=0.0,
                    pnl_pips=0.0,
                    closed_at=datetime.now(timezone.utc).isoformat(),
                )
            elif broker_deal_id not in broker_deal_ids:
                # Real trade closed by broker (SL/TP hit between runs)
                exit_info = self._fetch_exit_details(trade)
                actual_close_time = exit_info.get("actual_close_time")
                close_time = actual_close_time or datetime.now(timezone.utc).isoformat()
                status = self._infer_exit_status(trade, exit_info["exit_price"])
                logger.info(
                    f"Reconciliation: trade {trade['id']} ({trade['instrument']} "
                    f"{trade['direction']}) deal_id={broker_deal_id} closed by broker — "
                    f"exit={exit_info['exit_price']}, pnl={exit_info['pnl']}, status={status}"
                )
                self.db.update_trade(
                    trade["id"],
                    status=status,
                    exit_price=exit_info["exit_price"],
                    pnl=exit_info["pnl"],
                    pnl_pips=exit_info["pnl_pips"],
                    closed_at=close_time,
                )
                self.db.insert_trade_event(trade["id"], status, {
                    "exit_price": exit_info["exit_price"],
                    "pnl": exit_info["pnl"],
                    "pnl_pips": exit_info["pnl_pips"],
                    "actual_close_time": actual_close_time,
                    "detection_time": datetime.now(timezone.utc).isoformat(),
                })
                newly_closed.append(trade["id"])
            else:
                # Trade still open on broker — verify SL/TP and size match
                self._verify_position(trade, broker_by_deal_id[broker_deal_id])

        # ── Broker→DB: detect unknown broker positions ──
        all_local_deal_ids = set()
        all_open = self.db.get_open_trades()
        for t in all_open:
            did = t.get("broker_deal_id") or ""
            if did:
                all_local_deal_ids.add(did)

        self._untracked_positions = []
        for deal_id, pos in broker_by_deal_id.items():
            if deal_id not in all_local_deal_ids:
                # Also check if it exists as a closed trade (recently reconciled)
                existing = self.db.get_trade_by_deal_id(deal_id)
                if not existing:
                    logger.warning(
                        f"Reconciliation: UNTRACKED broker position deal_id={deal_id} "
                        f"{pos.get('instrument')} {pos.get('direction')} — not in local DB"
                    )
                    self._untracked_positions.append(pos)

        return newly_closed

    def _verify_position(self, trade: dict, broker_pos: dict):
        """Verify local trade matches broker position (SL/TP/size)."""
        changes = {}

        # Check stop loss
        broker_sl = broker_pos.get("stop_loss")
        if broker_sl is not None and trade.get("stop_loss"):
            if abs(float(broker_sl) - trade["stop_loss"]) > 1e-6:
                old_sl = trade["stop_loss"]
                changes["stop_loss"] = float(broker_sl)
                self.db.insert_trade_event(trade["id"], "sl_updated", {
                    "old_value": old_sl,
                    "new_value": float(broker_sl),
                    "source": "broker_sync",
                })
                logger.info(
                    f"Trade {trade['id']}: SL updated {old_sl} → {broker_sl} (broker)"
                )

        # Check take profit
        broker_tp = broker_pos.get("take_profit")
        if broker_tp is not None and trade.get("take_profit"):
            if abs(float(broker_tp) - trade["take_profit"]) > 1e-6:
                old_tp = trade["take_profit"]
                changes["take_profit"] = float(broker_tp)
                self.db.insert_trade_event(trade["id"], "tp_updated", {
                    "old_value": old_tp,
                    "new_value": float(broker_tp),
                    "source": "broker_sync",
                })
                logger.info(
                    f"Trade {trade['id']}: TP updated {old_tp} → {broker_tp} (broker)"
                )

        # Check position size
        broker_size = broker_pos.get("currentUnits")
        if broker_size is not None:
            broker_size_f = abs(float(broker_size))
            if broker_size_f > 0 and abs(broker_size_f - trade["position_size"]) > 0.01:
                old_size = trade["position_size"]
                changes["position_size"] = broker_size_f
                self.db.insert_trade_event(trade["id"], "size_adjusted", {
                    "old_value": old_size,
                    "new_value": broker_size_f,
                    "source": "broker_sync",
                })
                logger.info(
                    f"Trade {trade['id']}: size adjusted {old_size} → {broker_size_f} (broker)"
                )

        if changes:
            self.db.update_trade(trade["id"], **changes)

    def get_untracked_positions(self) -> list[dict]:
        """Return broker positions not found in local DB (populated after reconcile)."""
        return getattr(self, "_untracked_positions", [])

    def _fetch_exit_details(self, trade: dict) -> dict:
        """Get exit price/pnl/close time for a reconciled trade.

        Priority: broker deal activity → current market price → SL price → entry price.
        Returns dict with exit_price, pnl, pnl_pips, and optionally actual_close_time.
        """
        # Try broker deal activity
        deal_id = trade.get("broker_deal_id", "")
        if deal_id:
            try:
                activity = self.broker.get_deal_activity(deal_id)
                if activity:
                    actions = activity.get("actions", [])
                    close_action = next(
                        (a for a in actions if a.get("actionType") in
                         ("POSITION_CLOSED", "POSITION_PARTIALLY_CLOSED")),
                        None,
                    )
                    if close_action:
                        exit_price = float(close_action.get("level", 0))
                        if exit_price > 0:
                            result = self._calc_pnl(trade, exit_price)
                            # Extract actual close timestamp from activity
                            close_time = activity.get("date") or activity.get("timestamp")
                            if close_time:
                                result["actual_close_time"] = close_time
                            return result
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

    @staticmethod
    def _infer_exit_status(trade: dict, exit_price: float) -> str:
        """Determine whether a broker-closed trade hit TP, SL, or is ambiguous.

        Compares exit_price to the trade's take_profit and stop_loss levels,
        accounting for direction. Falls back to 'closed_reconciled' when the
        exit price doesn't clearly match either level.
        """
        tp = trade.get("take_profit")
        sl = trade.get("stop_loss")
        direction = trade.get("direction", "long")

        if not tp or not sl:
            return "closed_reconciled"

        if direction == "long":
            if exit_price >= tp:
                return "closed_tp"
            if exit_price <= sl:
                return "closed_sl"
        else:  # short
            if exit_price <= tp:
                return "closed_tp"
            if exit_price >= sl:
                return "closed_sl"

        return "closed_reconciled"

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
