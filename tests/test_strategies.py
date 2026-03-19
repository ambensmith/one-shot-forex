"""Tests for trading strategies."""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone

from backend.strategies.registry import discover_strategies, get_strategy
from backend.strategies.base import TechnicalSignal


def _make_df(count=200, base_price=1.08, volatility=0.001):
    """Generate test OHLCV DataFrame."""
    np.random.seed(42)
    times = [datetime.now(timezone.utc) - timedelta(hours=count - i) for i in range(count)]
    prices = [base_price]
    for _ in range(count - 1):
        prices.append(prices[-1] + np.random.normal(0, volatility))

    data = []
    for i, p in enumerate(prices):
        h = p + abs(np.random.normal(0, volatility * 0.5))
        l = p - abs(np.random.normal(0, volatility * 0.5))
        data.append({
            "Open": p + np.random.normal(0, volatility * 0.3),
            "High": max(p, h),
            "Low": min(p, l),
            "Close": p,
            "Volume": np.random.randint(100, 5000),
        })
    return pd.DataFrame(data, index=pd.DatetimeIndex(times, name="time"))


def test_strategy_discovery():
    strategies = discover_strategies()
    assert len(strategies) == 5
    assert "momentum" in strategies
    assert "carry" in strategies
    assert "breakout" in strategies
    assert "mean_reversion" in strategies
    assert "volatility_breakout" in strategies


def test_momentum_signal():
    strat = get_strategy("momentum")
    df = _make_df()
    signal = strat.analyze(df, "EUR_USD")
    assert isinstance(signal, TechnicalSignal)
    assert signal.direction in ("long", "short", "neutral")
    assert 0 <= signal.confidence <= 1


def test_carry_signal():
    strat = get_strategy("carry")
    df = _make_df()
    signal = strat.analyze(df, "EUR_USD")
    assert isinstance(signal, TechnicalSignal)
    assert signal.direction in ("long", "short", "neutral")


def test_breakout_signal():
    strat = get_strategy("breakout")
    df = _make_df()
    signal = strat.analyze(df, "EUR_USD")
    assert isinstance(signal, TechnicalSignal)
    assert signal.direction in ("long", "short", "neutral")


def test_mean_reversion_signal():
    strat = get_strategy("mean_reversion")
    df = _make_df()
    signal = strat.analyze(df, "EUR_USD")
    assert isinstance(signal, TechnicalSignal)
    assert signal.direction in ("long", "short", "neutral")


def test_volatility_breakout_signal():
    strat = get_strategy("volatility_breakout")
    df = _make_df()
    signal = strat.analyze(df, "EUR_USD")
    assert isinstance(signal, TechnicalSignal)
    assert signal.direction in ("long", "short", "neutral")


def test_strategy_parameters():
    strat = get_strategy("momentum")
    params = strat.get_parameters()
    assert "lookback_months" in params
    strat.set_parameters({"lookback_months": 6})
    assert strat.get_parameters()["lookback_months"] == 6


def test_carry_commodity():
    """Carry strategy should return neutral for commodities (no rate data)."""
    strat = get_strategy("carry")
    df = _make_df(base_price=2350)
    signal = strat.analyze(df, "XAU_USD")
    assert signal.direction == "neutral"


def test_insufficient_data():
    strat = get_strategy("mean_reversion")
    df = _make_df(count=5)  # Too few candles
    signal = strat.analyze(df, "EUR_USD")
    assert signal.direction == "neutral"
