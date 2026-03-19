"""Tests for risk manager."""

from backend.core.database import Database
from backend.data.oanda_client import OandaClient
from backend.risk.risk_manager import RiskManager


def _setup():
    config = {
        "risk": {
            "max_risk_per_trade": 0.01,
            "max_open_positions_per_stream": 5,
            "max_daily_loss_per_stream": 0.03,
            "max_correlated_positions": 2,
            "default_rr_ratio": 1.5,
            "stop_loss_method": "atr",
            "atr_multiplier": 1.5,
            "atr_period": 14,
        },
        "execution": {"oanda_environment": "practice"},
    }
    db = Database(":memory:")
    oanda = OandaClient(config)
    risk = RiskManager(config, oanda, db)
    return risk, db


def test_risk_check_approved():
    risk, db = _setup()
    check = risk.check_trade("strategy", "EUR_USD", "long", 1.0800, 1.0750)
    assert check.approved
    assert check.position_size > 0


def test_position_sizing():
    risk, _ = _setup()
    size = risk.calculate_position_size(33333, 0.01, 1.0800, 1.0750, "EUR_USD")
    assert size > 0


def test_stop_loss_calculation():
    risk, _ = _setup()
    sl = risk.calculate_stop_loss("EUR_USD", 1.0800, "long")
    assert sl < 1.0800

    sl_short = risk.calculate_stop_loss("EUR_USD", 1.0800, "short")
    assert sl_short > 1.0800


def test_take_profit_calculation():
    risk, _ = _setup()
    tp = risk.calculate_take_profit(1.0800, 1.0750, "long")
    assert tp > 1.0800

    tp_short = risk.calculate_take_profit(1.0800, 1.0850, "short")
    assert tp_short < 1.0800
