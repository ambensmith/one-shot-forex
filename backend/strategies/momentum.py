"""Time Series Momentum — Moskowitz, Ooi & Pedersen (2012).

Logic: Calculate returns over past lookback period. If positive, go long.
If negative, go short. Confidence scales with magnitude of return."""

from __future__ import annotations

import pandas as pd

from backend.strategies.base import Strategy, TechnicalSignal


class MomentumStrategy(Strategy):
    def __init__(self):
        self._lookback_months = 12
        self._rebalance_frequency = "weekly"

    @property
    def name(self) -> str:
        return "momentum"

    @property
    def description(self) -> str:
        return "Time Series Momentum (Moskowitz 2012) — trades in the direction of recent returns"

    def analyze(self, df: pd.DataFrame, instrument: str) -> TechnicalSignal:
        if len(df) < 20:
            return TechnicalSignal(
                instrument=instrument, direction="neutral",
                confidence=0.0, strategy_name=self.name,
                metadata={"reason": "Insufficient data"},
            )

        # Use available data (up to lookback months * ~22 trading days)
        lookback_periods = min(len(df), self._lookback_months * 22)
        returns = (df["Close"].iloc[-1] / df["Close"].iloc[-lookback_periods]) - 1

        # Shorter-term momentum (1 month)
        short_periods = min(len(df), 22)
        short_returns = (df["Close"].iloc[-1] / df["Close"].iloc[-short_periods]) - 1

        # Combined signal: weight longer-term more
        combined = returns * 0.6 + short_returns * 0.4

        # Confidence based on magnitude (capped at 1.0)
        confidence = min(abs(combined) * 10, 1.0)

        if combined > 0.001:
            direction = "long"
        elif combined < -0.001:
            direction = "short"
        else:
            direction = "neutral"
            confidence = 0.0

        entry = df["Close"].iloc[-1]

        return TechnicalSignal(
            instrument=instrument,
            direction=direction,
            confidence=round(confidence, 3),
            strategy_name=self.name,
            entry_price=entry,
            metadata={
                "lookback_return": round(returns, 5),
                "short_return": round(short_returns, 5),
                "combined_signal": round(combined, 5),
            },
        )

    def get_parameters(self) -> dict:
        return {
            "lookback_months": self._lookback_months,
            "rebalance_frequency": self._rebalance_frequency,
        }

    def set_parameters(self, params: dict) -> None:
        if "lookback_months" in params:
            self._lookback_months = params["lookback_months"]
        if "rebalance_frequency" in params:
            self._rebalance_frequency = params["rebalance_frequency"]
