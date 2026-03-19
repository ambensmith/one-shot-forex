"""Per-run review generator — builds a review for each trading cycle."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger("forex_sentinel.reviews.run")


class RunReviewGenerator:
    """Generate a markdown review scoped to a single run cycle."""

    def __init__(self, db, config: dict):
        self.db = db
        self.config = config

    def generate(self, run_context: dict) -> str:
        """Generate a per-run review and return the markdown."""
        run_id = run_context["run_id"]
        started_at = run_context["started_at"]
        completed_at = run_context.get("completed_at", datetime.now(timezone.utc).isoformat())
        market_open = run_context.get("market_open", True)
        skipped_reason = run_context.get("skipped_reason")

        signals = run_context.get("signals_generated", [])
        trades_opened = run_context.get("trades_opened", [])
        trades_closed = run_context.get("trades_closed", [])
        trades_carried = run_context.get("trades_carried", [])
        rejected_signals = run_context.get("rejected_signals", [])
        streams_run = run_context.get("streams_run", [])

        lines = []
        lines.append(f"# Run Review — {run_id}")
        lines.append("")

        if skipped_reason:
            lines.append(f"> **Run skipped:** {skipped_reason}")
            lines.append("")
            return "\n".join(lines)

        # Configuration snapshot
        lines.append("## Run Configuration")
        lines.append(f"- **Streams:** {', '.join(streams_run) if streams_run else 'None'}")
        risk = self.config.get("risk", {})
        lines.append(f"- **Risk:** {risk.get('max_risk_per_trade', 0)*100:.1f}% per trade, "
                      f"max {risk.get('max_open_positions_per_stream', 0)} open, "
                      f"{risk.get('max_daily_loss_per_stream', 0)*100:.0f}% daily loss limit")
        news_cfg = self.config.get("streams", {}).get("news_stream", {})
        if news_cfg.get("enabled"):
            lines.append(f"- **News confidence threshold:** {news_cfg.get('min_confidence', 0)}")
        lines.append("")

        # Signals
        lines.append("## Signal Analysis")
        lines.append("")

        signal_records = self._get_signal_records(signals)
        if signal_records:
            lines.append("### Signals Generated")
            lines.append("| Stream | Instrument | Direction | Confidence | Source | Traded | Reason |")
            lines.append("|--------|-----------|-----------|------------|--------|--------|--------|")
            for s in signal_records:
                traded = "Yes" if s.get("was_traded") else "No"
                reason = s.get("rejection_reason") or (s.get("reasoning", "")[:60] if s.get("was_traded") else "—")
                lines.append(f"| {s.get('stream', '')} | {s.get('instrument', '')} | "
                             f"{s.get('direction', '')} | {s.get('confidence', 0):.2f} | "
                             f"{s.get('source', '')} | {traded} | {reason} |")
            lines.append("")

        rejected_records = self._get_signal_records(rejected_signals)
        if rejected_records:
            lines.append("### Rejected Signals")
            lines.append("| Instrument | Direction | Confidence | Rejection Reason |")
            lines.append("|-----------|-----------|------------|-----------------|")
            for s in rejected_records:
                lines.append(f"| {s.get('instrument', '')} | {s.get('direction', '')} | "
                             f"{s.get('confidence', 0):.2f} | {s.get('rejection_reason', 'Unknown')} |")
            lines.append("")

        # Trade Activity
        lines.append("## Trade Activity")
        lines.append("")

        opened_records = self._get_trade_records(trades_opened)
        if opened_records:
            lines.append("### New Trades Opened")
            lines.append("| # | Stream | Instrument | Dir | Entry | SL | TP | Size |")
            lines.append("|---|--------|-----------|-----|-------|----|----|------|")
            for t in opened_records:
                lines.append(f"| {t.get('id', '')} | {t.get('stream', '')} | "
                             f"{t.get('instrument', '')} | {t.get('direction', '')} | "
                             f"{(t.get('entry_price') or 0):.5f} | {(t.get('stop_loss') or 0):.5f} | "
                             f"{(t.get('take_profit') or 0):.5f} | {(t.get('position_size') or 0):.2f} |")
            lines.append("")

        closed_records = self._get_trade_records(trades_closed)
        if closed_records:
            lines.append("### Trades Closed (This Run)")
            lines.append("| # | Stream | Instrument | Dir | Entry | Exit | P&L | Pips | Status |")
            lines.append("|---|--------|-----------|-----|-------|------|-----|------|--------|")
            for t in closed_records:
                exit_p = t.get("exit_price") or 0
                pnl = t.get("pnl") or 0
                pips = t.get("pnl_pips") or 0
                lines.append(f"| {t.get('id', '')} | {t.get('stream', '')} | "
                             f"{t.get('instrument', '')} | {t.get('direction', '')} | "
                             f"{(t.get('entry_price') or 0):.5f} | {exit_p:.5f} | "
                             f"{pnl:+.2f} | {pips:+.1f} | closed |")
            lines.append("")

        carried_records = self._get_trade_records(trades_carried)
        if carried_records:
            lines.append("### Carried Trades (Still Open)")
            lines.append("| # | Stream | Instrument | Dir | Entry | SL | TP | Size |")
            lines.append("|---|--------|-----------|-----|-------|----|----|------|")
            for t in carried_records:
                lines.append(f"| {t.get('id', '')} | {t.get('stream', '')} | "
                             f"{t.get('instrument', '')} | {t.get('direction', '')} | "
                             f"{(t.get('entry_price') or 0):.5f} | {(t.get('stop_loss') or 0):.5f} | "
                             f"{(t.get('take_profit') or 0):.5f} | {(t.get('position_size') or 0):.2f} |")
            lines.append("")

        if not opened_records and not closed_records and not carried_records:
            lines.append("*No trade activity this run.*")
            lines.append("")

        # Summary
        realized_pnl = sum(t.get("pnl", 0) or 0 for t in closed_records)
        lines.append("## Run Summary")
        lines.append(f"- **Signals analyzed:** {len(signal_records)}")
        lines.append(f"- **Trades opened:** {len(opened_records)}")
        lines.append(f"- **Trades closed:** {len(closed_records)}")
        lines.append(f"- **Trades carried:** {len(carried_records)}")
        lines.append(f"- **Net realized P&L:** {realized_pnl:+.2f}")
        lines.append(f"- **Started:** {started_at}")
        lines.append(f"- **Completed:** {completed_at}")
        lines.append("")

        return "\n".join(lines)

    def _get_signal_records(self, signal_ids: list) -> list[dict]:
        """Fetch signal records by IDs."""
        if not signal_ids:
            return []
        records = []
        for sid in signal_ids:
            row = self.db.execute("SELECT * FROM signals WHERE id = ?", (sid,)).fetchone()
            if row:
                records.append(dict(row))
        return records

    def _get_trade_records(self, trade_ids: list) -> list[dict]:
        """Fetch trade records by IDs."""
        if not trade_ids:
            return []
        records = []
        for tid in trade_ids:
            row = self.db.execute("SELECT * FROM trades WHERE id = ?", (tid,)).fetchone()
            if row:
                records.append(dict(row))
        return records
