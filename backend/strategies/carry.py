"""Carry Trade — Menkhoff, Sarno, Schmeling & Schrimpf (2012).

Logic: Buy currencies with higher interest rates, sell those with lower rates.
Uses manually configured central bank rate differentials."""

from __future__ import annotations

import pandas as pd

from backend.strategies.base import Strategy, TechnicalSignal

# Approximate central bank rates (updated periodically)
CENTRAL_BANK_RATES = {
    "USD": 5.25,
    "EUR": 4.50,
    "GBP": 5.25,
    "JPY": 0.10,
    "CHF": 1.75,
    "AUD": 4.35,
    "CAD": 5.00,
    "NZD": 5.50,
}


class CarryStrategy(Strategy):
    def __init__(self):
        self._rate_data = "manual"
        self._min_differential = 0.5  # Min rate diff to trigger

    @property
    def name(self) -> str:
        return "carry"

    @property
    def description(self) -> str:
        return "Carry Trade (Menkhoff 2012) — long high-yield, short low-yield currencies"

    def analyze(self, df: pd.DataFrame, instrument: str) -> TechnicalSignal:
        # Parse currency pair
        parts = instrument.split("_")
        if len(parts) != 2:
            return TechnicalSignal(
                instrument=instrument, direction="neutral",
                confidence=0.0, strategy_name=self.name,
                metadata={"reason": "Cannot parse pair"},
            )

        base, quote = parts[0], parts[1]

        # Get rates (handle commodities)
        base_rate = CENTRAL_BANK_RATES.get(base)
        quote_rate = CENTRAL_BANK_RATES.get(quote)

        if base_rate is None or quote_rate is None:
            return TechnicalSignal(
                instrument=instrument, direction="neutral",
                confidence=0.0, strategy_name=self.name,
                metadata={"reason": f"No rate data for {base} or {quote}"},
            )

        differential = base_rate - quote_rate

        # Volatility check — avoid carry in high-vol environments
        if len(df) >= 20:
            recent_vol = df["Close"].pct_change().rolling(20).std().iloc[-1]
            vol_penalty = min(recent_vol * 50, 0.5)  # High vol reduces confidence
        else:
            vol_penalty = 0.0

        # Confidence based on differential magnitude
        confidence = min(abs(differential) / 5.0, 1.0) - vol_penalty
        confidence = max(0.0, round(confidence, 3))

        if differential > self._min_differential:
            direction = "long"  # Buy base (higher rate)
        elif differential < -self._min_differential:
            direction = "short"  # Sell base (lower rate)
        else:
            direction = "neutral"
            confidence = 0.0

        entry = df["Close"].iloc[-1] if len(df) > 0 else None

        return TechnicalSignal(
            instrument=instrument,
            direction=direction,
            confidence=confidence,
            strategy_name=self.name,
            entry_price=entry,
            metadata={
                "base_rate": base_rate,
                "quote_rate": quote_rate,
                "differential": round(differential, 2),
                "vol_penalty": round(vol_penalty, 3),
            },
        )

    def get_parameters(self) -> dict:
        return {
            "rate_data": self._rate_data,
            "min_differential": self._min_differential,
            "rates": CENTRAL_BANK_RATES.copy(),
        }

    def set_parameters(self, params: dict) -> None:
        if "rate_data" in params:
            self._rate_data = params["rate_data"]
        if "min_differential" in params:
            self._min_differential = params["min_differential"]
