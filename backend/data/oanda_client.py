"""OANDA v20 REST API client for candles, orders, and account info."""

from __future__ import annotations

import logging
import os
from typing import Any

import pandas as pd

logger = logging.getLogger("forex_sentinel.oanda")


class OandaClient:
    """Wraps OANDA v20 API. Fails gracefully when keys aren't configured."""

    def __init__(self, config: dict):
        self.api_key = os.environ.get("OANDA_API_KEY", "")
        self.account_id = os.environ.get("OANDA_ACCOUNT_ID", "")
        self.environment = config.get("execution", {}).get("oanda_environment", "practice")

        if self.environment == "live":
            self.base_url = "https://api-fxtrade.oanda.com"
        else:
            self.base_url = "https://api-fxpractice.oanda.com"

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        self._connected = False

        if self.api_key and self.account_id:
            try:
                self._test_connection()
                self._connected = True
            except Exception as e:
                logger.warning(f"OANDA connection failed: {e}. Running in offline mode.")
        else:
            logger.info("OANDA credentials not configured. Running in offline mode.")

    @property
    def is_connected(self) -> bool:
        return self._connected

    def _test_connection(self):
        import urllib.request
        import json
        url = f"{self.base_url}/v3/accounts/{self.account_id}/summary"
        req = urllib.request.Request(url, headers=self.headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            balance = data["account"]["balance"]
            logger.info(f"OANDA connected. Account balance: {balance}")

    def get_account_summary(self) -> dict[str, Any]:
        if not self._connected:
            return {"balance": 100000.0, "unrealizedPL": 0.0, "currency": "GBP", "openTradeCount": 0}
        import urllib.request
        import json
        url = f"{self.base_url}/v3/accounts/{self.account_id}/summary"
        req = urllib.request.Request(url, headers=self.headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            return data["account"]

    def get_candles(self, instrument: str, granularity: str = "H1",
                    count: int = 200) -> pd.DataFrame:
        """Fetch OHLCV candles. Returns DataFrame with columns: Open, High, Low, Close, Volume."""
        if not self._connected:
            return self._generate_dummy_candles(instrument, count)

        import urllib.request
        import json
        url = (
            f"{self.base_url}/v3/instruments/{instrument}/candles"
            f"?granularity={granularity}&count={count}&price=M"
        )
        req = urllib.request.Request(url, headers=self.headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())

        rows = []
        for candle in data.get("candles", []):
            if candle["complete"]:
                mid = candle["mid"]
                rows.append({
                    "time": candle["time"],
                    "Open": float(mid["o"]),
                    "High": float(mid["h"]),
                    "Low": float(mid["l"]),
                    "Close": float(mid["c"]),
                    "Volume": int(candle["volume"]),
                })

        if not rows:
            return self._generate_dummy_candles(instrument, count)

        df = pd.DataFrame(rows)
        df["time"] = pd.to_datetime(df["time"])
        df.set_index("time", inplace=True)
        return df

    def get_current_price(self, instrument: str) -> dict[str, float]:
        """Get current bid/ask/mid price."""
        if not self._connected:
            return {"bid": 1.0800, "ask": 1.0802, "mid": 1.0801}

        import urllib.request
        import json
        url = f"{self.base_url}/v3/accounts/{self.account_id}/pricing?instruments={instrument}"
        req = urllib.request.Request(url, headers=self.headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            price = data["prices"][0]
            bid = float(price["bids"][0]["price"])
            ask = float(price["asks"][0]["price"])
            return {"bid": bid, "ask": ask, "mid": (bid + ask) / 2}

    def place_order(self, instrument: str, units: float, side: str,
                    stop_loss: float, take_profit: float) -> dict[str, Any]:
        """Place a market order. units is positive for buy, negative for sell."""
        if not self._connected:
            logger.info(f"[OFFLINE] Would place {side} {abs(units)} {instrument} SL={stop_loss} TP={take_profit}")
            return {"id": "offline-" + instrument, "status": "simulated"}

        import urllib.request
        import json

        actual_units = abs(units) if side == "long" else -abs(units)
        order_body = {
            "order": {
                "type": "MARKET",
                "instrument": instrument,
                "units": str(int(actual_units)),
                "stopLossOnFill": {"price": f"{stop_loss:.5f}"},
                "takeProfitOnFill": {"price": f"{take_profit:.5f}"},
                "timeInForce": "FOK",
            }
        }

        url = f"{self.base_url}/v3/accounts/{self.account_id}/orders"
        data_bytes = json.dumps(order_body).encode()
        req = urllib.request.Request(url, data=data_bytes, headers=self.headers, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            logger.info(f"Order placed: {side} {abs(units)} {instrument}")
            return result

    def get_open_trades(self) -> list[dict]:
        """Get all open trades from OANDA."""
        if not self._connected:
            return []
        import urllib.request
        import json
        url = f"{self.base_url}/v3/accounts/{self.account_id}/openTrades"
        req = urllib.request.Request(url, headers=self.headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            return data.get("trades", [])

    def close_trade(self, trade_id: str) -> dict:
        """Close a specific trade."""
        if not self._connected:
            logger.info(f"[OFFLINE] Would close trade {trade_id}")
            return {"status": "simulated"}
        import urllib.request
        import json
        url = f"{self.base_url}/v3/accounts/{self.account_id}/trades/{trade_id}/close"
        req = urllib.request.Request(url, data=b'{"units": "ALL"}', headers=self.headers, method="PUT")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())

    @staticmethod
    def _generate_dummy_candles(instrument: str, count: int) -> pd.DataFrame:
        """Generate realistic dummy data for offline mode."""
        import numpy as np
        from datetime import datetime, timedelta, timezone

        # Base prices per instrument type
        base_prices = {
            "EUR_USD": 1.0800, "GBP_USD": 1.2650, "USD_JPY": 150.50,
            "USD_CHF": 0.8800, "AUD_USD": 0.6550, "USD_CAD": 1.3600,
            "NZD_USD": 0.6100, "XAU_USD": 2350.0, "XAG_USD": 28.50,
            "BCO_USD": 82.50, "WTICO_USD": 78.50, "NATGAS_USD": 2.80,
            "EUR_GBP": 0.8540, "EUR_JPY": 162.50, "GBP_JPY": 190.30,
        }
        base = base_prices.get(instrument, 1.0)
        volatility = base * 0.001

        np.random.seed(hash(instrument) % 2**31)
        returns = np.random.normal(0, volatility, count)
        prices = [base]
        for r in returns[1:]:
            prices.append(prices[-1] + r)

        now = datetime.now(timezone.utc)
        times = [now - timedelta(hours=count - i) for i in range(count)]

        rows = []
        for i, t in enumerate(times):
            p = prices[i]
            h = p + abs(np.random.normal(0, volatility * 0.5))
            l = p - abs(np.random.normal(0, volatility * 0.5))
            o = p + np.random.normal(0, volatility * 0.3)
            rows.append({
                "Open": o, "High": max(o, h, p), "Low": min(o, l, p),
                "Close": p, "Volume": int(np.random.randint(100, 5000)),
            })

        df = pd.DataFrame(rows, index=pd.DatetimeIndex(times, name="time"))
        return df

    @staticmethod
    def pip_value(instrument: str) -> float:
        """Return the pip size for an instrument."""
        if "JPY" in instrument:
            return 0.01
        if instrument.startswith("XAU"):
            return 0.1
        if instrument.startswith("XAG"):
            return 0.01
        if "NATGAS" in instrument:
            return 0.001
        if instrument.startswith(("BCO", "WTICO")):
            return 0.01
        return 0.0001
