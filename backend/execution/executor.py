"""Trade execution — places and manages orders via the configured data provider."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("forex_sentinel.executor")

# Only these statuses from place_order() mean the order actually went through
CONFIRMED_STATUSES = {"ACCEPTED", "OPEN", "AMENDED", "simulated"}


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
        from backend.core.models import Trade
        trade = Trade(
            instrument=instrument,
            direction=direction,
            size=position_size,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            source=stream_id,
            signal_id=signal_ids[0] if signal_ids else None,
            broker_deal_id=broker_deal_id,
            status="open",
        )
        trade_id = self.db.insert_trade(trade)

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

    def backfill_closed_history(self, since_iso: str, repair: bool = False) -> dict:
        """Import closed deals from broker history that aren't in the local DB.

        Catches trades that opened and closed between reconcile ticks — those
        never appear in `/api/v1/positions` and would otherwise be lost.

        When `repair=True`, also overwrites the PnL (and flips status to closed
        if still open locally) on already-imported deals when the broker's
        realized EUR PnL differs from what's stored locally. Idempotent — if
        local already matches broker, it's a no-op.

        Returns a dict with `imported` and `repaired` lists of trade IDs.
        """
        if not self.broker.is_connected:
            return {"imported": [], "repaired": []}
        get_history = getattr(self.broker, "get_closed_trades_since", None)
        if not callable(get_history):
            return {"imported": [], "repaired": []}

        try:
            closed_deals = get_history(since_iso)
        except Exception as e:
            logger.warning(f"Broker history fetch failed: {e}")
            return {"imported": [], "repaired": []}

        imported: list[str] = []
        repaired: list[str] = []
        for deal in closed_deals:
            deal_id = deal.get("broker_deal_id") or ""
            if not deal_id:
                continue
            existing = self.db.get_trade_by_deal_id(deal_id)
            if existing:
                if repair:
                    broker_pnl = deal.get("pnl")
                    local_pnl = existing.get("pnl")
                    if broker_pnl is not None and (
                        local_pnl is None
                        or abs(float(local_pnl) - float(broker_pnl)) > 0.01
                    ):
                        update_kwargs = {"pnl": broker_pnl}
                        if existing.get("status") == "open":
                            update_kwargs["status"] = "closed"
                            update_kwargs["close_reason"] = "broker_backfill_repair"
                            if deal.get("closed_at"):
                                update_kwargs["closed_at"] = deal["closed_at"]
                            if deal.get("exit_price"):
                                update_kwargs["exit_price"] = deal["exit_price"]
                        self.db.update_trade(existing["id"], **update_kwargs)
                        self.db.insert_trade_event(existing["id"], "pnl_repaired", {
                            "source": "sync_backfill_repair",
                            "old_pnl": local_pnl,
                            "new_pnl": broker_pnl,
                            "broker_currency": deal.get("pnl_currency"),
                            "status_flip": existing.get("status") == "open",
                        })
                        logger.info(
                            f"Repaired trade {existing['id']} ({deal.get('instrument')}): "
                            f"pnl {local_pnl} → {broker_pnl} EUR"
                        )
                        repaired.append(existing["id"])
                continue

            instrument = deal.get("instrument") or ""
            entry = deal.get("entry_price") or 0.0
            exit_p = deal.get("exit_price")
            pnl_pips = None
            if entry and exit_p and instrument:
                try:
                    from backend.data.provider import pip_value
                    pv = pip_value(instrument)
                    if deal.get("direction") == "long":
                        pnl_pips = round((exit_p - entry) / pv, 1)
                    elif deal.get("direction") == "short":
                        pnl_pips = round((entry - exit_p) / pv, 1)
                except Exception:
                    pass

            opened_at = deal.get("opened_at") or deal.get("closed_at")
            closed_at = deal.get("closed_at") or deal.get("opened_at")
            from backend.core.models import Trade
            trade_kwargs = dict(
                instrument=instrument,
                direction=deal.get("direction") or "long",
                size=deal.get("size") or 0.0,
                entry_price=entry,
                stop_loss=deal.get("stop_loss"),
                take_profit=deal.get("take_profit"),
                exit_price=exit_p,
                pnl=deal.get("pnl"),
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
            trade_id = self.db.insert_trade(trade)
            self.db.insert_trade_event(trade_id, "broker_backfill", {
                "source": "capitalcom_history",
                "deal": {k: deal.get(k) for k in (
                    "broker_deal_id", "instrument", "epic", "direction", "size",
                    "entry_price", "exit_price", "stop_loss", "take_profit",
                    "pnl", "opened_at", "closed_at",
                )},
                "raw_activities": deal.get("raw_activities"),
                "raw_transaction": deal.get("raw_transaction"),
            })
            logger.info(
                f"Backfilled closed trade {trade_id} deal_id={deal_id} "
                f"{instrument} {deal.get('direction')} size={deal.get('size')} pnl={deal.get('pnl')}"
            )
            imported.append(trade_id)

        return {"imported": imported, "repaired": repaired}

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
        local_open = self.db.get_open_trades_by_source(stream_id)
        for trade in local_open:
            broker_deal_id = trade.get("broker_deal_id") or ""

            if not broker_deal_id or broker_deal_id.startswith("offline-"):
                # Offline/simulated trade — skip reconciliation, not a real broker position
                continue
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
        all_open = self.db.get_open_trades_by_source()
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
                    logger.info(
                        f"Reconciliation: importing untracked broker position deal_id={deal_id} "
                        f"{pos.get('instrument')} {pos.get('direction')}"
                    )
                    from backend.core.models import Trade
                    imported_trade = Trade(
                        instrument=pos.get("instrument", ""),
                        direction=pos.get("direction", ""),
                        size=float(pos.get("currentUnits", 0)),
                        entry_price=pos.get("entry_price", 0),
                        stop_loss=pos.get("stop_loss"),
                        take_profit=pos.get("take_profit"),
                        source="broker",
                        broker_deal_id=deal_id,
                        status="open",
                    )
                    trade_id = self.db.insert_trade(imported_trade)
                    self.db.insert_trade_event(trade_id, "imported", {
                        "source": "broker_reconciliation",
                        "broker_data": {
                            "dealId": deal_id,
                            "instrument": pos.get("instrument"),
                            "direction": pos.get("direction"),
                            "unrealizedPL": pos.get("unrealizedPL"),
                        },
                    })
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
            if broker_size_f > 0 and abs(broker_size_f - trade["size"]) > 0.01:
                old_size = trade["size"]
                changes["size"] = broker_size_f
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

        Priority:
        1. Broker's realized EUR PnL from the transactions ledger (authoritative).
        2. Broker deal activity for exit level + local EUR calc as fallback.
        3. Current market price as estimate.
        4. SL price as last resort.
        """
        deal_id = trade.get("broker_deal_id", "")

        # Try broker deal activity for exit level and close time
        exit_price = None
        actual_close_time = None
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
                        lvl = float(close_action.get("level", 0) or 0)
                        if lvl > 0:
                            exit_price = lvl
                    actual_close_time = activity.get("date") or activity.get("timestamp")
            except Exception as e:
                logger.warning(f"Deal activity lookup failed for {deal_id}: {e}")

        # Fallbacks for exit price
        if not exit_price:
            try:
                exit_price = self.broker.get_current_price(trade["instrument"])["mid"]
            except Exception as e:
                logger.warning(f"Market price fallback failed for trade {trade['id']}: {e}")
                exit_price = trade.get("stop_loss") or trade.get("entry_price")
                logger.warning(f"Using fallback exit estimate {exit_price} for trade {trade['id']}")

        result = Executor.calc_pnl(trade, exit_price, broker=self.broker)

        # Prefer broker's realized PnL from the transaction ledger — it's the
        # account-currency source of truth and uses the broker's actual fill.
        if deal_id:
            try:
                realized = getattr(self.broker, "get_realized_pnl", lambda *_: None)(deal_id)
                if realized and realized.get("pnl") is not None:
                    logger.info(
                        f"Trade {trade['id']} PnL: broker realized={realized['pnl']} "
                        f"{realized.get('currency')} (local calc={result['pnl']} EUR)"
                    )
                    result["pnl"] = realized["pnl"]
                    if realized.get("date") and not actual_close_time:
                        actual_close_time = realized["date"]
            except Exception as e:
                logger.warning(f"Realized PnL lookup failed for {deal_id}: {e}")

        if actual_close_time:
            result["actual_close_time"] = actual_close_time
        return result

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
        return Executor.calc_pnl(trade, exit_price, broker=self.broker)

    @staticmethod
    def calc_pnl(trade: dict, exit_price: float, broker=None) -> dict:
        """Calculate P&L from entry and exit price, converted to the account currency (EUR).

        The raw `(exit - entry) * size` expression returns PnL in the *quote*
        currency of the pair (JPY for USD/JPY, CHF for USD/CHF, etc). Without a
        conversion step, reconciled trades got stored as if those numbers were
        EUR — which was how a ~84-pip loss on USD/JPY was rendered as €843
        when the real loss was about €5. When a `broker` is provided we pull a
        live EUR-per-quote rate and convert; otherwise we return the raw
        quote-currency number and mark it as unconverted.
        """
        from backend.data.provider import pip_value
        pip_val = pip_value(trade["instrument"])
        entry = trade["entry_price"]
        size = trade.get("size") or 0.0
        if trade["direction"] == "long":
            pnl_pips = (exit_price - entry) / pip_val
        else:
            pnl_pips = (entry - exit_price) / pip_val
        pnl_quote = pnl_pips * pip_val * size

        instrument = trade.get("instrument") or ""
        quote = instrument.split("_")[1] if "_" in instrument else ""
        pnl_eur = pnl_quote
        converted = False
        if quote and quote != "EUR" and broker is not None:
            try:
                rate = broker.get_current_price(f"EUR_{quote}")["mid"]
                if rate and rate > 0:
                    pnl_eur = pnl_quote / rate
                    converted = True
            except Exception as e:
                logger.warning(
                    f"EUR conversion for {instrument} failed ({e}); storing raw {quote} PnL"
                )
        elif quote == "EUR":
            converted = True

        return {
            "exit_price": exit_price,
            "pnl": round(pnl_eur, 2),
            "pnl_pips": round(pnl_pips, 1),
            "pnl_currency": "EUR" if converted else quote or "unknown",
        }

    def check_and_close_trades(self, stream_id: str):
        """Check open trades for SL/TP hits and close them."""
        self.reconcile_positions(stream_id=stream_id)
        open_trades = self.db.get_open_trades_by_source(stream_id)
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
            result = Executor.calc_pnl(trade, current_price, broker=self.broker)
            self.db.update_trade(
                trade["id"],
                exit_price=current_price,
                pnl=result["pnl"],
                pnl_pips=result["pnl_pips"],
                status=status,
                closed_at=datetime.now(timezone.utc).isoformat(),
            )
            logger.info(
                f"Trade {trade['id']} {status}: PnL=€{result['pnl']:.2f} "
                f"({result['pnl_pips']:.1f} pips)"
            )
