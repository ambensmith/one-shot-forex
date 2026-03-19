"""Generate REVIEW.md prose from computed metrics."""

from __future__ import annotations

from datetime import datetime, timezone


def generate_review_md(
    period_label: str,
    stream_metrics: dict[str, dict],
    strategy_metrics: list[dict],
    instrument_metrics: list[dict],
    trigger: str,
) -> str:
    """Build the full REVIEW.md content."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

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

    # Headlines
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

    lines.extend(["", "---", ""])

    # Stream Performance
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

    # Strategy Breakdown
    if strategy_metrics:
        lines.append("## Strategy Breakdown")
        lines.append("")
        lines.append("| Strategy | Signals | Trades | P&L | Win % |")
        lines.append("|----------|---------|--------|-----|-------|")
        for s in strategy_metrics:
            lines.append(
                f"| {s['name']} | {s['signal_count']} | {s['trade_count']} | "
                f"{s['total_pnl']:+.2f} | {s['win_rate']*100:.0f}% |"
            )
        lines.extend(["", "---", ""])

    # Instrument Analysis
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

    # Winning & Losing Trades
    lines.append("## Trade Analysis")
    lines.append("")

    for sid, m in stream_metrics.items():
        if m.get("best_trade"):
            bt = m["best_trade"]
            lines.append(f"### Best Trade ({sid})")
            lines.append(f"- **{bt['instrument']}** {bt['direction']} — P&L: {bt['pnl']:+.2f}")
            lines.append(f"- Opened: {bt.get('opened_at', 'N/A')} | Closed: {bt.get('closed_at', 'N/A')}")
            lines.append("")

        if m.get("worst_trade"):
            wt = m["worst_trade"]
            lines.append(f"### Worst Trade ({sid})")
            lines.append(f"- **{wt['instrument']}** {wt['direction']} — P&L: {wt['pnl']:+.2f}")
            lines.append(f"- Opened: {wt.get('opened_at', 'N/A')} | Closed: {wt.get('closed_at', 'N/A')}")
            lines.append("")

    lines.extend(["---", ""])

    # Auto-Generated Questions
    lines.append("## Questions for Review")
    lines.append("")

    questions = _generate_questions(stream_metrics, strategy_metrics, instrument_metrics)
    for q in questions:
        lines.append(f"- {q}")

    lines.append("")
    return "\n".join(lines)


def _generate_questions(stream_metrics, strategy_metrics, instrument_metrics) -> list[str]:
    """Generate data-driven questions for human review."""
    questions = []

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

    # Default question if none generated
    if not questions:
        questions.append("Review overall system performance and check for anomalies.")

    return questions
