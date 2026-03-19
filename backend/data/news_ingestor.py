"""News ingestor — fetches from RSS, GDELT, and economic calendar."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("forex_sentinel.news")


@dataclass
class RawNewsItem:
    headline: str
    source: str
    url: str | None = None
    summary: str | None = None
    published_at: datetime | None = None


class NewsIngestor:
    """Fetches news from multiple free sources."""

    def __init__(self, config: dict):
        self.config = config
        self.stream_cfg = config.get("streams", {}).get("news_stream", {})
        self.sources = self.stream_cfg.get("news_sources", [])

    async def fetch_all(self) -> list[RawNewsItem]:
        """Fetch news from all configured sources."""
        items: list[RawNewsItem] = []

        for source in self.sources:
            source_type = source.get("type", "")
            try:
                if source_type == "rss":
                    items.extend(await self._fetch_rss(source))
                elif source_type == "gdelt":
                    if source.get("enabled", True):
                        items.extend(await self._fetch_gdelt())
                elif source_type == "economic_calendar":
                    items.extend(await self._fetch_calendar(source))
            except Exception as e:
                logger.warning(f"Failed to fetch from {source_type}/{source.get('name', 'unknown')}: {e}")

        logger.info(f"Fetched {len(items)} total news items from {len(self.sources)} sources")
        return items

    async def _fetch_rss(self, source: dict) -> list[RawNewsItem]:
        """Fetch and parse RSS feed."""
        import aiohttp
        import feedparser

        url = source.get("url", "")
        name = source.get("name", "RSS")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status != 200:
                        logger.warning(f"RSS {name} returned status {resp.status}")
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

        items = []
        for entry in entries:
            published = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                try:
                    published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                except Exception:
                    pass
            title = entry.get("title", "").strip() if isinstance(entry, dict) else getattr(entry, "title", "").strip()
            link = entry.get("link") if isinstance(entry, dict) else getattr(entry, "link", None)
            summary = entry.get("summary", "") if isinstance(entry, dict) else getattr(entry, "summary", "")

            items.append(RawNewsItem(
                headline=title,
                source=name,
                url=link,
                summary=summary[:500] if summary else None,
                published_at=published,
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

    async def _fetch_gdelt(self) -> list[RawNewsItem]:
        """Fetch from GDELT Project API."""
        import aiohttp
        import json

        url = (
            "http://api.gdeltproject.org/api/v2/doc/doc"
            "?query=forex+OR+economy+OR+central+bank+OR+interest+rate"
            "&mode=artlist&maxrecords=30&format=json"
        )

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status != 200:
                        return []
                    data = await resp.json(content_type=None)
        except Exception as e:
            logger.warning(f"GDELT fetch failed: {e}")
            return []

        items = []
        articles = data.get("articles", [])
        for article in articles[:20]:
            published = None
            if article.get("seendate"):
                try:
                    published = datetime.strptime(
                        article["seendate"][:14], "%Y%m%dT%H%M%S"
                    ).replace(tzinfo=timezone.utc)
                except Exception:
                    pass

            items.append(RawNewsItem(
                headline=article.get("title", "").strip(),
                source="GDELT",
                url=article.get("url"),
                published_at=published,
            ))

        logger.info(f"GDELT: {len(items)} items")
        return items

    async def _fetch_calendar(self, source: dict) -> list[RawNewsItem]:
        """Fetch economic calendar from ForexFactory."""
        import aiohttp

        url = source.get("url", "https://nfs.faireconomy.media/ff_calendar_thisweek.json")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status != 200:
                        return []
                    data = await resp.json(content_type=None)
        except Exception as e:
            logger.warning(f"Calendar fetch failed: {e}")
            return []

        items = []
        if not isinstance(data, list):
            return items

        for event in data[:30]:
            title = event.get("title", "")
            country = event.get("country", "")
            impact = event.get("impact", "")
            actual = event.get("actual", "")
            forecast = event.get("forecast", "")

            if impact not in ("High", "Medium"):
                continue

            headline = f"[{country}] {title}"
            if actual:
                headline += f" Actual: {actual}"
                if forecast:
                    headline += f" (Forecast: {forecast})"

            items.append(RawNewsItem(
                headline=headline,
                source="Economic Calendar",
                summary=f"Impact: {impact}. {country} economic event.",
            ))

        logger.info(f"Calendar: {len(items)} high/medium impact events")
        return items


def deduplicate_headlines(items: list[RawNewsItem]) -> list[RawNewsItem]:
    """Remove near-duplicate headlines using simple string similarity."""
    if not items:
        return items

    unique: list[RawNewsItem] = []
    seen_normalized: set[str] = set()

    for item in items:
        normalized = item.headline.lower().strip()
        # Simple token-based dedup
        tokens = frozenset(normalized.split())
        is_dup = False
        for seen in seen_normalized:
            seen_tokens = frozenset(seen.split())
            overlap = len(tokens & seen_tokens) / max(len(tokens | seen_tokens), 1)
            if overlap > 0.7:
                is_dup = True
                break
        if not is_dup:
            unique.append(item)
            seen_normalized.add(normalized)

    removed = len(items) - len(unique)
    if removed > 0:
        logger.info(f"Dedup removed {removed} duplicate headlines")
    return unique
