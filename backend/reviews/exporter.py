"""Export review data to CSV files."""

from __future__ import annotations

import csv
import io
from datetime import datetime
from pathlib import Path


def export_trades_csv(trades: list[dict]) -> str:
    """Export trades to CSV string."""
    output = io.StringIO()
    if not trades:
        return "No trades in review period.\n"

    fields = ["id", "stream", "instrument", "direction", "entry_price", "exit_price",
              "stop_loss", "take_profit", "position_size", "pnl", "pnl_pips",
              "status", "opened_at", "closed_at"]
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(trades)
    return output.getvalue()


def export_signals_csv(signals: list[dict]) -> str:
    """Export signals to CSV string."""
    output = io.StringIO()
    if not signals:
        return "No signals in review period.\n"

    fields = ["id", "stream", "source", "instrument", "direction", "confidence",
              "reasoning", "was_traded", "rejection_reason", "is_comparison", "created_at"]
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(signals)
    return output.getvalue()


def export_equity_csv(equity_data: list[dict]) -> str:
    """Export equity snapshots to CSV string."""
    output = io.StringIO()
    if not equity_data:
        return "No equity data in review period.\n"

    fields = ["stream", "equity", "open_positions", "recorded_at"]
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(equity_data)
    return output.getvalue()


def export_open_positions_csv(positions: list[dict]) -> str:
    """Export currently open positions to CSV string."""
    output = io.StringIO()
    if not positions:
        return "No open positions.\n"

    fields = ["id", "stream", "instrument", "direction", "entry_price",
              "stop_loss", "take_profit", "position_size", "opened_at"]
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(positions)
    return output.getvalue()


def write_review_files(output_dir: Path, review_md: str,
                       trades_csv: str, signals_csv: str,
                       equity_csv: str, positions_csv: str):
    """Write all review files to a directory."""
    output_dir.mkdir(parents=True, exist_ok=True)

    (output_dir / "REVIEW.md").write_text(review_md)
    (output_dir / "trades.csv").write_text(trades_csv)
    (output_dir / "signals.csv").write_text(signals_csv)
    (output_dir / "equity_curves.csv").write_text(equity_csv)
    (output_dir / "open_positions.csv").write_text(positions_csv)
