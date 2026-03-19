"""Tests for JSON dashboard export."""

import json
from pathlib import Path

from backend.core.database import Database
from backend.dashboard.json_exporter import export_all


def test_export_creates_files(tmp_path):
    """Test that export creates all expected JSON files."""
    db_path = str(tmp_path / "test.db")
    db = Database(db_path)

    # Insert some test data
    db.insert_signal(
        stream="strategy", source="momentum", instrument="EUR_USD",
        direction="long", confidence=0.75, reasoning="test"
    )
    db.insert_trade(
        stream="strategy", instrument="EUR_USD", direction="long",
        entry_price=1.08, stop_loss=1.075, take_profit=1.0875,
        position_size=1000,
    )
    db.insert_equity_snapshot("strategy", 100, 1)
    db.close()

    # Monkey-patch output dir
    import backend.dashboard.json_exporter as exporter
    original_dir = exporter.OUTPUT_DIR
    exporter.OUTPUT_DIR = tmp_path / "data"

    try:
        export_all(db_path)

        assert (tmp_path / "data" / "dashboard.json").exists()
        assert (tmp_path / "data" / "trades.json").exists()
        assert (tmp_path / "data" / "equity.json").exists()
        assert (tmp_path / "data" / "signals.json").exists()
        assert (tmp_path / "data" / "models.json").exists()

        # Validate JSON
        dashboard = json.loads((tmp_path / "data" / "dashboard.json").read_text())
        assert "streams" in dashboard
        assert len(dashboard["streams"]) >= 2
    finally:
        exporter.OUTPUT_DIR = original_dir
