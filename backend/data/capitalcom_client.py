"""Capital.com REST API client — candles, orders, and account info."""

from __future__ import annotations

import json
import logging
import os
import urllib.request
import urllib.error
from typing import Any

import pandas as pd

logger = logging.getLogger("forex_sentinel.capitalcom")

# Map instrument symbols to Capital.com epics
# Forex pairs: strip underscores. Commodities: use Capital.com-specific names.
INSTRUMENT_TO_EPIC = {
    "EUR_USD": "EURUSD",
    "GBP_USD": "GBPUSD",
    "USD_JPY": "USDJPY",
    "USD_CHF": "USDCHF",
    "AUD_USD": "AUDUSD",
    "USD_CAD": "USDCAD",
    "NZD_USD": "NZDUSD",
    "EUR_GBP": "EURGBP",
    "EUR_JPY": "EURJPY",
    "GBP_JPY": "GBPJPY",
    "XAU_USD": "GOLD",
    "XAG_USD": "SILVER",
    "BCO_USD": "OIL_CRUDE",
    "WTICO_USD": "OIL_CRUDE",
    "NATGAS_USD": "NATURALGAS",
}

# Reverse mapping — when multiple instruments share an epic (e.g. BCO_USD and
# WTICO_USD both map to OIL_CRUDE), prefer the one used in streams config.
EPIC_TO_INSTRUMENT: dict[str, str] = {v: k for k, v in INSTRUMENT_TO_EPIC.items()}
EPIC_TO_INSTRUMENT["OIL_CRUDE"] = "BCO_USD"  # prefer BCO_USD (Brent) over WTICO_USD

# Granularity mapping
GRANULARITY_MAP = {
    "M1": "MINUTE",
    "M5": "MINUTE_5",
    "M15": "MINUTE_15",
    "M30": "MINUTE_30",
    "H1": "HOUR",
    "H4": "HOUR_4",
    "D": "DAY",
    "W": "WEEK",
}


class CapitalComClient:
    """Capital.com REST API client.

    Uses the demo environment by default. Falls back to offline mode
    if credentials are not configured.
    """

    # Base prices for offline simulation
    BASE_PRICES = {
        "EUR_USD": 1.0800, "GBP_USD": 1.2650, "USD_JPY": 150.50,
        "USD_CHF": 0.8800, "AUD_USD": 0.6550, "USD_CAD": 1.3600,
        "NZD_USD": 0.6100, "XAU_USD": 2350.0, "XAG_USD": 28.50,
        "BCO_USD": 82.50, "WTICO_USD": 78.50, "NATGAS_USD": 2.80,
        "EUR_GBP": 0.8540, "EUR_JPY": 162.50, "GBP_JPY": 190.30,
    }

    def __init__(self, config: dict):
        self.api_key = os.environ.get("CAPITALCOM_API_KEY", "")
        self.email = os.environ.get("CAPITALCOM_EMAIL", "")
        self.password = os.environ.get("CAPITALCOM_PASSWORD", "")
        self.base_url = "https://demo-api-capital.backend-capital.com"

        self._cst = ""
        self._security_token = ""
        self._connected = False

        if self.api_key and self.email and self.password:
            try:
                self._create_session()
                self._connected = True
            except Exception as e:
                logger.warning(f"Capital.com connection failed: {e}. Running in offline mode.")
        else:
            logger.info("Capital.com credentials not configured. Running in offline mode.")

    @property
    def is_connected(self) -> bool:
        return self._connected

    # ── Session management ─────────────────────────────────────────

    def _create_session(self):
        """Authenticate and store CST + X-SECURITY-TOKEN."""
        body = json.dumps({
            "identifier": self.email,
            "password": self.password,
        }).encode()
        req = urllib.request.Request(
            f"{self.base_url}/api/v1/session",
            data=body,
            headers={
                "X-CAP-API-KEY": self.api_key,
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            self._cst = resp.headers.get("CST", "")
            self._security_token = resp.headers.get("X-SECURITY-TOKEN", "")
            logger.info("Capital.com session created successfully.")

    def _auth_headers(self) -> dict[str, str]:
        return {
            "X-SECURITY-TOKEN": self._security_token,
            "CST": self._cst,
            "Content-Type": "application/json",
        }

    def _request(self, method: str, path: str, body: dict | None = None) -> dict:
        """Make an authenticated API request with auto-retry on session expiry."""
        url = f"{self.base_url}{path}"
        data = json.dumps(body).encode() if body else None
        req = urllib.request.Request(url, data=data, headers=self._auth_headers(), method=method)

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = resp.read()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            if e.code == 401:
                # Session expired — refresh and retry once
                logger.info("Capital.com session expired, refreshing...")
                self._create_session()
                req = urllib.request.Request(url, data=data, headers=self._auth_headers(), method=method)
                with urllib.request.urlopen(req, timeout=15) as resp:
                    raw = resp.read()
                    return json.loads(raw) if raw else {}
            raise

    def _to_epic(self, instrument: str) -> str:
        """Convert instrument symbol to Capital.com epic."""
        epic = INSTRUMENT_TO_EPIC.get(instrument)
        if epic:
            return epic
        # Fallback: strip underscores
        return instrument.replace("_", "")

    # ── DataProvider interface ─────────────────────────────────────

    def get_account_summary(self) -> dict[str, Any]:
        if not self._connected:
            return {"balance": 100000.0, "unrealizedPL": 0.0, "currency": "EUR", "openTradeCount": 0}

        data = self._request("GET", "/api/v1/accounts")
        accounts = data.get("accounts", [])
        if not accounts:
            return {"balance": 100000.0, "unrealizedPL": 0.0, "currency": "EUR", "openTradeCount": 0}

        # Use the preferred account, or the first one
        acct = next((a for a in accounts if a.get("preferred")), accounts[0])
        balance_info = acct.get("balance", {})
        return {
            "balance": float(balance_info.get("balance", 0)),
            "unrealizedPL": float(balance_info.get("profitLoss", 0)),
            "currency": acct.get("currency", "EUR"),
            "openTradeCount": 0,  # Not directly available; positions endpoint needed
        }

    def get_candles(self, instrument: str, granularity: str = "H1",
                    count: int = 200) -> pd.DataFrame:
        """Fetch OHLCV candles. Returns DataFrame with columns: Open, High, Low, Close, Volume."""
        if not self._connected:
            return self._generate_dummy_candles(instrument, count)

        epic = self._to_epic(instrument)
        resolution = GRANULARITY_MAP.get(granularity, "HOUR")

        try:
            data = self._request(
                "GET",
                f"/api/v1/prices/{epic}?resolution={resolution}&max={count}",
            )
        except Exception as e:
            logger.warning(f"Failed to fetch candles for {instrument}: {e}")
            return self._generate_dummy_candles(instrument, count)

        prices = data.get("prices", [])
        if not prices:
            return self._generate_dummy_candles(instrument, count)

        rows = []
        for candle in prices:
            # Capital.com returns bid/ask for each OHLC — use mid prices
            o = (candle["openPrice"]["bid"] + candle["openPrice"]["ask"]) / 2
            h = (candle["highPrice"]["bid"] + candle["highPrice"]["ask"]) / 2
            l = (candle["lowPrice"]["bid"] + candle["lowPrice"]["ask"]) / 2
            c = (candle["closePrice"]["bid"] + candle["closePrice"]["ask"]) / 2
            rows.append({
                "time": candle.get("snapshotTimeUTC", candle.get("snapshotTime")),
                "Open": o,
                "High": h,
                "Low": l,
                "Close": c,
                "Volume": int(candle.get("lastTradedVolume", 0)),
            })

        df = pd.DataFrame(rows)
        df["time"] = pd.to_datetime(df["time"])
        df.set_index("time", inplace=True)
        return df

    def get_current_price(self, instrument: str) -> dict[str, float]:
        """Get current bid/ask/mid price via the markets endpoint."""
        if not self._connected:
            import random
            base = self.BASE_PRICES.get(instrument, 1.0)
            spread = base * 0.0002
            jitter = base * random.uniform(-0.001, 0.001)
            mid = base + jitter
            return {"bid": mid - spread / 2, "ask": mid + spread / 2, "mid": mid}

        epic = self._to_epic(instrument)
        try:
            data = self._request("GET", f"/api/v1/markets/{epic}")
            snapshot = data.get("snapshot", {})
            bid = float(snapshot.get("bid", 0))
            ask = float(snapshot.get("offer", 0))
            return {"bid": bid, "ask": ask, "mid": (bid + ask) / 2}
        except Exception as e:
            logger.warning(f"Failed to get price for {instrument}: {e}")
            base = self.BASE_PRICES.get(instrument, 1.0)
            return {"bid": base, "ask": base, "mid": base}

    def place_order(self, instrument: str, units: float, side: str,
                    stop_loss: float, take_profit: float) -> dict[str, Any]:
        """Place a market order via Capital.com positions endpoint."""
        if not self._connected:
            logger.info(f"[OFFLINE] Would place {side} {abs(units)} {instrument} SL={stop_loss} TP={take_profit}")
            return {"id": "offline-" + instrument, "status": "simulated"}

        epic = self._to_epic(instrument)
        direction = "BUY" if side == "long" else "SELL"
        body = {
            "epic": epic,
            "direction": direction,
            "size": abs(units),
            "stopLevel": stop_loss,
            "profitLevel": take_profit,
            "guaranteedStop": False,
        }

        # Place the order — if this succeeds, the position is live on the broker
        try:
            result = self._request("POST", "/api/v1/positions", body)
            deal_ref = result.get("dealReference", "")
            logger.info(f"Order placed: {side} {abs(units)} {instrument} dealRef={deal_ref}")
        except Exception as e:
            logger.error(f"Order failed for {instrument}: {e}")
            return {"id": "", "status": "REJECTED", "error": str(e)}

        # Confirm the deal — if this fails, we still return ACCEPTED since
        # the position was already created on the broker
        if deal_ref:
            try:
                confirm = self._request("GET", f"/api/v1/confirms/{deal_ref}")
                return {
                    "id": confirm.get("dealId", deal_ref),
                    "status": confirm.get("dealStatus", "UNKNOWN"),
                    "dealReference": deal_ref,
                }
            except Exception as e:
                logger.warning(
                    f"Order confirm failed for {instrument} dealRef={deal_ref}: {e}. "
                    f"Position likely exists on broker — recording with dealRef as ID."
                )
                return {"id": deal_ref, "status": "ACCEPTED", "dealReference": deal_ref}
        return {"id": deal_ref, "status": "ACCEPTED", "dealReference": deal_ref}

    def get_open_trades(self) -> list[dict]:
        """Get all open positions from Capital.com."""
        if not self._connected:
            return []

        try:
            data = self._request("GET", "/api/v1/positions")
            positions = data.get("positions", [])
            trades = []
            for pos in positions:
                position = pos.get("position", {})
                market = pos.get("market", {})
                trades.append({
                    "id": position.get("dealId", ""),
                    "instrument": EPIC_TO_INSTRUMENT.get(
                        market.get("epic", ""), market.get("epic", "")
                    ),
                    "currentUnits": str(position.get("size", 0)),
                    "unrealizedPL": str(position.get("upl", 0)),
                    "direction": "long" if position.get("direction") == "BUY" else "short",
                    "entry_price": position.get("level"),
                    "stop_loss": position.get("stopLevel"),
                    "take_profit": position.get("profitLevel"),
                })
            return trades
        except Exception as e:
            logger.warning(f"Failed to get open trades: {e}")
            return []

    def get_deal_activity(self, deal_id: str) -> dict | None:
        """Fetch activity details for a specific deal from Capital.com."""
        if not self._connected:
            return None
        try:
            data = self._request("GET", f"/api/v1/history/activity?dealId={deal_id}")
            activities = data.get("activities", [])
            return activities[0] if activities else None
        except Exception as e:
            logger.warning(f"Failed to fetch deal activity for {deal_id}: {e}")
            return None

    def close_trade(self, trade_id: str) -> dict:
        """Close a specific position by dealId."""
        if not self._connected:
            logger.info(f"[OFFLINE] Would close trade {trade_id}")
            return {"status": "simulated"}

        try:
            result = self._request("DELETE", f"/api/v1/positions/{trade_id}")
            deal_ref = result.get("dealReference", "")
            logger.info(f"Trade {trade_id} closed. dealRef={deal_ref}")
            return {"status": "closed", "dealReference": deal_ref}
        except Exception as e:
            logger.warning(f"Failed to close trade {trade_id}: {e}")
            return {"status": "error", "error": str(e)}

    @staticmethod
    def pip_value(instrument: str) -> float:
        """Return the pip size for an instrument."""
        if "JPY" in instrument:
            return 0.01
        if instrument.startswith("XAU") or instrument == "GOLD":
            return 0.1
        if instrument.startswith("XAG") or instrument == "SILVER":
            return 0.01
        if "NATGAS" in instrument or instrument == "NATURALGAS":
            return 0.001
        if instrument.startswith(("BCO", "WTICO")) or instrument == "OIL_CRUDE":
            return 0.01
        return 0.0001

    # ── Offline fallback ───────────────────────────────────────────

    @staticmethod
    def _generate_dummy_candles(instrument: str, count: int) -> pd.DataFrame:
        """Generate realistic dummy data for offline mode."""
        import numpy as np
        from datetime import datetime, timedelta, timezone

        base = CapitalComClient.BASE_PRICES.get(instrument, 1.0)
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
