"""Risk manager — validates trades against risk rules before execution."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("forex_sentinel.risk")


# Correlated instrument groups
CORRELATION_GROUPS = [
    {"EUR_USD", "EUR_GBP", "EUR_JPY"},
    {"GBP_USD", "GBP_JPY", "EUR_GBP"},
    {"USD_JPY", "EUR_JPY", "GBP_JPY"},
    {"BCO_USD", "WTICO_USD"},
    {"XAU_USD", "XAG_USD"},
]


@dataclass
class RiskCheck:
    approved: bool
    position_size: float = 0.0
    rejection_reason: str | None = None


class RiskManager:
    def __init__(self, config: dict, broker, db):
        self.config = config
        self.broker = broker
        self.db = db
        risk_cfg = config.get("risk", {})
        self.max_risk_per_trade = risk_cfg.get("max_risk_per_trade", 0.01)
        self.max_open_per_stream = risk_cfg.get("max_open_positions_per_stream", 5)
        self.max_daily_loss = risk_cfg.get("max_daily_loss_per_stream", 0.03)
        self.max_correlated = risk_cfg.get("max_correlated_positions", 2)
        self.default_rr = risk_cfg.get("default_rr_ratio", 1.5)
        self.sl_method = risk_cfg.get("stop_loss_method", "atr")
        self.atr_multiplier = risk_cfg.get("atr_multiplier", 1.5)
        self.atr_period = risk_cfg.get("atr_period", 14)
        self.leverage = risk_cfg.get("leverage", 1)
        self.target_notional_eur = risk_cfg.get("target_notional_eur", 0)
        self.fixed_position_size = risk_cfg.get("fixed_position_size", 0)

    def check_trade(self, stream_id: str, instrument: str,
                    direction: str, entry_price: float,
                    stop_loss: float) -> RiskCheck:
        from backend.main import is_market_open
        if not is_market_open():
            return RiskCheck(approved=False, rejection_reason="Market closed")

        # Max open positions check
        open_count = self.db.count_open_positions(stream_id)
        if open_count >= self.max_open_per_stream:
            return RiskCheck(approved=False,
                             rejection_reason=f"Max open positions ({self.max_open_per_stream}) reached")

        # Daily loss limit check
        equity = self.db.get_stream_equity(stream_id)
        if equity <= 0:
            try:
                summary = self.broker.get_account_summary()
                equity = summary.get("balance", 0)
            except Exception:
                pass
        if equity <= 0:
            return RiskCheck(approved=False, rejection_reason="No equity data available")
        daily_pnl = self.db.get_daily_pnl(stream_id)
        if daily_pnl < -(equity * self.max_daily_loss):
            return RiskCheck(approved=False,
                             rejection_reason=f"Daily loss limit ({self.max_daily_loss*100}%) exceeded")

        # Correlation check
        open_trades = self.db.get_open_trades_by_source(stream_id)
        open_instruments = {t["instrument"] for t in open_trades}
        for group in CORRELATION_GROUPS:
            if instrument in group:
                correlated_open = len(open_instruments & group)
                if correlated_open >= self.max_correlated:
                    return RiskCheck(
                        approved=False,
                        rejection_reason=f"Max correlated positions ({self.max_correlated}) for group",
                    )

        # Calculate position size
        if self.fixed_position_size > 0:
            position_size = self.fixed_position_size
        elif self.target_notional_eur > 0:
            position_size = self._convert_eur_to_units(instrument, self.target_notional_eur)
        else:
            position_size = self.calculate_position_size(
                equity, self.max_risk_per_trade, entry_price, stop_loss, instrument
            )

        if position_size <= 0:
            return RiskCheck(approved=False, rejection_reason="Position size too small")

        return RiskCheck(approved=True, position_size=position_size)

    def calculate_position_size(self, account_balance: float, risk_pct: float,
                                 entry: float, stop_loss: float,
                                 instrument: str) -> float:
        """Position size = (balance * risk%) / (|entry - stop_loss| * pip_value)."""
        from backend.data.provider import pip_value
        pip_val = pip_value(instrument)
        stop_distance = abs(entry - stop_loss)
        if stop_distance == 0:
            return 0.0
        risk_amount = account_balance * risk_pct
        pips = stop_distance / pip_val
        if pips == 0:
            return 0.0
        # For forex, 1 standard lot = 100,000 units; pip value ~$10 per lot
        # Simplified: units = risk_amount / stop_distance
        units = risk_amount / stop_distance
        units *= self.leverage
        return round(units)

    # Capital.com minimum deal sizes per base currency
    MIN_SIZES = {"XAU": 0.1, "XAG": 1.0}
    MIN_SIZE_DEFAULT = 100  # forex pairs: 100 units minimum

    def _convert_eur_to_units(self, instrument: str, target_eur: float) -> float:
        """Convert a target EUR notional amount to Capital.com position units.

        Capital.com 'size' = units of the base currency of the pair.
        E.g. for USD/CAD, size=1080 means 1080 USD notional exposure.
        Clamps to broker minimums automatically.
        """
        base = instrument.split("_")[0]

        if base == "EUR":
            units = target_eur
        else:
            eur_per_base = self._get_eur_per_base(base)
            units = target_eur / eur_per_base

        # Round: XAU to 2 decimals (fractional ounces), forex to integers
        if base == "XAU":
            units = round(units, 2)
        else:
            units = round(units)

        # Clamp to Capital.com minimum deal sizes
        min_size = self.MIN_SIZES.get(base, self.MIN_SIZE_DEFAULT)
        if units < min_size:
            logger.info(
                "EUR sizing: %.2f units for %s below minimum %s, clamping",
                units, instrument, min_size,
            )
            units = min_size

        logger.info(
            "EUR sizing: €%.0f → %.2f units for %s",
            target_eur, units, instrument,
        )
        return units

    def _get_eur_per_base(self, base: str) -> float:
        """Return the value of 1 unit of base currency in EUR."""
        try:
            if base == "USD":
                eurusd = self.broker.get_current_price("EUR_USD")["mid"]
                return 1.0 / eurusd
            elif base == "GBP":
                eurgbp = self.broker.get_current_price("EUR_GBP")["mid"]
                return 1.0 / eurgbp
            else:
                # Cross via USD for AUD, XAU, NZD, etc.
                base_usd = self.broker.get_current_price(f"{base}_USD")["mid"]
                eurusd = self.broker.get_current_price("EUR_USD")["mid"]
                return base_usd / eurusd
        except Exception as e:
            logger.warning("Could not get EUR rate for %s, defaulting to 1.0: %s", base, e)
            return 1.0

    def calculate_stop_loss(self, instrument: str, entry_price: float,
                            direction: str, df=None) -> float:
        """Calculate stop loss based on ATR or fixed pips."""
        from backend.data.provider import pip_value
        pip_val = pip_value(instrument)

        if self.sl_method == "atr" and df is not None and len(df) >= self.atr_period:
            tr = df["High"] - df["Low"]
            atr = tr.rolling(self.atr_period).mean().iloc[-1]
            distance = atr * self.atr_multiplier
        else:
            # Fixed pips fallback: 50 pips for forex, scaled for commodities
            if instrument.startswith("XAU"):
                distance = 15.0
            elif instrument.startswith(("BCO", "WTICO")):
                distance = 1.5
            elif "JPY" in instrument:
                distance = 0.50
            else:
                distance = 0.0050

        if direction == "long":
            return entry_price - distance
        else:
            return entry_price + distance

    def calculate_take_profit(self, entry_price: float, stop_loss: float,
                               direction: str) -> float:
        """TP = entry + RR * stop_distance."""
        distance = abs(entry_price - stop_loss) * self.default_rr
        if direction == "long":
            return entry_price + distance
        else:
            return entry_price - distance
