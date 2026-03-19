"""Backtesting engine for strategies."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd

logger = logging.getLogger("forex_sentinel.backtest")


@dataclass
class BacktestTrade:
    instrument: str
    direction: str
    entry_price: float
    exit_price: float
    entry_time: datetime
    exit_time: datetime
    pnl: float
    pnl_pips: float


@dataclass
class BacktestResult:
    strategy_name: str
    instrument: str
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    total_trades: int
    trades: list[BacktestTrade] = field(default_factory=list)
    equity_curve: list[float] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"Strategy: {self.strategy_name} | Instrument: {self.instrument}\n"
            f"  Return: {self.total_return:.2%} | Sharpe: {self.sharpe_ratio:.2f}\n"
            f"  Max DD: {self.max_drawdown:.2%} | Win Rate: {self.win_rate:.1%}\n"
            f"  Total Trades: {self.total_trades}"
        )


class BacktestEngine:
    """Walk-forward backtester for strategies."""

    def __init__(self, initial_capital: float = 100.0,
                 risk_per_trade: float = 0.01, rr_ratio: float = 1.5):
        self.initial_capital = initial_capital
        self.risk_per_trade = risk_per_trade
        self.rr_ratio = rr_ratio

    def run(self, strategy, df: pd.DataFrame, instrument: str) -> BacktestResult:
        """Run backtest on historical data."""
        from backend.data.provider import pip_value
        pip_val = pip_value(instrument)

        trades: list[BacktestTrade] = []
        equity = self.initial_capital
        equity_curve = [equity]
        peak_equity = equity

        # Walk forward through data
        min_lookback = 50
        position = None  # Current position dict

        for i in range(min_lookback, len(df)):
            window = df.iloc[:i + 1]
            current_price = df["Close"].iloc[i]
            current_time = df.index[i]

            # Check open position for SL/TP
            if position is not None:
                high = df["High"].iloc[i]
                low = df["Low"].iloc[i]
                closed = False

                if position["direction"] == "long":
                    if low <= position["stop_loss"]:
                        exit_price = position["stop_loss"]
                        closed = True
                    elif high >= position["take_profit"]:
                        exit_price = position["take_profit"]
                        closed = True
                else:
                    if high >= position["stop_loss"]:
                        exit_price = position["stop_loss"]
                        closed = True
                    elif low <= position["take_profit"]:
                        exit_price = position["take_profit"]
                        closed = True

                if closed:
                    if position["direction"] == "long":
                        pnl_pips = (exit_price - position["entry_price"]) / pip_val
                    else:
                        pnl_pips = (position["entry_price"] - exit_price) / pip_val
                    pnl = pnl_pips * pip_val * position["size"]
                    equity += pnl

                    trades.append(BacktestTrade(
                        instrument=instrument,
                        direction=position["direction"],
                        entry_price=position["entry_price"],
                        exit_price=exit_price,
                        entry_time=position["entry_time"],
                        exit_time=current_time,
                        pnl=pnl,
                        pnl_pips=pnl_pips,
                    ))
                    position = None

            # Generate signal if no position
            if position is None:
                signal = strategy.analyze(window, instrument)
                if signal.direction in ("long", "short") and signal.confidence >= 0.5:
                    entry_price = current_price

                    # ATR-based stop loss
                    tr = window["High"] - window["Low"]
                    atr = tr.rolling(14).mean().iloc[-1] if len(tr) >= 14 else tr.mean()
                    sl_distance = atr * 1.5

                    if signal.direction == "long":
                        sl = entry_price - sl_distance
                        tp = entry_price + sl_distance * self.rr_ratio
                    else:
                        sl = entry_price + sl_distance
                        tp = entry_price - sl_distance * self.rr_ratio

                    # Position sizing
                    risk_amount = equity * self.risk_per_trade
                    if sl_distance > 0:
                        size = risk_amount / sl_distance
                    else:
                        size = 0

                    if size > 0:
                        position = {
                            "direction": signal.direction,
                            "entry_price": entry_price,
                            "stop_loss": sl,
                            "take_profit": tp,
                            "size": size,
                            "entry_time": current_time,
                        }

            equity_curve.append(equity)
            peak_equity = max(peak_equity, equity)

        # Calculate metrics
        total_return = (equity - self.initial_capital) / self.initial_capital
        wins = sum(1 for t in trades if t.pnl > 0)
        win_rate = wins / len(trades) if trades else 0

        # Sharpe ratio
        if len(equity_curve) > 1:
            returns = pd.Series(equity_curve).pct_change().dropna()
            sharpe = (returns.mean() / (returns.std() + 1e-10)) * (252 ** 0.5)
        else:
            sharpe = 0.0

        # Max drawdown
        eq_series = pd.Series(equity_curve)
        peaks = eq_series.cummax()
        drawdowns = (eq_series - peaks) / (peaks + 1e-10)
        max_dd = drawdowns.min()

        return BacktestResult(
            strategy_name=strategy.name,
            instrument=instrument,
            total_return=total_return,
            sharpe_ratio=round(sharpe, 2),
            max_drawdown=round(max_dd, 4),
            win_rate=win_rate,
            total_trades=len(trades),
            trades=trades,
            equity_curve=equity_curve,
        )
