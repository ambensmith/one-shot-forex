"""Bollinger Mean Reversion — Pojarliev & Levich (2008).

Logic: When price reaches outer Bollinger Band and RSI shows divergence,
trade the reversal."""

from __future__ import annotations

import pandas as pd

from backend.strategies.base import Strategy, TechnicalSignal


class MeanReversionStrategy(Strategy):
    def __init__(self):
        self._bb_period = 20
        self._bb_std = 2.0
        self._rsi_period = 14
        self._rsi_oversold = 30
        self._rsi_overbought = 70

    @property
    def name(self) -> str:
        return "mean_reversion"

    @property
    def description(self) -> str:
        return "Bollinger Mean Reversion (Pojarliev 2008) — trades reversals at Bollinger Band extremes"

    def analyze(self, df: pd.DataFrame, instrument: str) -> TechnicalSignal:
        min_periods = max(self._bb_period, self._rsi_period) + 5
        if len(df) < min_periods:
            return TechnicalSignal(
                instrument=instrument, direction="neutral",
                confidence=0.0, strategy_name=self.name,
                metadata={"reason": "Insufficient data"},
            )

        close = df["Close"]
        current_price = close.iloc[-1]

        # Bollinger Bands
        sma = close.rolling(self._bb_period).mean()
        std = close.rolling(self._bb_period).std()
        upper_band = sma + self._bb_std * std
        lower_band = sma - self._bb_std * std

        bb_upper = upper_band.iloc[-1]
        bb_lower = lower_band.iloc[-1]
        bb_mid = sma.iloc[-1]

        # RSI
        rsi = self._calculate_rsi(close, self._rsi_period)
        current_rsi = rsi.iloc[-1]

        # %B (position within bands)
        bb_width = bb_upper - bb_lower
        if bb_width > 0:
            pct_b = (current_price - bb_lower) / bb_width
        else:
            pct_b = 0.5

        direction = "neutral"
        confidence = 0.0

        # Long signal: price at/below lower band + RSI oversold
        if current_price <= bb_lower and current_rsi <= self._rsi_oversold:
            direction = "long"
            bb_signal = max(0, 1 - pct_b)
            rsi_signal = max(0, (self._rsi_oversold - current_rsi) / self._rsi_oversold)
            confidence = (bb_signal * 0.5 + rsi_signal * 0.5)

        # Short signal: price at/above upper band + RSI overbought
        elif current_price >= bb_upper and current_rsi >= self._rsi_overbought:
            direction = "short"
            bb_signal = max(0, pct_b - 1)
            rsi_signal = max(0, (current_rsi - self._rsi_overbought) / (100 - self._rsi_overbought))
            confidence = (bb_signal * 0.5 + rsi_signal * 0.5)

        confidence = round(max(0.0, min(confidence, 1.0)), 3)

        return TechnicalSignal(
            instrument=instrument,
            direction=direction,
            confidence=confidence,
            strategy_name=self.name,
            entry_price=current_price,
            metadata={
                "bb_upper": round(bb_upper, 5),
                "bb_lower": round(bb_lower, 5),
                "bb_mid": round(bb_mid, 5),
                "rsi": round(current_rsi, 2),
                "pct_b": round(pct_b, 3),
            },
        )

    @staticmethod
    def _calculate_rsi(series: pd.Series, period: int) -> pd.Series:
        delta = series.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        avg_gain = gain.rolling(period, min_periods=period).mean()
        avg_loss = loss.rolling(period, min_periods=period).mean()
        rs = avg_gain / (avg_loss + 1e-10)
        return 100 - (100 / (1 + rs))

    def get_parameters(self) -> dict:
        return {
            "bb_period": self._bb_period,
            "bb_std": self._bb_std,
            "rsi_period": self._rsi_period,
            "rsi_oversold": self._rsi_oversold,
            "rsi_overbought": self._rsi_overbought,
        }

    def set_parameters(self, params: dict) -> None:
        for key in ("bb_period", "bb_std", "rsi_period", "rsi_oversold", "rsi_overbought"):
            if key in params:
                setattr(self, f"_{key}", params[key])
