"""Hybrid Stream — user-defined recipes combining news + strategies."""

from __future__ import annotations

import logging
from typing import Any

from backend.streams.base_stream import BaseStream, StreamSignal

logger = logging.getLogger("forex_sentinel.hybrid_stream")


class HybridStream(BaseStream):
    """Combines news signals and strategy signals with configurable combiner logic."""

    def __init__(self, hybrid_config: dict, config: dict, db, oanda, risk, executor):
        stream_id = f"hybrid:{hybrid_config['name']}"
        super().__init__(stream_id, config, db, oanda, risk, executor)
        self.hybrid_config = hybrid_config
        self.modules = hybrid_config.get("modules", [])
        self.combiner_mode = hybrid_config.get("combiner_mode", "weighted")
        self.instruments = hybrid_config.get("instruments", [])
        self.min_confidence = 0.60

    async def tick(self) -> list[StreamSignal]:
        """Run all modules and combine their signals."""
        signals: list[StreamSignal] = []

        # Check and close existing trades
        self.executor.check_and_close_trades(self.stream_id)

        for instrument in self.instruments:
            try:
                module_signals = await self._gather_module_signals(instrument)

                if not module_signals:
                    continue

                # Check must_participate constraints
                if not self._check_must_participate(module_signals):
                    continue

                # Combine signals
                combined = self._combine_signals(instrument, module_signals)

                if combined is None or combined.direction == "neutral":
                    continue

                # Record signal
                signal_id = self.record_signal(combined, source=f"hybrid:{self.hybrid_config['name']}")
                signals.append(combined)

                if combined.confidence < self.min_confidence:
                    self.db.execute(
                        "UPDATE signals SET rejection_reason = ? WHERE id = ?",
                        (f"Below threshold ({combined.confidence} < {self.min_confidence})", signal_id),
                    )
                    self.db.commit()
                    continue

                # Get price and risk check
                df = self.oanda.get_candles(instrument, count=50)
                price_data = self.oanda.get_current_price(instrument)
                entry_price = price_data["mid"]

                stop_loss = self.risk.calculate_stop_loss(
                    instrument, entry_price, combined.direction, df
                )
                take_profit = self.risk.calculate_take_profit(
                    entry_price, stop_loss, combined.direction
                )
                risk_check = self.risk.check_trade(
                    self.stream_id, instrument, combined.direction,
                    entry_price, stop_loss,
                )

                if not risk_check.approved:
                    self.db.execute(
                        "UPDATE signals SET rejection_reason = ? WHERE id = ?",
                        (risk_check.rejection_reason, signal_id),
                    )
                    self.db.commit()
                    continue

                self.executor.execute_trade(
                    stream_id=self.stream_id,
                    instrument=instrument,
                    direction=combined.direction,
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    position_size=risk_check.position_size,
                    signal_ids=[signal_id],
                )

            except Exception as e:
                logger.error(f"Hybrid error on {instrument}: {e}")

        self.record_equity()
        logger.info(f"Hybrid stream '{self.hybrid_config['name']}' tick complete. {len(signals)} signals.")
        return signals

    async def _gather_module_signals(self, instrument: str) -> list[dict]:
        """Gather signals from all configured modules."""
        results = []

        for module in self.modules:
            mod_type = module.get("type", "")
            mod_name = module.get("name", "")
            weight = module.get("weight", 0.5)

            try:
                if mod_type == "news":
                    signal = await self._get_news_signal(instrument)
                elif mod_type == "strategy":
                    signal = self._get_strategy_signal(instrument, mod_name)
                else:
                    continue

                if signal:
                    results.append({
                        "module": module,
                        "direction": signal.direction,
                        "confidence": signal.confidence,
                        "weight": weight,
                        "must_participate": module.get("must_participate", False),
                    })
            except Exception as e:
                logger.warning(f"Module {mod_name} failed for {instrument}: {e}")

        return results

    async def _get_news_signal(self, instrument: str) -> StreamSignal | None:
        """Get the latest news signal for an instrument."""
        row = self.db.execute(
            """SELECT * FROM signals
               WHERE stream = 'news' AND instrument = ? AND is_comparison = 0
               ORDER BY created_at DESC LIMIT 1""",
            (instrument,),
        ).fetchone()

        if row:
            r = dict(row)
            return StreamSignal(
                stream_id="news", instrument=instrument,
                direction=r["direction"], confidence=r["confidence"],
                reasoning=r.get("reasoning", ""),
            )
        return None

    def _get_strategy_signal(self, instrument: str, strategy_name: str) -> StreamSignal | None:
        """Run a strategy and return its signal."""
        from backend.strategies.registry import get_strategy

        strategy = get_strategy(strategy_name)
        df = self.oanda.get_candles(
            instrument,
            granularity=self.config.get("data", {}).get("candle_granularity", "H1"),
            count=self.config.get("data", {}).get("lookback_periods", 200),
        )

        if df.empty:
            return None

        tech = strategy.analyze(df, instrument)
        return StreamSignal(
            stream_id="strategy", instrument=instrument,
            direction=tech.direction, confidence=tech.confidence,
            sources=[strategy_name],
        )

    def _check_must_participate(self, module_signals: list[dict]) -> bool:
        """Check that all must_participate modules produced non-neutral signals."""
        for ms in module_signals:
            if ms["must_participate"] and ms["direction"] == "neutral":
                return False
        return True

    def _combine_signals(self, instrument: str,
                          module_signals: list[dict]) -> StreamSignal | None:
        """Combine module signals using the configured combiner mode."""
        if not module_signals:
            return None

        if self.combiner_mode == "all_agree":
            return self._combine_all_agree(instrument, module_signals)
        elif self.combiner_mode == "majority":
            return self._combine_majority(instrument, module_signals)
        elif self.combiner_mode == "weighted":
            return self._combine_weighted(instrument, module_signals)
        elif self.combiner_mode == "any":
            return self._combine_any(instrument, module_signals)
        else:
            return self._combine_weighted(instrument, module_signals)

    def _combine_all_agree(self, instrument: str, signals: list[dict]) -> StreamSignal | None:
        """All non-neutral modules must agree on direction."""
        non_neutral = [s for s in signals if s["direction"] != "neutral"]
        if not non_neutral:
            return None

        directions = set(s["direction"] for s in non_neutral)
        if len(directions) != 1:
            return None

        direction = directions.pop()
        avg_confidence = sum(s["confidence"] for s in non_neutral) / len(non_neutral)

        return StreamSignal(
            stream_id=self.stream_id, instrument=instrument,
            direction=direction, confidence=avg_confidence,
            sources=[s["module"]["name"] for s in signals],
            reasoning=f"All {len(non_neutral)} modules agree: {direction}",
        )

    def _combine_majority(self, instrument: str, signals: list[dict]) -> StreamSignal | None:
        """Majority of non-neutral modules agree."""
        non_neutral = [s for s in signals if s["direction"] != "neutral"]
        if not non_neutral:
            return None

        long_count = sum(1 for s in non_neutral if s["direction"] == "long")
        short_count = sum(1 for s in non_neutral if s["direction"] == "short")
        total = len(non_neutral)

        if long_count > total / 2:
            direction = "long"
        elif short_count > total / 2:
            direction = "short"
        else:
            return None

        matching = [s for s in non_neutral if s["direction"] == direction]
        avg_confidence = sum(s["confidence"] for s in matching) / len(matching)

        return StreamSignal(
            stream_id=self.stream_id, instrument=instrument,
            direction=direction, confidence=avg_confidence,
            sources=[s["module"]["name"] for s in signals],
            reasoning=f"Majority ({len(matching)}/{total}): {direction}",
        )

    def _combine_weighted(self, instrument: str, signals: list[dict]) -> StreamSignal | None:
        """Weighted sum of directional signals."""
        score = 0.0
        total_weight = 0.0

        for s in signals:
            dir_val = {"long": 1.0, "short": -1.0, "neutral": 0.0}.get(s["direction"], 0)
            score += dir_val * s["confidence"] * s["weight"]
            total_weight += s["weight"]

        if total_weight == 0:
            return None

        normalized = score / total_weight
        threshold = 0.2

        if normalized > threshold:
            direction = "long"
        elif normalized < -threshold:
            direction = "short"
        else:
            return None

        confidence = min(abs(normalized), 1.0)

        return StreamSignal(
            stream_id=self.stream_id, instrument=instrument,
            direction=direction, confidence=round(confidence, 3),
            sources=[s["module"]["name"] for s in signals],
            reasoning=f"Weighted score: {normalized:.3f}",
        )

    def _combine_any(self, instrument: str, signals: list[dict]) -> StreamSignal | None:
        """Any single module above confidence triggers."""
        best = None
        for s in signals:
            if s["direction"] != "neutral" and s["confidence"] >= self.min_confidence:
                if best is None or s["confidence"] > best["confidence"]:
                    best = s

        if best is None:
            return None

        return StreamSignal(
            stream_id=self.stream_id, instrument=instrument,
            direction=best["direction"], confidence=best["confidence"],
            sources=[best["module"]["name"]],
            reasoning=f"Triggered by {best['module']['name']} ({best['confidence']:.2f})",
        )
