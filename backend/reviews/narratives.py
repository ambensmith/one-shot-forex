"""Generate REVIEW.md prose from computed metrics."""

from __future__ import annotations

import json
from datetime import datetime, timezone


def _parse_json_field(value):
    """Parse a JSON string field from SQLite, returning parsed value or original."""
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, ValueError):
            return value
    return value


def _format_duration(opened_at, closed_at) -> str:
    """Format trade duration as human-readable string."""
    if not opened_at or not closed_at:
        return "N/A"
    try:
        t_open = datetime.fromisoformat(str(opened_at))
        t_close = datetime.fromisoformat(str(closed_at))
        delta = t_close - t_open
        total_seconds = int(delta.total_seconds())
        if total_seconds < 0:
            return "N/A"
        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60
        if days > 0:
            return f"{days}d {hours}h"
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"
    except (ValueError, TypeError):
        return "N/A"


def _build_signal_lookup(signals: list[dict]) -> dict[int, dict]:
    """Build id -> signal dict lookup for O(1) access."""
    lookup = {}
    for s in signals:
        sid = s.get("id")
        if sid is not None:
            lookup[int(sid)] = s
    return lookup


def _get_linked_signals(trade: dict, signal_lookup: dict[int, dict]) -> list[dict]:
    """Get signals linked to a trade via signal_ids."""
    raw_ids = _parse_json_field(trade.get("signal_ids"))
    if not raw_ids:
        return []
    if isinstance(raw_ids, list):
        return [signal_lookup[int(sid)] for sid in raw_ids if int(sid) in signal_lookup]
    return []


def _format_price(price) -> str:
    """Format a price value, handling None."""
    if price is None:
        return "N/A"
    return f"{float(price):.5f}"


def _compute_rr(entry, target, stop) -> str:
    """Compute risk:reward ratio as string."""
    try:
        entry, target, stop = float(entry), float(target), float(stop)
        risk = abs(entry - stop)
        if risk == 0:
            return "N/A"
        reward = abs(target - entry)
        return f"1:{reward/risk:.1f}"
    except (TypeError, ValueError, ZeroDivisionError):
        return "N/A"


def generate_review_md(
    period_label: str,
    stream_metrics: dict[str, dict],
    strategy_metrics: list[dict],
    instrument_metrics: list[dict],
    trigger: str,
    trades: list[dict] | None = None,
    signals: list[dict] | None = None,
) -> str:
    """Build the full REVIEW.md content."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    trades = trades or []
    signals = signals or []

    signal_lookup = _build_signal_lookup(signals)

    lines = [
        f"# Forex Sentinel — Review",
        f"",
        f"**Period:** {period_label}",
        f"**Generated:** {now}",
        f"**Trigger:** {trigger}",
        f"",
        "---",
        "",
    ]

    # ── Headlines ──
    lines.append("## Headlines")
    lines.append("")

    all_pnl = sum(m.get("total_pnl", 0) for m in stream_metrics.values())
    all_trades = sum(m.get("trade_count", 0) for m in stream_metrics.values())

    best_stream = max(stream_metrics.items(), key=lambda x: x[1].get("total_pnl", 0))
    worst_stream = min(stream_metrics.items(), key=lambda x: x[1].get("total_pnl", 0))

    lines.append(f"- **Overall P&L:** {all_pnl:+.2f}")
    lines.append(f"- **Total Trades:** {all_trades}")
    lines.append(f"- **Best Performer:** {best_stream[0]} ({best_stream[1]['total_pnl']:+.2f})")
    lines.append(f"- **Worst Performer:** {worst_stream[0]} ({worst_stream[1]['total_pnl']:+.2f})")

    # Find biggest winner/loser across all streams
    for sid, m in stream_metrics.items():
        if m.get("best_trade"):
            bt = m["best_trade"]
            lines.append(f"- **Biggest Winner:** {bt['instrument']} {bt['direction']} ({bt['pnl']:+.2f})")
            break
    for sid, m in stream_metrics.items():
        if m.get("worst_trade"):
            wt = m["worst_trade"]
            lines.append(f"- **Biggest Loser:** {wt['instrument']} {wt['direction']} ({wt['pnl']:+.2f})")
            break

    # Signal conversion stats
    if signals:
        non_comparison = [s for s in signals if not s.get("is_comparison")]
        traded = [s for s in non_comparison if s.get("was_traded")]
        rejected = [s for s in non_comparison if s.get("rejection_reason")]
        neutral = [s for s in non_comparison if s.get("direction") == "neutral"]
        lines.append(
            f"- **Signals Generated:** {len(non_comparison)} "
            f"({len(traded)} traded, {len(rejected)} rejected, {len(neutral)} neutral)"
        )

    lines.extend(["", "---", ""])

    # ── Stream Performance ──
    lines.append("## Stream Performance")
    lines.append("")
    lines.append("| Stream | P&L | Trades | Win % | Sharpe | Max DD |")
    lines.append("|--------|-----|--------|-------|--------|--------|")
    for sid, m in stream_metrics.items():
        lines.append(
            f"| {sid} | {m['total_pnl']:+.2f} | {m['trade_count']} | "
            f"{m['win_rate']*100:.0f}% | {m['sharpe_ratio']:.2f} | {m['max_drawdown']*100:.1f}% |"
        )
    lines.extend(["", "---", ""])

    # ── Strategy Breakdown (enhanced with conversion rate) ──
    if strategy_metrics:
        lines.append("## Strategy Breakdown")
        lines.append("")
        lines.append("| Strategy | Signals | Trades | Conv % | P&L | Win % |")
        lines.append("|----------|---------|--------|--------|-----|-------|")
        for s in strategy_metrics:
            conv = (s["trade_count"] / s["signal_count"] * 100) if s["signal_count"] > 0 else 0
            lines.append(
                f"| {s['name']} | {s['signal_count']} | {s['trade_count']} | "
                f"{conv:.0f}% | {s['total_pnl']:+.2f} | {s['win_rate']*100:.0f}% |"
            )
        lines.extend(["", "---", ""])

    # ── Instrument Analysis ──
    if instrument_metrics:
        lines.append("## Instrument Analysis")
        lines.append("")
        lines.append("| Instrument | Trades | P&L | Win % |")
        lines.append("|------------|--------|-----|-------|")
        for i in instrument_metrics:
            lines.append(
                f"| {i['instrument']} | {i['trade_count']} | "
                f"{i['total_pnl']:+.2f} | {i['win_rate']*100:.0f}% |"
            )
        lines.extend(["", "---", ""])

    # ── Signal Pipeline ──
    if signals:
        lines.extend(_build_signal_pipeline_section(signals))

    # ── Rejected Signals ──
    if signals:
        lines.extend(_build_rejected_signals_section(signals))

    # ── Trade Analysis (enhanced best/worst) ──
    lines.append("## Trade Analysis")
    lines.append("")

    for sid, m in stream_metrics.items():
        if m.get("best_trade"):
            bt = m["best_trade"]
            lines.append(f"### Best Trade ({sid})")
            lines.append(f"- **{bt['instrument']}** {bt['direction']} — P&L: {bt['pnl']:+.2f} ({bt.get('pnl_pips', 'N/A')} pips)")
            lines.append(f"- Entry: {_format_price(bt.get('entry_price'))} | Exit: {_format_price(bt.get('exit_price'))}")
            lines.append(f"- SL: {_format_price(bt.get('stop_loss'))} | TP: {_format_price(bt.get('take_profit'))}")
            lines.append(f"- Size: {bt.get('position_size', 'N/A')} | Duration: {_format_duration(bt.get('opened_at'), bt.get('closed_at'))}")
            lines.append(f"- Planned R:R: {_compute_rr(bt.get('entry_price'), bt.get('take_profit'), bt.get('stop_loss'))}")
            # Link signal reasoning
            linked = _get_linked_signals(bt, signal_lookup)
            for sig in linked:
                lines.append(f"  > **Signal:** conf {sig.get('confidence', 'N/A')}, source: {sig.get('source', 'N/A')}")
                if sig.get("reasoning"):
                    lines.append(f"  > **Reasoning:** {sig['reasoning']}")
                meta = _parse_json_field(sig.get("metadata"))
                if isinstance(meta, dict) and meta.get("headlines"):
                    headlines = meta["headlines"][:3]
                    lines.append(f"  > **Headlines:** {'; '.join(str(h) for h in headlines)}")
            lines.append("")

        if m.get("worst_trade"):
            wt = m["worst_trade"]
            lines.append(f"### Worst Trade ({sid})")
            lines.append(f"- **{wt['instrument']}** {wt['direction']} — P&L: {wt['pnl']:+.2f} ({wt.get('pnl_pips', 'N/A')} pips)")
            lines.append(f"- Entry: {_format_price(wt.get('entry_price'))} | Exit: {_format_price(wt.get('exit_price'))}")
            lines.append(f"- SL: {_format_price(wt.get('stop_loss'))} | TP: {_format_price(wt.get('take_profit'))}")
            lines.append(f"- Size: {wt.get('position_size', 'N/A')} | Duration: {_format_duration(wt.get('opened_at'), wt.get('closed_at'))}")
            lines.append(f"- Planned R:R: {_compute_rr(wt.get('entry_price'), wt.get('take_profit'), wt.get('stop_loss'))}")
            linked = _get_linked_signals(wt, signal_lookup)
            for sig in linked:
                lines.append(f"  > **Signal:** conf {sig.get('confidence', 'N/A')}, source: {sig.get('source', 'N/A')}")
                if sig.get("reasoning"):
                    lines.append(f"  > **Reasoning:** {sig['reasoning']}")
                meta = _parse_json_field(sig.get("metadata"))
                if isinstance(meta, dict) and meta.get("headlines"):
                    headlines = meta["headlines"][:3]
                    lines.append(f"  > **Headlines:** {'; '.join(str(h) for h in headlines)}")
            lines.append("")

    lines.extend(["---", ""])

    # ── Complete Trade Log ──
    if trades:
        lines.extend(_build_complete_trade_log(trades, signal_lookup))

    # ── Comparison Model Performance ──
    if signals:
        comp_lines = _build_comparison_section(signals)
        if comp_lines:
            lines.extend(comp_lines)

    # ── Auto-Generated Questions ──
    lines.append("## Questions for Review")
    lines.append("")

    questions = _generate_questions(stream_metrics, strategy_metrics, instrument_metrics, trades, signals)
    for q in questions:
        lines.append(f"- {q}")

    lines.append("")
    return "\n".join(lines)


def _build_signal_pipeline_section(signals: list[dict]) -> list[str]:
    """Build the Signal Pipeline section showing conversion funnel."""
    lines = ["## Signal Pipeline", ""]

    non_comparison = [s for s in signals if not s.get("is_comparison")]
    traded = [s for s in non_comparison if s.get("was_traded")]
    rejected = [s for s in non_comparison if s.get("rejection_reason")]
    neutral = [s for s in non_comparison if s.get("direction") == "neutral"]
    actionable = len(non_comparison) - len(neutral)
    conv_rate = (len(traded) / actionable * 100) if actionable > 0 else 0

    lines.append(f"- **Total Signals:** {len(non_comparison)} (excl. comparison models)")
    lines.append(f"- **Actionable (non-neutral):** {actionable}")
    lines.append(f"- **Traded:** {len(traded)}")
    lines.append(f"- **Rejected:** {len(rejected)}")
    lines.append(f"- **Neutral (no action):** {len(neutral)}")
    lines.append(f"- **Conversion Rate:** {conv_rate:.1f}%")
    lines.append("")

    # Rejection reasons breakdown
    if rejected:
        reasons: dict[str, int] = {}
        for s in rejected:
            reason = s.get("rejection_reason", "Unknown")
            # Normalize: extract category before parenthetical details
            if "(" in reason:
                reason = reason[:reason.index("(")].strip()
            reasons[reason] = reasons.get(reason, 0) + 1

        lines.append("### Rejection Reasons")
        lines.append("")
        lines.append("| Reason | Count | % of Rejections |")
        lines.append("|--------|-------|-----------------|")
        for reason, count in sorted(reasons.items(), key=lambda x: -x[1]):
            pct = count / len(rejected) * 100
            lines.append(f"| {reason} | {count} | {pct:.0f}% |")
        lines.append("")

    lines.extend(["---", ""])
    return lines


def _build_rejected_signals_section(signals: list[dict]) -> list[str]:
    """Build table of recent rejected signals."""
    rejected = [s for s in signals if s.get("rejection_reason") and not s.get("is_comparison")]
    if not rejected:
        return []

    lines = ["## Rejected Signals", ""]

    # Sort by created_at descending, take most recent 20
    rejected_sorted = sorted(rejected, key=lambda s: s.get("created_at", ""), reverse=True)
    shown = rejected_sorted[:20]

    lines.append("| Time | Stream | Instrument | Dir | Conf | Source | Reason |")
    lines.append("|------|--------|------------|-----|------|--------|--------|")
    for s in shown:
        created = str(s.get("created_at", "N/A"))
        if len(created) > 16:
            created = created[:16]  # Trim to YYYY-MM-DD HH:MM
        lines.append(
            f"| {created} | {s.get('stream', '')} | {s.get('instrument', '')} | "
            f"{s.get('direction', '')} | {s.get('confidence', 0):.2f} | "
            f"{s.get('source', '')} | {s.get('rejection_reason', '')} |"
        )

    if len(rejected) > 20:
        lines.append("")
        lines.append(f"*Showing 20 of {len(rejected)} rejected signals. See signals.csv for complete list.*")

    lines.extend(["", "---", ""])
    return lines


def _build_complete_trade_log(trades: list[dict], signal_lookup: dict[int, dict]) -> list[str]:
    """Build complete trade log grouped by stream with signal reasoning."""
    lines = ["## Complete Trade Log", ""]

    # Group trades by stream
    by_stream: dict[str, list[dict]] = {}
    for t in trades:
        stream = t.get("stream", "unknown")
        by_stream.setdefault(stream, []).append(t)

    max_trades = 50
    total_shown = 0

    for stream, stream_trades in sorted(by_stream.items()):
        lines.append(f"### {stream}")
        lines.append("")
        lines.append("| # | Instrument | Dir | Entry | Exit | SL | TP | Size | P&L | Pips | Status | Duration | R:R Plan |")
        lines.append("|---|------------|-----|-------|------|----|----|------|-----|------|--------|----------|----------|")

        for i, t in enumerate(stream_trades, 1):
            if total_shown >= max_trades:
                break

            pnl_str = f"{t['pnl']:+.2f}" if t.get("pnl") is not None else "open"
            pips_str = f"{t['pnl_pips']:+.1f}" if t.get("pnl_pips") is not None else "open"
            duration = _format_duration(t.get("opened_at"), t.get("closed_at"))
            rr_plan = _compute_rr(t.get("entry_price"), t.get("take_profit"), t.get("stop_loss"))

            lines.append(
                f"| {i} | {t.get('instrument', '')} | {t.get('direction', '')} | "
                f"{_format_price(t.get('entry_price'))} | {_format_price(t.get('exit_price'))} | "
                f"{_format_price(t.get('stop_loss'))} | {_format_price(t.get('take_profit'))} | "
                f"{t.get('position_size', 'N/A')} | {pnl_str} | {pips_str} | "
                f"{t.get('status', '')} | {duration} | {rr_plan} |"
            )

            # Signal details below the trade row
            linked = _get_linked_signals(t, signal_lookup)
            for sig in linked:
                lines.append(
                    f"| | > **Signal:** conf {sig.get('confidence', 'N/A'):.2f}, "
                    f"source: {sig.get('source', 'N/A')} | | | | | | | | | | | |"
                )
                if sig.get("reasoning"):
                    reasoning_text = str(sig["reasoning"])[:200]
                    lines.append(f"| | > *{reasoning_text}* | | | | | | | | | | | |")
                meta = _parse_json_field(sig.get("metadata"))
                if isinstance(meta, dict) and meta.get("headlines"):
                    headlines = [str(h) for h in meta["headlines"][:3]]
                    lines.append(f"| | > Headlines: {'; '.join(headlines)} | | | | | | | | | | | |")

            total_shown += 1

        if total_shown >= max_trades:
            break
        lines.append("")

    total_trades = len(trades)
    if total_trades > max_trades:
        lines.append(f"*Showing {max_trades} of {total_trades} trades. See trades.csv for complete list.*")
        lines.append("")

    lines.extend(["---", ""])
    return lines


def _build_comparison_section(signals: list[dict]) -> list[str]:
    """Build comparison model performance section if comparison signals exist."""
    comparison = [s for s in signals if s.get("is_comparison")]
    if not comparison:
        return []

    primary = [s for s in signals if not s.get("is_comparison") and s.get("stream") == "news"]

    lines = ["## Comparison Model Performance", ""]

    # Group by instrument for side-by-side
    by_instrument: dict[str, dict[str, list]] = {}
    for s in comparison:
        inst = s.get("instrument", "")
        by_instrument.setdefault(inst, {"comparison": [], "primary": []})
        by_instrument[inst]["comparison"].append(s)

    for s in primary:
        inst = s.get("instrument", "")
        if inst in by_instrument:
            by_instrument[inst]["primary"].append(s)

    lines.append("| Instrument | Primary Dir | Primary Conf | Comparison Dir | Comparison Conf | Source |")
    lines.append("|------------|-------------|--------------|----------------|-----------------|--------|")

    for inst, data in sorted(by_instrument.items()):
        for comp_sig in data["comparison"]:
            # Find matching primary signal (closest in time)
            pri = data["primary"][0] if data["primary"] else {}
            lines.append(
                f"| {inst} | {pri.get('direction', 'N/A')} | "
                f"{pri.get('confidence', 0):.2f} | {comp_sig.get('direction', 'N/A')} | "
                f"{comp_sig.get('confidence', 0):.2f} | {comp_sig.get('source', '')} |"
            )

    lines.extend(["", "---", ""])
    return lines


def _generate_questions(
    stream_metrics,
    strategy_metrics,
    instrument_metrics,
    trades: list[dict] | None = None,
    signals: list[dict] | None = None,
) -> list[str]:
    """Generate data-driven questions for human review."""
    questions = []
    trades = trades or []
    signals = signals or []

    # Check for underperforming strategies
    for s in strategy_metrics:
        if s["trade_count"] > 5 and s["win_rate"] < 0.4:
            questions.append(
                f"Strategy '{s['name']}' has a {s['win_rate']*100:.0f}% win rate over "
                f"{s['trade_count']} trades — should parameters be adjusted?"
            )

    # Check for losing instruments
    for i in instrument_metrics:
        if i["total_pnl"] < 0 and i["trade_count"] > 3:
            questions.append(
                f"{i['instrument']} is net negative ({i['total_pnl']:+.2f} over "
                f"{i['trade_count']} trades) — remove from active instruments?"
            )

    # Check for stream divergence
    pnls = {sid: m["total_pnl"] for sid, m in stream_metrics.items()}
    if len(pnls) >= 2:
        best = max(pnls.values())
        worst = min(pnls.values())
        if best > 0 and worst < 0:
            questions.append(
                f"Streams are diverging (best: {best:+.2f}, worst: {worst:+.2f}) — "
                "investigate what's causing the difference."
            )

    # Signal conversion rate check
    if signals:
        non_comparison = [s for s in signals if not s.get("is_comparison")]
        neutral = [s for s in non_comparison if s.get("direction") == "neutral"]
        actionable = len(non_comparison) - len(neutral)
        traded = [s for s in non_comparison if s.get("was_traded")]
        if actionable > 5:
            conv_rate = len(traded) / actionable
            if conv_rate < 0.3:
                questions.append(
                    f"Only {conv_rate*100:.0f}% of actionable signals converted to trades — "
                    "are confidence thresholds or risk limits too restrictive?"
                )

    # Dominant rejection reason
    if signals:
        rejected = [s for s in signals if s.get("rejection_reason") and not s.get("is_comparison")]
        if len(rejected) > 5:
            reasons: dict[str, int] = {}
            for s in rejected:
                reason = s.get("rejection_reason", "Unknown")
                if "(" in reason:
                    reason = reason[:reason.index("(")].strip()
                reasons[reason] = reasons.get(reason, 0) + 1
            top_reason, top_count = max(reasons.items(), key=lambda x: x[1])
            if top_count / len(rejected) > 0.5:
                questions.append(
                    f"'{top_reason}' accounts for {top_count}/{len(rejected)} rejections — "
                    "review the related parameters?"
                )

    # Short average trade duration
    if trades:
        closed = [t for t in trades if t.get("closed_at") and t.get("opened_at")]
        if len(closed) >= 3:
            try:
                durations = []
                for t in closed:
                    t_open = datetime.fromisoformat(str(t["opened_at"]))
                    t_close = datetime.fromisoformat(str(t["closed_at"]))
                    durations.append((t_close - t_open).total_seconds())
                avg_secs = sum(durations) / len(durations)
                if avg_secs < 3600:
                    questions.append(
                        f"Average trade duration is {avg_secs/60:.0f} minutes — are stops too tight?"
                    )
            except (ValueError, TypeError):
                pass

    # Comparison model disagreement
    if signals:
        comparison = [s for s in signals if s.get("is_comparison")]
        primary_news = [s for s in signals if not s.get("is_comparison") and s.get("stream") == "news"]
        if comparison and primary_news:
            disagree = 0
            for comp in comparison:
                inst = comp.get("instrument")
                matching = [p for p in primary_news if p.get("instrument") == inst]
                if matching and matching[0].get("direction") != comp.get("direction"):
                    disagree += 1
            if len(comparison) > 3 and disagree / len(comparison) > 0.3:
                questions.append(
                    f"Comparison model disagreed with primary on {disagree}/{len(comparison)} signals — investigate divergence."
                )

    # Default question if none generated
    if not questions:
        questions.append("Review overall system performance and check for anomalies.")

    return questions
