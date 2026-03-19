"""Test the news categorization pipeline with sample headlines.

Demonstrates: fetching -> deduplication -> instrument mapping -> display.
In production, headlines come from RSS/GDELT/calendar. Here we use realistic
sample data to verify the pipeline works end-to-end.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.core.config import load_instruments
from backend.data.news_ingestor import RawNewsItem, deduplicate_headlines
from backend.signals.instrument_mapper import InstrumentMapper


# Realistic sample headlines (mix of sources)
SAMPLE_NEWS = [
    # ECB / EUR
    RawNewsItem("ECB holds rates steady as Lagarde signals caution on inflation outlook", "BBC Business",
                published_at=datetime(2026, 3, 19, 8, 30, tzinfo=timezone.utc)),
    RawNewsItem("European Central Bank keeps policy unchanged, euro dips on dovish tone", "Reuters",
                published_at=datetime(2026, 3, 19, 8, 45, tzinfo=timezone.utc)),
    RawNewsItem("Eurozone GDP growth revised upward to 0.4% in Q4 2025", "GDELT",
                published_at=datetime(2026, 3, 19, 7, 0, tzinfo=timezone.utc)),

    # Fed / USD
    RawNewsItem("Federal Reserve officials hint at potential rate cut in June meeting", "Reuters",
                published_at=datetime(2026, 3, 19, 14, 0, tzinfo=timezone.utc)),
    RawNewsItem("FOMC minutes reveal growing concern over slowing US jobs market", "BBC Business",
                published_at=datetime(2026, 3, 19, 13, 30, tzinfo=timezone.utc)),
    RawNewsItem("US inflation falls to 2.3%, bolstering case for Fed rate cut", "GDELT",
                published_at=datetime(2026, 3, 19, 10, 0, tzinfo=timezone.utc)),
    RawNewsItem("Non-farm payrolls miss expectations at 142K vs 175K forecast", "Economic Calendar",
                summary="Impact: High. US economic event."),

    # BOJ / JPY
    RawNewsItem("Bank of Japan surprises with hawkish hold, yen strengthens sharply", "Reuters",
                published_at=datetime(2026, 3, 19, 3, 0, tzinfo=timezone.utc)),
    RawNewsItem("BOJ Governor Ueda hints at further policy normalisation in H2 2026", "GDELT",
                published_at=datetime(2026, 3, 19, 4, 0, tzinfo=timezone.utc)),

    # BOE / GBP
    RawNewsItem("Bank of England holds rates at 4.25% amid stubborn UK inflation", "BBC Business",
                published_at=datetime(2026, 3, 19, 12, 0, tzinfo=timezone.utc)),
    RawNewsItem("UK GDP contracts 0.1% in January, raising recession fears", "Reuters",
                published_at=datetime(2026, 3, 19, 9, 30, tzinfo=timezone.utc)),

    # Gold / safe haven
    RawNewsItem("Gold surges past $3100 as geopolitical tensions escalate in Middle East", "Reuters",
                published_at=datetime(2026, 3, 19, 11, 0, tzinfo=timezone.utc)),
    RawNewsItem("Central bank gold buying hits record in Q1 2026, led by China and India", "GDELT",
                published_at=datetime(2026, 3, 19, 6, 0, tzinfo=timezone.utc)),
    RawNewsItem("Treasury yields fall as investors seek safe haven assets", "BBC Business",
                published_at=datetime(2026, 3, 19, 15, 0, tzinfo=timezone.utc)),

    # Oil
    RawNewsItem("OPEC+ agrees to extend production cuts through Q3 2026", "Reuters",
                published_at=datetime(2026, 3, 19, 10, 30, tzinfo=timezone.utc)),
    RawNewsItem("Brent crude jumps 3% on supply fears as Iran tensions rise", "GDELT",
                published_at=datetime(2026, 3, 19, 11, 30, tzinfo=timezone.utc)),
    RawNewsItem("US shale production declines for third consecutive month", "BBC Business",
                published_at=datetime(2026, 3, 19, 16, 0, tzinfo=timezone.utc)),

    # Economic calendar events
    RawNewsItem("[USD] Non-Farm Payrolls Actual: 142K (Forecast: 175K)", "Economic Calendar",
                summary="Impact: High. US economic event."),
    RawNewsItem("[GBP] UK CPI y/y Actual: 3.1% (Forecast: 2.9%)", "Economic Calendar",
                summary="Impact: High. UK economic event."),
    RawNewsItem("[EUR] German Manufacturing PMI Actual: 48.2 (Forecast: 47.8)", "Economic Calendar",
                summary="Impact: Medium. Eurozone economic event."),

    # Risk sentiment (maps to JPY)
    RawNewsItem("Global risk sentiment sours as trade war rhetoric escalates", "GDELT",
                published_at=datetime(2026, 3, 19, 17, 0, tzinfo=timezone.utc)),

    # Near-duplicate (should be caught by dedup)
    RawNewsItem("ECB keeps rates steady, Lagarde cautious on inflation", "GDELT",
                published_at=datetime(2026, 3, 19, 9, 0, tzinfo=timezone.utc)),
    RawNewsItem("Gold price surges past $3100 amid Middle East geopolitical tensions", "BBC Business",
                published_at=datetime(2026, 3, 19, 11, 15, tzinfo=timezone.utc)),

    # Unrelated (should not map)
    RawNewsItem("Apple announces new MacBook Pro with M5 chip", "BBC Business",
                published_at=datetime(2026, 3, 19, 18, 0, tzinfo=timezone.utc)),
    RawNewsItem("SpaceX Starship completes first orbital refuelling test", "Reuters",
                published_at=datetime(2026, 3, 19, 19, 0, tzinfo=timezone.utc)),
]


def main():
    instruments = load_instruments()

    print("=" * 70)
    print("  FOREX SENTINEL — News Categorization Pipeline")
    print("=" * 70)

    raw_items = SAMPLE_NEWS
    print(f"\n  Raw items ingested: {len(raw_items)}")

    # Deduplicate
    items = deduplicate_headlines(raw_items)
    removed = len(raw_items) - len(items)
    print(f"  After dedup:        {len(items)}  ({removed} duplicates removed)")

    # By source
    sources = {}
    for item in items:
        sources.setdefault(item.source, []).append(item)

    print(f"\n  {'SOURCE':<25} {'COUNT':>5}")
    print(f"  {'-' * 32}")
    for source, source_items in sorted(sources.items()):
        print(f"    {source:<23} {len(source_items):>5}")

    # Map to instruments
    mapper = InstrumentMapper(instruments)
    headlines = [item.headline for item in items]
    instrument_map = mapper.map_headlines(headlines)

    # Track mapped vs unmapped
    mapped_headlines = set()
    for inst_headlines in instrument_map.values():
        mapped_headlines.update(inst_headlines)
    unmapped = [item for item in items if item.headline not in mapped_headlines]

    print(f"\n{'=' * 70}")
    print(f"  INSTRUMENT CATEGORIZATION")
    print(f"{'=' * 70}")
    print(f"\n  Mapped:   {len(mapped_headlines)} headlines -> {len(instrument_map)} instruments")
    print(f"  Unmapped: {len(unmapped)} headlines (no keyword match)")

    # Build headline->item lookup for timestamps
    headline_to_item = {item.headline: item for item in items}

    for instrument in sorted(instrument_map.keys()):
        inst_headlines = instrument_map[instrument]
        display = instruments.get(instrument, {}).get("display_name", instrument)
        itype = instruments.get(instrument, {}).get("type", "unknown")
        print(f"\n  [{itype.upper()}] {display} ({instrument}) — {len(inst_headlines)} headlines")
        print(f"  {'─' * 60}")
        for h in inst_headlines:
            item = headline_to_item.get(h)
            time_str = item.published_at.strftime("%H:%M") if item and item.published_at else "     "
            src = item.source[:12] if item else ""
            print(f"    {time_str}  {src:<13} {h[:70]}")

    if unmapped:
        print(f"\n  [UNMAPPED] No instrument match — {len(unmapped)} headlines")
        print(f"  {'─' * 60}")
        for item in unmapped:
            time_str = item.published_at.strftime("%H:%M") if item.published_at else "     "
            print(f"    {time_str}  {item.source:<13} {item.headline[:70]}")

    # Summary
    print(f"\n{'=' * 70}")
    print(f"  PIPELINE SUMMARY")
    print(f"{'=' * 70}")
    print(f"  Total fetched:      {len(raw_items)}")
    print(f"  After dedup:        {len(items)}")
    print(f"  Mapped to trades:   {len(mapped_headlines)}")
    print(f"  Discarded:          {len(unmapped)}")
    print(f"  Instruments active: {len(instrument_map)}")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
