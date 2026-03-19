"""Maps news headlines to instruments via keyword matching."""

from __future__ import annotations

import logging

from backend.core.config import load_instruments

logger = logging.getLogger("forex_sentinel.mapper")


class InstrumentMapper:
    def __init__(self, instruments: dict | None = None):
        self.instruments = instruments or load_instruments()

    def map_headline(self, headline: str) -> list[str]:
        """Match a headline to relevant instruments using keyword lists."""
        headline_lower = headline.lower()
        matched = []

        for symbol, info in self.instruments.items():
            keywords = info.get("keywords", [])
            for keyword in keywords:
                if keyword.lower() in headline_lower:
                    matched.append(symbol)
                    break  # One match per instrument is enough

        return matched

    def map_headlines(self, headlines: list[str]) -> dict[str, list[str]]:
        """Map multiple headlines, returning instrument -> [headlines] mapping."""
        instrument_headlines: dict[str, list[str]] = {}

        for headline in headlines:
            instruments = self.map_headline(headline)
            for inst in instruments:
                if inst not in instrument_headlines:
                    instrument_headlines[inst] = []
                instrument_headlines[inst].append(headline)

        return instrument_headlines
