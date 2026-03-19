"""Historical data loader with parquet caching."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger("forex_sentinel.backtest.data")

CACHE_DIR = Path("data/cache")


def load_historical_data(oanda, instrument: str, granularity: str = "H1",
                          count: int = 5000) -> pd.DataFrame:
    """Load historical data, using parquet cache when available."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / f"{instrument}_{granularity}_{count}.parquet"

    if cache_file.exists():
        logger.info(f"Loading cached data: {cache_file}")
        return pd.read_parquet(cache_file)

    logger.info(f"Fetching {count} {granularity} candles for {instrument}")
    df = oanda.get_candles(instrument, granularity=granularity, count=count)

    if not df.empty:
        df.to_parquet(cache_file)
        logger.info(f"Cached to {cache_file}")

    return df
