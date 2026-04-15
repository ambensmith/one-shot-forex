"""Review generator — builds complete Cowork review packets."""

from __future__ import annotations

import logging
import os
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

logger = logging.getLogger("forex_sentinel.reviews")


class ReviewGenerator:
    def __init__(self, db, config: dict):
        self.db = db
        self.config = config
        self.reviews_cfg = config.get("reviews", {})
        self.output_base = Path(self.reviews_cfg.get("output_dir", "reviews"))

    def generate(self, trigger: str = "manual", period_days: int | None = None):
        """Generate a complete review packet."""
        from backend.reviews.metrics import (
            compute_stream_metrics,
            compute_instrument_metrics,
            compute_strategy_metrics,
        )
        from backend.reviews.narratives import generate_review_md
        from backend.reviews.exporter import (
            export_trades_csv,
            export_signals_csv,
            export_equity_csv,
            export_open_positions_csv,
            write_review_files,
        )

        days = period_days or self.reviews_cfg.get("review_period_days", 7)
        since = datetime.now(timezone.utc) - timedelta(days=days)
        period_label = f"Last {days} days ({since.strftime('%Y-%m-%d')} to {datetime.now(timezone.utc).strftime('%Y-%m-%d')})"

        logger.info(f"Generating review: {period_label} (trigger: {trigger})")

        # Compute metrics for all streams
        stream_metrics = {}
        for stream_id in ["news", "strategy"]:
            stream_metrics[stream_id] = compute_stream_metrics(self.db, stream_id, since)

        for hybrid in self.db.get_active_hybrids():
            hid = f"hybrid:{hybrid['name']}"
            stream_metrics[hid] = compute_stream_metrics(self.db, hid, since)

        strategy_metrics = compute_strategy_metrics(self.db, since)
        instrument_metrics = compute_instrument_metrics(self.db, since)

        # Query trades and signals (used by both narrative and CSV export)
        trades = self.db.get_trades(limit=10000, since=since)
        signals = self.db.get_signals(limit=10000, since=since)

        # Generate REVIEW.md
        review_md = generate_review_md(
            period_label=period_label,
            stream_metrics=stream_metrics,
            strategy_metrics=strategy_metrics,
            instrument_metrics=instrument_metrics,
            trigger=trigger,
            trades=trades,
            signals=signals,
        )

        # Export CSVs
        equity = []
        for sid in ["news", "strategy"]:
            equity.extend(self.db.get_equity_history(sid, since=since))
        open_positions = self.db.get_open_trades()

        trades_csv = export_trades_csv(trades)
        signals_csv = export_signals_csv(signals)
        equity_csv = export_equity_csv(equity)
        positions_csv = export_open_positions_csv(open_positions)

        # Write to timestamped archive directory
        now = datetime.now(timezone.utc)
        archive_name = f"{now.strftime('%Y-%m-%d_%H-%M')}_{trigger}"
        archive_dir = self.output_base / "archive" / archive_name
        write_review_files(archive_dir, review_md, trades_csv, signals_csv, equity_csv, positions_csv)

        # Update latest symlink
        latest_dir = self.output_base / "latest"
        if latest_dir.exists():
            if latest_dir.is_symlink():
                latest_dir.unlink()
            else:
                shutil.rmtree(latest_dir)
        # Copy to latest instead of symlink (better git compatibility)
        shutil.copytree(archive_dir, latest_dir)

        # Generate SYSTEM_CONTEXT.md
        self._generate_system_context()

        # Prune old archives
        self._prune_archives()

        logger.info(f"Review generated: {archive_dir}")

    def _generate_system_context(self):
        """Auto-generate SYSTEM_CONTEXT.md from current config."""
        import yaml

        lines = [
            "# Forex Sentinel — System Context",
            "",
            "This file is auto-generated from the current system configuration.",
            "It provides full context for Cowork review sessions.",
            "",
            "---",
            "",
            "## Active Streams",
            "",
        ]

        streams = self.config.get("streams", {})

        # News stream
        news_cfg = streams.get("news_stream", {})
        if news_cfg.get("enabled"):
            lines.append("### News Stream")
            lines.append(f"- **Capital:** {news_cfg.get('capital_allocation', 0)}")
            lines.append(f"- **Instruments:** {', '.join(news_cfg.get('instruments', []))}")
            llm = news_cfg.get("llm", {})
            lines.append(f"- **Relevance Model:** {llm.get('relevance_model', 'N/A')}")
            lines.append(f"- **Signal Model:** {llm.get('signal_model', 'N/A')}")
            lines.append(f"- **Min Confidence:** {news_cfg.get('min_confidence', 0)}")
            lines.append("")

        # Strategy stream
        strat_cfg = streams.get("strategy_stream", {})
        if strat_cfg.get("enabled"):
            lines.append("### Strategy Stream")
            lines.append(f"- **Capital:** {strat_cfg.get('capital_allocation', 0)}")
            lines.append(f"- **Instruments:** {', '.join(strat_cfg.get('instruments', []))}")
            lines.append("- **Strategies:**")
            for s in strat_cfg.get("strategies", []):
                status = "ON" if s.get("enabled", True) else "OFF"
                lines.append(f"  - {s['name']} [{status}] — params: {s.get('params', {})}")
            lines.append("")

        # Hybrid streams
        hybrids = self.db.get_active_hybrids()
        if hybrids:
            lines.append("### Active Hybrids")
            for h in hybrids:
                lines.append(f"- **{h['name']}**: {h.get('combiner_mode', 'N/A')} combiner")
                lines.append(f"  Instruments: {', '.join(h.get('instruments', []))}")
                for m in h.get("modules", []):
                    lines.append(f"  - {m.get('name', 'N/A')} (weight: {m.get('weight', 0)}, must_participate: {m.get('must_participate', False)})")
            lines.append("")

        # Risk settings
        risk = self.config.get("risk", {})
        lines.extend([
            "---",
            "",
            "## Risk Settings",
            "",
            f"- Max risk per trade: {risk.get('max_risk_per_trade', 0)*100}%",
            f"- Max open positions per stream: {risk.get('max_open_positions_per_stream', 0)}",
            f"- Max daily loss per stream: {risk.get('max_daily_loss_per_stream', 0)*100}%",
            f"- Max correlated positions: {risk.get('max_correlated_positions', 0)}",
            f"- Default R:R ratio: {risk.get('default_rr_ratio', 0)}",
            f"- Stop loss method: {risk.get('stop_loss_method', 'N/A')}",
            "",
            "---",
            "",
            "## What I Want From Reviews",
            "",
            "- Which stream is performing best and why",
            "- Which instruments are profitable vs loss-making",
            "- Whether the LLM reasoning was correct on winning AND losing trades",
            "- Suggestions for parameter changes backed by the data",
            "- Whether any strategy should be enabled/disabled",
            "- Correlation between streams — are they taking the same trades?",
            "",
        ])

        (self.output_base / "SYSTEM_CONTEXT.md").write_text("\n".join(lines))

    def _prune_archives(self):
        """Remove oldest archives beyond max_archive_count."""
        max_count = self.reviews_cfg.get("max_archive_count", 30)
        archive_dir = self.output_base / "archive"
        if not archive_dir.exists():
            return

        archives = sorted(archive_dir.iterdir(), key=lambda p: p.name)
        while len(archives) > max_count:
            oldest = archives.pop(0)
            shutil.rmtree(oldest)
            logger.info(f"Pruned old review: {oldest}")

    @classmethod
    def from_cli(cls, period: str | None = None):
        """Create generator from CLI args and run."""
        from backend.core.config import load_config
        from backend.core.database import Database

        config = load_config()
        db = Database("data/sentinel.db")

        days = 7
        if period:
            if period.endswith("d"):
                days = int(period[:-1])
            elif period.endswith("w"):
                days = int(period[:-1]) * 7

        generator = cls(db, config)
        generator.generate(trigger="manual", period_days=days)
