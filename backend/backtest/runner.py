"""CLI backtest execution."""

from __future__ import annotations

import logging

logger = logging.getLogger("forex_sentinel.backtest")


def run_backtest(strategy_name: str | None = None, instrument: str | None = None):
    """Run backtest for a strategy on an instrument."""
    from backend.core.config import load_config
    from backend.main import create_data_provider
    from backend.strategies.registry import get_strategy
    from backend.backtest.engine import BacktestEngine
    from backend.backtest.data_loader import load_historical_data

    config = load_config()
    broker = create_data_provider(config)

    strategies_cfg = config.get("streams", {}).get("strategy_stream", {}).get("strategies", [])
    instruments_cfg = config.get("streams", {}).get("strategy_stream", {}).get("instruments", [])

    # Filter to requested strategy/instrument
    if strategy_name:
        strategies_to_test = [s for s in strategies_cfg if s["name"] == strategy_name]
        if not strategies_to_test:
            print(f"Strategy '{strategy_name}' not found in config.")
            return
    else:
        strategies_to_test = [s for s in strategies_cfg if s.get("enabled", True)]

    if instrument:
        instruments_to_test = [instrument]
    else:
        instruments_to_test = instruments_cfg

    engine = BacktestEngine()

    print("=" * 60)
    print("FOREX SENTINEL — BACKTEST")
    print("=" * 60)

    for strat_cfg in strategies_to_test:
        strategy = get_strategy(strat_cfg["name"], strat_cfg.get("params"))
        print(f"\nStrategy: {strategy.name} — {strategy.description}")
        print("-" * 60)

        for inst in instruments_to_test:
            df = load_historical_data(broker, inst, count=2000)
            if df.empty or len(df) < 100:
                print(f"  {inst}: Insufficient data ({len(df)} candles)")
                continue

            result = engine.run(strategy, df, inst)
            print(f"  {result.summary()}")

    print("\n" + "=" * 60)
    print("Backtest complete.")
