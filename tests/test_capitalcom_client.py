"""Tests for Capital.com API client."""

import json
from unittest.mock import patch, MagicMock

from backend.data.capitalcom_client import (
    CapitalComClient,
    INSTRUMENT_TO_EPIC,
    GRANULARITY_MAP,
)


def _offline_client():
    """Create a client with no credentials (offline mode)."""
    return CapitalComClient({})


# ── Offline mode tests ────────────────────────────────────────────


def test_offline_mode_no_credentials():
    client = _offline_client()
    assert not client.is_connected


def test_offline_account_summary():
    client = _offline_client()
    summary = client.get_account_summary()
    assert summary["balance"] == 100000.0
    assert "unrealizedPL" in summary
    assert "currency" in summary


def test_offline_candles():
    client = _offline_client()
    df = client.get_candles("EUR_USD", "H1", 50)
    assert len(df) == 50
    assert list(df.columns) == ["Open", "High", "Low", "Close", "Volume"]
    assert df.index.name == "time"


def test_offline_current_price():
    client = _offline_client()
    price = client.get_current_price("EUR_USD")
    assert "bid" in price
    assert "ask" in price
    assert "mid" in price
    assert price["bid"] < price["ask"]


def test_offline_place_order():
    client = _offline_client()
    result = client.place_order("EUR_USD", 1000, "long", 1.0750, 1.0900)
    assert result["status"] == "simulated"


def test_offline_open_trades():
    client = _offline_client()
    assert client.get_open_trades() == []


def test_offline_close_trade():
    client = _offline_client()
    result = client.close_trade("some-id")
    assert result["status"] == "simulated"


# ── Instrument mapping tests ─────────────────────────────────────


def test_instrument_mapping():
    client = _offline_client()
    assert client._to_epic("EUR_USD") == "EURUSD"
    assert client._to_epic("XAU_USD") == "GOLD"
    assert client._to_epic("BCO_USD") == "OIL_CRUDE"
    assert client._to_epic("NATGAS_USD") == "NATURALGAS"
    assert client._to_epic("XAG_USD") == "SILVER"


def test_instrument_mapping_fallback():
    client = _offline_client()
    # Unknown instrument should strip underscores
    assert client._to_epic("FOO_BAR") == "FOOBAR"


def test_all_instruments_mapped():
    """Every instrument used in the system should have a mapping."""
    expected = [
        "EUR_USD", "GBP_USD", "USD_JPY", "USD_CHF", "AUD_USD",
        "USD_CAD", "NZD_USD", "EUR_GBP", "EUR_JPY", "GBP_JPY",
        "XAU_USD", "XAG_USD", "BCO_USD", "WTICO_USD", "NATGAS_USD",
    ]
    for inst in expected:
        assert inst in INSTRUMENT_TO_EPIC


# ── Granularity mapping tests ────────────────────────────────────


def test_granularity_mapping():
    assert GRANULARITY_MAP["H1"] == "HOUR"
    assert GRANULARITY_MAP["D"] == "DAY"
    assert GRANULARITY_MAP["M5"] == "MINUTE_5"


# ── pip_value tests ──────────────────────────────────────────────


def test_pip_value():
    assert CapitalComClient.pip_value("EUR_USD") == 0.0001
    assert CapitalComClient.pip_value("USD_JPY") == 0.01
    assert CapitalComClient.pip_value("XAU_USD") == 0.1
    assert CapitalComClient.pip_value("GOLD") == 0.1
    assert CapitalComClient.pip_value("XAG_USD") == 0.01
    assert CapitalComClient.pip_value("BCO_USD") == 0.01
    assert CapitalComClient.pip_value("NATGAS_USD") == 0.001


# ── Connected mode tests (mocked HTTP) ───────────────────────────


def _mock_urlopen(response_data, headers=None):
    """Create a mock for urllib.request.urlopen."""
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(response_data).encode()
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)
    if headers:
        mock_resp.headers = MagicMock()
        mock_resp.headers.get = lambda key, default="": headers.get(key, default)
    return mock_resp


@patch("backend.data.capitalcom_client.urllib.request.urlopen")
def test_session_creation(mock_urlopen):
    """Test that session creation stores CST and security token."""
    session_resp = _mock_urlopen({}, headers={"CST": "test-cst", "X-SECURITY-TOKEN": "test-token"})
    mock_urlopen.return_value = session_resp

    with patch.dict("os.environ", {
        "CAPITALCOM_API_KEY": "test-key",
        "CAPITALCOM_EMAIL": "test@test.com",
        "CAPITALCOM_PASSWORD": "testpass",
    }):
        client = CapitalComClient({})

    assert client.is_connected
    assert client._cst == "test-cst"
    assert client._security_token == "test-token"


@patch("backend.data.capitalcom_client.urllib.request.urlopen")
def test_get_candles_connected(mock_urlopen):
    """Test candle parsing from Capital.com response format."""
    session_resp = _mock_urlopen({}, headers={"CST": "cst", "X-SECURITY-TOKEN": "tok"})
    candles_resp = _mock_urlopen({
        "prices": [
            {
                "snapshotTimeUTC": "2024-01-15T10:00:00",
                "openPrice": {"bid": 1.0800, "ask": 1.0802},
                "highPrice": {"bid": 1.0820, "ask": 1.0822},
                "lowPrice": {"bid": 1.0790, "ask": 1.0792},
                "closePrice": {"bid": 1.0810, "ask": 1.0812},
                "lastTradedVolume": 1500,
            },
            {
                "snapshotTimeUTC": "2024-01-15T11:00:00",
                "openPrice": {"bid": 1.0810, "ask": 1.0812},
                "highPrice": {"bid": 1.0830, "ask": 1.0832},
                "lowPrice": {"bid": 1.0800, "ask": 1.0802},
                "closePrice": {"bid": 1.0825, "ask": 1.0827},
                "lastTradedVolume": 2000,
            },
        ]
    })
    mock_urlopen.side_effect = [session_resp, candles_resp]

    with patch.dict("os.environ", {
        "CAPITALCOM_API_KEY": "k",
        "CAPITALCOM_EMAIL": "e",
        "CAPITALCOM_PASSWORD": "p",
    }):
        client = CapitalComClient({})

    df = client.get_candles("EUR_USD", "H1", 2)
    assert len(df) == 2
    assert list(df.columns) == ["Open", "High", "Low", "Close", "Volume"]
    assert df.index.name == "time"
    # Check mid-price calculation: (bid + ask) / 2
    assert abs(df.iloc[0]["Open"] - 1.0801) < 0.0001
    assert df.iloc[0]["Volume"] == 1500


@patch("backend.data.capitalcom_client.urllib.request.urlopen")
def test_place_order_connected(mock_urlopen):
    """Test order placement and confirmation flow."""
    session_resp = _mock_urlopen({}, headers={"CST": "cst", "X-SECURITY-TOKEN": "tok"})
    order_resp = _mock_urlopen({"dealReference": "ref-123"})
    confirm_resp = _mock_urlopen({"dealId": "deal-456", "dealStatus": "ACCEPTED"})
    mock_urlopen.side_effect = [session_resp, order_resp, confirm_resp]

    with patch.dict("os.environ", {
        "CAPITALCOM_API_KEY": "k",
        "CAPITALCOM_EMAIL": "e",
        "CAPITALCOM_PASSWORD": "p",
    }):
        client = CapitalComClient({})

    result = client.place_order("EUR_USD", 1000, "long", 1.0750, 1.0900)
    assert result["id"] == "deal-456"
    assert result["status"] == "ACCEPTED"
