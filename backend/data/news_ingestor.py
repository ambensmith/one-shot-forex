"""News ingestor — fetches from Finnhub, RSS feeds, and economic calendar."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger("forex_sentinel.news")

# Words that indicate market direction — headlines differing in these
# must NOT be deduplicated even if token overlap is high.
DIRECTIONAL_WORDS = frozenset({
    "raise", "raises", "raised", "raising",
    "cut", "cuts", "cutting",
    "hike", "hikes", "hiking",
    "ease", "eases", "easing",
    "hawkish", "dovish",
    "tighten", "tightens", "tightening",
    "loosen", "loosens", "loosening",
    "surge", "surges", "surging",
    "plunge", "plunges", "plunging",
    "rally", "rallies", "rallying",
    "crash", "crashes", "crashing",
    "rise", "rises", "rising",
    "fall", "falls", "falling",
    "drop", "drops", "dropping",
    "jump", "jumps", "jumping",
    "climb", "climbs", "climbing",
    "slide", "slides", "sliding",
    "increase", "increases", "increasing",
    "decrease", "decreases", "decreasing",
})


@dataclass
class RawNewsItem:
    headline: str
    source: str
    url: str | None = None
    summary: str | None = None
    content: str | None = None
    published_at: datetime | None = None
    category: str | None = None
    image_url: str | None = None
    sentiment_score: float | None = None
    source_metadata: dict[str, Any] | None = None
    source_count: int = 1
    sources: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.sources:
            self.sources = [self.source]


class NewsIngestor:
    """Fetches news from multiple free sources."""

    def __init__(self, config: dict):
        self.config = config
        self.stream_cfg = config.get("streams", {}).get("news_stream", {})
        self.sources = self.stream_cfg.get("news_sources", [])
        self.lookback_hours = self.stream_cfg.get("news_lookback_hours", 4)
        self.dedup_threshold = self.stream_cfg.get("dedup_threshold", 0.80)

        # Finnhub config
        finnhub_cfg = config.get("finnhub", {})
        self._finnhub_base_url = finnhub_cfg.get("base_url", "https://finnhub.io/api/v1")
        api_key_env = finnhub_cfg.get("api_key_env", "FINNHUB_API_KEY")
        self._finnhub_api_key = os.environ.get(api_key_env, "")

    async def fetch_all(self) -> list[RawNewsItem]:
        """Fetch news from all configured sources."""
        items: list[RawNewsItem] = []

        for source in self.sources:
            source_type = source.get("type", "")
            if not source.get("enabled", True):
                continue
            try:
                if source_type == "rss":
                    items.extend(await self._fetch_rss(source))
                elif source_type == "finnhub":
                    items.extend(await self._fetch_finnhub_news(source))
                elif source_type == "finnhub_calendar":
                    items.extend(await self._fetch_finnhub_calendar(source))
            except Exception as e:
                logger.warning(f"Failed to fetch from {source_type}/{source.get('name', 'unknown')}: {e}")

        logger.info(f"Fetched {len(items)} total news items from {len(self.sources)} sources")
        return items

    # ── Finnhub ────────────────────────────────────────────────

    async def _fetch_finnhub_news(self, source: dict) -> list[RawNewsItem]:
        """Fetch general/forex news from Finnhub API."""
        import aiohttp

        if not self._finnhub_api_key:
            logger.warning("FINNHUB_API_KEY not set, skipping Finnhub news")
            return []

        name = source.get("name", "Finnhub News")
        cutoff = datetime.now(timezone.utc) - timedelta(hours=self.lookback_hours)
        items: list[RawNewsItem] = []

        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self._finnhub_base_url}/news?category=forex&token={self._finnhub_api_key}"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status != 200:
                        body = await resp.text()
                        logger.warning(f"Finnhub news returned status {resp.status}: {body[:200]}")
                        return []
                    data = await resp.json(content_type=None)
        except Exception as e:
            logger.warning(f"Finnhub news fetch failed: {type(e).__name__}: {e}")
            return []

        if not isinstance(data, list):
            logger.warning(f"Finnhub news returned unexpected format: {type(data)}")
            return []

        for article in data:
            published = None
            ts = article.get("datetime")
            if ts:
                try:
                    published = datetime.fromtimestamp(ts, tz=timezone.utc)
                except (ValueError, OSError):
                    pass

            # Skip items older than lookback window
            if published and published < cutoff:
                continue

            headline_text = article.get("headline", "").strip()
            if not headline_text:
                continue

            items.append(RawNewsItem(
                headline=headline_text,
                source=name,
                url=article.get("url"),
                summary=article.get("summary", "")[:500] or None,
                image_url=article.get("image") or None,
                published_at=published,
                category=article.get("category"),
                source_metadata=article,
            ))

        logger.info(f"Finnhub news: {len(items)} items")
        return items

    async def _fetch_finnhub_calendar(self, source: dict) -> list[RawNewsItem]:
        """Fetch economic calendar from Finnhub API."""
        import aiohttp

        if not self._finnhub_api_key:
            logger.warning("FINNHUB_API_KEY not set, skipping Finnhub calendar")
            return []

        name = source.get("name", "Finnhub Calendar")
        items: list[RawNewsItem] = []

        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self._finnhub_base_url}/calendar/economic?token={self._finnhub_api_key}"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status != 200:
                        body = await resp.text()
                        logger.warning(f"Finnhub calendar returned status {resp.status}: {body[:200]}")
                        return []
                    data = await resp.json(content_type=None)
        except Exception as e:
            logger.warning(f"Finnhub calendar fetch failed: {type(e).__name__}: {e}")
            return []

        events = data.get("economicCalendar", []) if isinstance(data, dict) else []

        for event in events:
            impact = event.get("impact", "")
            if impact not in ("high", "medium", 3, 2):
                continue

            country = event.get("country", "")
            title = event.get("event", "")
            actual = event.get("actual", "")
            estimate = event.get("estimate", "")
            prev = event.get("prev", "")

            impact_label = "HIGH IMPACT" if impact in ("high", 3) else "MEDIUM IMPACT"
            headline_text = f"[{impact_label}] {country} {title}"
            if actual not in (None, ""):
                headline_text += f" — Actual: {actual}"
                parts = []
                if estimate not in (None, ""):
                    parts.append(f"Forecast: {estimate}")
                if prev not in (None, ""):
                    parts.append(f"Previous: {prev}")
                if parts:
                    headline_text += f" ({', '.join(parts)})"

            summary = f"Impact: {impact_label}. {country} economic event."

            items.append(RawNewsItem(
                headline=headline_text,
                source=name,
                summary=summary,
                category="economic_calendar",
                source_metadata=event,
            ))

        logger.info(f"Finnhub calendar: {len(items)} high/medium impact events")
        return items

    # ── RSS ────────────────────────────────────────────────────

    async def _fetch_rss(self, source: dict) -> list[RawNewsItem]:
        """Fetch and parse RSS feed."""
        import aiohttp

        url = source.get("url", "")
        name = source.get("name", "RSS")
        category = source.get("category")

        headers = {"User-Agent": "ForexSentinel/1.0 (news aggregator)"}

        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status != 200:
                        body = await resp.text()
                        logger.warning(f"RSS {name} returned status {resp.status}: {body[:200]}")
                        return []
                    content = await resp.text()
        except Exception as e:
            logger.warning(f"RSS fetch failed for {name}: {e}")
            return []

        try:
            import feedparser
            feed = feedparser.parse(content)
            entries = feed.entries[:20]
        except ImportError:
            entries = self._parse_rss_xml(content)

        cutoff = datetime.now(timezone.utc) - timedelta(hours=self.lookback_hours)
        items = []
        for entry in entries:
            published = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                try:
                    published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                except Exception:
                    pass

            # Skip items definitively older than lookback window
            if published and published < cutoff:
                continue

            title = entry.get("title", "").strip() if isinstance(entry, dict) else getattr(entry, "title", "").strip()
            link = entry.get("link") if isinstance(entry, dict) else getattr(entry, "link", None)
            summary = entry.get("summary", "") if isinstance(entry, dict) else getattr(entry, "summary", "")
            entry_content = entry.get("content", "") if isinstance(entry, dict) else getattr(entry, "content", "")

            if not title:
                continue

            # feedparser content is a list of dicts with 'value' key
            content_text = None
            if isinstance(entry_content, list) and entry_content:
                content_text = entry_content[0].get("value", "")[:2000] or None
            elif isinstance(entry_content, str) and entry_content:
                content_text = entry_content[:2000]

            # Build source_metadata from the raw entry
            if isinstance(entry, dict):
                metadata = entry
            else:
                metadata = {k: v for k, v in entry.items() if isinstance(v, (str, int, float, bool, list))}

            items.append(RawNewsItem(
                headline=title,
                source=name,
                url=link,
                summary=summary[:500] if summary else None,
                content=content_text,
                published_at=published,
                category=category,
                source_metadata=metadata,
            ))

        logger.info(f"RSS {name}: {len(items)} items")
        return items

    @staticmethod
    def _parse_rss_xml(content: str) -> list[dict]:
        """Fallback RSS parser using stdlib xml.etree."""
        import xml.etree.ElementTree as ET
        items = []
        try:
            root = ET.fromstring(content)
            for item in root.iter("item"):
                title_el = item.find("title")
                link_el = item.find("link")
                desc_el = item.find("description")
                items.append({
                    "title": title_el.text.strip() if title_el is not None and title_el.text else "",
                    "link": link_el.text.strip() if link_el is not None and link_el.text else None,
                    "summary": desc_el.text.strip() if desc_el is not None and desc_el.text else "",
                })
        except ET.ParseError:
            pass
        return items[:20]


# ── Deduplication ──────────────────────────────────────────


def deduplicate_headlines(
    items: list[RawNewsItem],
    threshold: float = 0.80,
) -> list[RawNewsItem]:
    """Deduplicate headlines using token overlap with directional word protection.

    Two headlines are merged if their token overlap exceeds `threshold`,
    UNLESS they differ in directional words (e.g. "raise" vs "cut"),
    which would indicate opposite market signals.
    """
    if not items:
        return items

    unique: list[RawNewsItem] = []
    seen_token_sets: list[frozenset[str]] = []

    for item in items:
        normalized = item.headline.lower().strip()
        tokens = frozenset(normalized.split())
        directional = tokens & DIRECTIONAL_WORDS

        merged_index = -1
        for i, seen in enumerate(seen_token_sets):
            overlap = len(tokens & seen) / max(len(tokens | seen), 1)
            if overlap > threshold:
                # Check directional word protection
                seen_directional = seen & DIRECTIONAL_WORDS
                if directional != seen_directional:
                    # Different directional words — do not merge
                    continue
                merged_index = i
                break

        if merged_index >= 0:
            if item.source not in unique[merged_index].sources:
                unique[merged_index].sources.append(item.source)
                unique[merged_index].source_count = len(unique[merged_index].sources)
        else:
            unique.append(item)
            seen_token_sets.append(tokens)

    merged = len(items) - len(unique)
    multi_source = sum(1 for u in unique if u.source_count > 1)
    if merged > 0:
        logger.info(f"Dedup merged {merged} duplicates. {multi_source} headlines confirmed by multiple sources.")
    return unique


# ── Conversion ─────────────────────────────────────────────


def to_headline(item: RawNewsItem):
    """Convert a RawNewsItem to a Headline model for DB insertion."""
    from backend.core.models import Headline

    return Headline(
        headline=item.headline,
        summary=item.summary,
        content=item.content,
        source=item.source,
        source_url=item.url,
        image_url=item.image_url,
        category=item.category,
        published_at=item.published_at,
        sentiment_score=item.sentiment_score,
        source_metadata=item.source_metadata,
    )


# ── Pipeline orchestrator ──────────────────────────────────


async def ingest_pipeline(config: dict, db) -> dict:
    """Full ingest pipeline: fetch all sources, dedup, convert, store.

    Returns summary dict with counts.
    """
    ingestor = NewsIngestor(config)
    raw_items = await ingestor.fetch_all()
    fetched = len(raw_items)

    deduped = deduplicate_headlines(raw_items, threshold=ingestor.dedup_threshold)
    after_dedup = len(deduped)

    new_inserted = 0
    skipped_existing = 0

    for item in deduped:
        if db.headline_exists(item.headline):
            skipped_existing += 1
            continue

        headline = to_headline(item)
        db.insert_headline(headline)
        new_inserted += 1

    summary = {
        "fetched": fetched,
        "after_dedup": after_dedup,
        "new_inserted": new_inserted,
        "skipped_existing": skipped_existing,
    }
    logger.info(f"Ingest pipeline complete: {summary}")
    return summary
