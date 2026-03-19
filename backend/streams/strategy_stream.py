"""Strategy Stream — runs peer-reviewed mechanical strategies."""

from __future__ import annotations

import logging

from backend.streams.base_stream import BaseStream, StreamSignal

logger = logging.getLogger("forex_sentinel.strategy_stream")


class StrategyStream(BaseStream):
    def __init__(self, config: dict, db, broker, risk, executor):
        super().__init__("strategy", config, db, broker, risk, executor)
        self.stream_config = config.get("streams", {}).get("strategy_stream", {})

    async def tick(self) -> list[StreamSignal]:
        """Run all enabled strategies across configured instruments."""
        from backend.strategies.registry import get_strategy

        strategies_cfg = self.stream_config.get("strategies", [])
        instruments = self.stream_config.get("instruments", [])
        min_confidence = self.stream_config.get("min_confidence", 0.60)
        signals: list[StreamSignal] = []

        # Check and close existing trades
        self.executor.check_and_close_trades(self.stream_id)

        for strat_cfg in strategies_cfg:
            if not strat_cfg.get("enabled", True):
                continue

            strat_name = strat_cfg["name"]
            try:
                strategy = get_strategy(strat_name, strat_cfg.get("params"))
            except ValueError as e:
                logger.warning(str(e))
                continue

            for instrument in instruments:
                try:
                    df = self.broker.get_candles(
                        instrument,
                        granularity=self.config.get("data", {}).get("candle_granularity", "H1"),
                        count=self.config.get("data", {}).get("lookback_periods", 200),
                    )
                    if df.empty:
                        continue

                    tech_signal = strategy.analyze(df, instrument)

                    stream_signal = StreamSignal(
                        stream_id=self.stream_id,
                        instrument=instrument,
                        direction=tech_signal.direction,
                        confidence=tech_signal.confidence,
                        sources=[strat_name],
                        reasoning=f"{strat_name}: {tech_signal.metadata}",
                        metadata=tech_signal.metadata,
                    )
                    signals.append(stream_signal)

                    # Record signal
                    signal_id = self.record_signal(stream_signal, source=strat_name)

                    # Check if tradeable
                    if tech_signal.direction == "neutral":
                        continue
                    if tech_signal.confidence < min_confidence:
                        self.db.execute(
                            "UPDATE signals SET rejection_reason = ? WHERE id = ?",
                            (f"Below confidence threshold ({tech_signal.confidence} < {min_confidence})", signal_id),
                        )
                        self.db.commit()
                        continue

                    # Risk check
                    entry_price = tech_signal.entry_price or df["Close"].iloc[-1]
                    stop_loss = tech_signal.stop_loss or self.risk.calculate_stop_loss(
                        instrument, entry_price, tech_signal.direction, df
                    )
                    take_profit = tech_signal.take_profit or self.risk.calculate_take_profit(
                        entry_price, stop_loss, tech_signal.direction
                    )

                    risk_check = self.risk.check_trade(
                        self.stream_id, instrument, tech_signal.direction,
                        entry_price, stop_loss,
                    )

                    if not risk_check.approved:
                        self.db.execute(
                            "UPDATE signals SET rejection_reason = ? WHERE id = ?",
                            (risk_check.rejection_reason, signal_id),
                        )
                        self.db.commit()
                        logger.info(f"Trade rejected: {instrument} {strat_name} — {risk_check.rejection_reason}")
                        continue

                    # Execute
                    self.executor.execute_trade(
                        stream_id=self.stream_id,
                        instrument=instrument,
                        direction=tech_signal.direction,
                        entry_price=entry_price,
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        position_size=risk_check.position_size,
                        signal_ids=[signal_id],
                    )

                except Exception as e:
                    logger.error(f"Error running {strat_name} on {instrument}: {e}")

        self.record_equity()
        logger.info(f"Strategy stream tick complete. {len(signals)} signals generated.")
        return signals
