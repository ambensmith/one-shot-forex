"""News Stream — ingests headlines, runs LLM analysis, trades on signals."""

from __future__ import annotations

import logging
from pathlib import Path

from backend.streams.base_stream import BaseStream, StreamSignal

logger = logging.getLogger("forex_sentinel.news_stream")


class NewsStream(BaseStream):
    def __init__(self, config: dict, db, broker, risk, executor):
        super().__init__("news", config, db, broker, risk, executor)
        self.stream_config = config.get("streams", {}).get("news_stream", {})

    async def tick(self) -> list[StreamSignal]:
        """Fetch news, map to instruments, analyze with LLM, trade."""
        from backend.data.news_ingestor import NewsIngestor, deduplicate_headlines
        from backend.signals.instrument_mapper import InstrumentMapper
        from backend.signals.llm_client import UnifiedLLMClient, parse_llm_signal

        signals: list[StreamSignal] = []

        # Check and close existing trades
        self.executor.check_and_close_trades(self.stream_id)

        # 1. Fetch news
        ingestor = NewsIngestor(self.config)
        raw_items = await ingestor.fetch_all()

        if not raw_items:
            logger.info("No news items fetched. Skipping cycle.")
            self.record_equity()
            return signals

        # 2. Deduplicate
        raw_items = deduplicate_headlines(raw_items)

        # 3. Store news items and map to instruments
        mapper = InstrumentMapper(self.config.get("instruments"))
        allowed_instruments = set(self.stream_config.get("instruments", []))

        for item in raw_items:
            mapped = mapper.map_headline(item.headline)
            filtered_mapped = [m for m in mapped if m in allowed_instruments]

            if not self.db.headline_exists(item.headline):
                self.db.insert_news_item(
                    headline=item.headline,
                    source=item.source,
                    url=item.url,
                    summary=item.summary,
                    mapped_instruments=filtered_mapped,
                    published_at=item.published_at.isoformat() if item.published_at else None,
                )

        # 4. Build instrument -> headlines mapping
        headline_to_item = {item.headline: item for item in raw_items}
        headlines = [item.headline for item in raw_items]
        instrument_headlines = mapper.map_headlines(headlines)

        # 5. Create LLM client
        llm_cfg = self.stream_config.get("llm", {})
        primary_model = llm_cfg.get("signal_model", "groq/llama-4-scout")
        min_confidence = self.stream_config.get("min_confidence", 0.60)

        try:
            primary_client = UnifiedLLMClient.from_model_key(primary_model)
        except ValueError as e:
            logger.warning(f"Primary LLM not available: {e}. Skipping news analysis.")
            self.record_equity()
            return signals

        # Load prompt template
        prompt_template = self._load_prompt_template()

        # 6. Analyze each instrument with relevant news
        for instrument, inst_headlines in instrument_headlines.items():
            if instrument not in allowed_instruments:
                continue

            try:
                # Get market context
                df = self.broker.get_candles(instrument, count=50)
                price_data = self.broker.get_current_price(instrument)
                current_price = price_data["mid"]

                daily_change = 0.0
                if len(df) >= 24:
                    daily_change = ((df["Close"].iloc[-1] / df["Close"].iloc[-24]) - 1) * 100

                trend = "ranging"
                if len(df) >= 20:
                    sma20 = df["Close"].rolling(20).mean().iloc[-1]
                    if current_price > sma20 * 1.002:
                        trend = "bullish"
                    elif current_price < sma20 * 0.998:
                        trend = "bearish"

                # Build prompt
                prompt = prompt_template.format(
                    instrument=instrument,
                    news_headlines="\n".join(
                        f"- {h} [{headline_to_item[h].source_count} source{'s' if headline_to_item[h].source_count > 1 else ''}: {', '.join(headline_to_item[h].sources)}]"
                        if h in headline_to_item else f"- {h} [1 source]"
                        for h in inst_headlines[:10]
                    ),
                    current_price=f"{current_price:.5f}",
                    daily_change=f"{daily_change:.2f}",
                    trend_description=trend,
                    time_horizon="4-8 hours",
                )

                # Primary model analysis
                response = primary_client.analyze(prompt)
                signal_data = parse_llm_signal(response)

                stream_signal = StreamSignal(
                    stream_id=self.stream_id,
                    instrument=instrument,
                    direction=signal_data["direction"],
                    confidence=signal_data["confidence"],
                    sources=[primary_model],
                    reasoning=signal_data.get("reasoning", ""),
                    metadata={
                        "headlines": inst_headlines[:5],
                        "key_factors": signal_data.get("key_factors", []),
                        "model": primary_model,
                    },
                )
                signals.append(stream_signal)
                signal_id = self.record_signal(stream_signal, source=primary_model)

                # Trade decision
                if signal_data["direction"] == "neutral":
                    continue
                if signal_data["confidence"] < min_confidence:
                    self.db.execute(
                        "UPDATE signals SET rejection_reason = ? WHERE id = ?",
                        (f"Below threshold ({signal_data['confidence']} < {min_confidence})", signal_id),
                    )
                    self.db.commit()
                    continue

                # Risk check
                stop_loss = self.risk.calculate_stop_loss(
                    instrument, current_price, signal_data["direction"], df
                )
                take_profit = self.risk.calculate_take_profit(
                    current_price, stop_loss, signal_data["direction"]
                )
                risk_check = self.risk.check_trade(
                    self.stream_id, instrument, signal_data["direction"],
                    current_price, stop_loss,
                )

                if not risk_check.approved:
                    self.db.execute(
                        "UPDATE signals SET rejection_reason = ? WHERE id = ?",
                        (risk_check.rejection_reason, signal_id),
                    )
                    self.db.commit()
                    logger.info(f"Trade rejected: {instrument} — {risk_check.rejection_reason}")
                    continue

                # Execute
                self.executor.execute_trade(
                    stream_id=self.stream_id,
                    instrument=instrument,
                    direction=signal_data["direction"],
                    entry_price=current_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    position_size=risk_check.position_size,
                    signal_ids=[signal_id],
                )

            except Exception as e:
                logger.error(f"Error analyzing {instrument}: {e}")

        self.record_equity()
        logger.info(f"News stream tick complete. {len(signals)} signals generated.")
        return signals

    @staticmethod
    def _load_prompt_template() -> str:
        path = Path("config/prompts/forex_signal.txt")
        if path.exists():
            return path.read_text()
        # Fallback minimal prompt
        return (
            "Analyze these news headlines for {instrument}:\n"
            "{news_headlines}\n"
            "Current price: {current_price}, 24h change: {daily_change}%, trend: {trend_description}\n"
            "Time horizon: {time_horizon}\n"
            'Respond in JSON: {{"direction": "long"|"short"|"neutral", '
            '"confidence": 0.0-1.0, "reasoning": "...", "key_factors": []}}'
        )
