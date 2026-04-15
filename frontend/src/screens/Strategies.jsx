import { useStrategies } from '../hooks/useLLMData'
import DirectionBadge from '../components/DirectionBadge'
import { ConfidenceBar } from '../components/TimelineChapter'
import { INSTRUMENT_META, timeAgo, formatPnlCurrency } from '../lib/constants'

const STRATEGY_DESCRIPTIONS = {
  momentum: {
    description: 'Momentum trading is based on the observation that assets which have been rising tend to continue rising, and those falling tend to continue falling. This is one of the most well-documented anomalies in financial markets, supported by decades of academic research. The strategy exploits the tendency of market participants to underreact to new information, creating persistent price trends.',
    how_it_works: 'The strategy compares returns over two timeframes: a long lookback window (typically 12 months) captures the overall trend, while a short window (1 month) confirms the trend is still active. When both windows agree on direction, a signal is generated. Confidence increases with the strength and consistency of the trend.',
    weaknesses: 'Momentum strategies are vulnerable to sudden reversals ("momentum crashes"), which tend to occur during market stress. They also underperform in range-bound markets where there is no clear trend to follow.',
  },
  carry: {
    description: 'The carry trade exploits interest rate differentials between currencies. Investors borrow in low-interest-rate currencies and invest in high-interest-rate currencies, earning the spread. This is one of the oldest and most widely-used strategies in foreign exchange, driven by the fundamental observation that capital flows toward higher returns.',
    how_it_works: 'The strategy estimates the interest rate differential between two currencies using central bank policy rates and short-term government bond yields. When the differential exceeds a threshold, a carry signal is generated in favour of the higher-yielding currency. Confidence scales with the size of the differential.',
    weaknesses: 'Carry trades are exposed to sudden risk-off events where investors unwind positions simultaneously, causing sharp losses. The strategy also assumes interest rate differentials persist, which breaks down around central bank policy changes.',
  },
  breakout: {
    description: 'Breakout trading identifies moments when price moves beyond established support or resistance levels, suggesting the start of a new trend. This approach is grounded in market microstructure theory: when price breaks through a level where many orders are clustered, the resulting order flow can drive further movement in the same direction.',
    how_it_works: 'The strategy calculates a recent trading range using the highest high and lowest low over a lookback period. When the current price breaks above the range high, a long signal is generated; when it breaks below the range low, a short signal. The strength of the breakout (distance beyond the range) determines confidence.',
    weaknesses: 'Many breakouts are false — price briefly exceeds the range then reverses. Tight, choppy ranges can generate excessive false signals. The strategy also struggles in markets with low volatility where ranges are too narrow to be meaningful.',
  },
  mean_reversion: {
    description: 'Mean reversion is based on the statistical tendency of prices to return toward their long-term average after deviating significantly. When a currency pair moves far from its typical value, the strategy bets on a return to normality. This approach is supported by the economic concept that exchange rates are anchored by fundamental equilibrium values.',
    how_it_works: 'The strategy computes a z-score measuring how many standard deviations the current price is from its moving average. When the z-score exceeds a threshold (price is abnormally extended), a counter-trend signal is generated. Confidence is highest at moderate extensions and decreases at extreme values, where the trend may be structural rather than temporary.',
    weaknesses: 'Mean reversion fails when a structural shift has occurred — for example, a permanent change in monetary policy. "The market can stay irrational longer than you can stay solvent" is the classic warning. The strategy also requires careful calibration of what counts as "normal."',
  },
  volatility_breakout: {
    description: 'Volatility breakout trading identifies periods of unusually low volatility — a "coiled spring" — and positions for the explosive move that often follows. Markets alternate between periods of compression and expansion; this strategy exploits the transition. Academic research by Alizadeh (2002) demonstrated that range-based volatility measures are more efficient estimators than traditional close-to-close methods.',
    how_it_works: 'The strategy monitors the Average True Range (ATR) over a lookback period. When ATR contracts below a threshold, it signals a volatility squeeze. A breakout signal is generated when price moves beyond a multiple of the contracted ATR, anticipating that the period of low volatility will resolve into a directional move.',
    weaknesses: 'Low volatility can persist longer than expected, leading to premature entries. False breakouts during continued compression generate losses. The strategy also struggles to determine breakout direction — it signals that a move is coming, but not which way.',
  },
}

export default function Strategies() {
  const { strategies, loading, error } = useStrategies()

  return (
    <div>
      <h1 className="font-display text-4xl font-bold tracking-tight text-primary" style={{ letterSpacing: '-0.5px', lineHeight: 1.15 }}>
        Strategies
      </h1>
      <p className="text-tertiary mt-1 text-xs">Traditional quantitative trading strategies</p>

      {loading && <p className="text-sm text-tertiary mt-8">Loading strategies...</p>}
      {error && <p className="text-sm text-loss-text mt-8">Error loading strategies: {error}</p>}

      <div className="mt-8 space-y-8">
        {strategies.map(strategy => (
          <StrategyCard key={strategy.name} strategy={strategy} />
        ))}
        {!loading && strategies.length === 0 && (
          <p className="text-sm italic text-tertiary">No strategies configured.</p>
        )}
      </div>
    </div>
  )
}

function StrategyCard({ strategy }) {
  const desc = STRATEGY_DESCRIPTIONS[strategy.name] || {}
  const title = strategy.name.charAt(0).toUpperCase() + strategy.name.slice(1).replace(/_/g, ' ')

  return (
    <div className="bg-surface border border-border rounded-card p-6 shadow-whisper">
      <h2 className="font-display text-[22px] font-semibold text-primary" style={{ letterSpacing: '-0.2px' }}>
        {title}
      </h2>

      {/* Description */}
      <p className="text-base text-secondary leading-[1.65] mt-3 max-w-narrative">
        {desc.description || strategy.description}
      </p>

      {/* How it works */}
      {desc.how_it_works && (
        <div className="mt-5">
          <span className="text-[11px] font-semibold uppercase tracking-[0.8px] text-tertiary">How it works</span>
          <p className="text-sm text-secondary leading-relaxed mt-2 max-w-narrative">{desc.how_it_works}</p>
        </div>
      )}

      {/* Weaknesses */}
      {desc.weaknesses && (
        <div className="mt-4">
          <span className="text-[11px] font-semibold uppercase tracking-[0.8px] text-tertiary">Weaknesses</span>
          <p className="text-sm text-secondary leading-relaxed mt-2 max-w-narrative">{desc.weaknesses}</p>
        </div>
      )}

      {/* Parameters */}
      {strategy.parameters && Object.keys(strategy.parameters).length > 0 && (
        <div className="mt-5">
          <span className="text-[11px] font-semibold uppercase tracking-[0.8px] text-tertiary">Parameters</span>
          <div className="flex flex-wrap gap-x-6 gap-y-2 mt-2">
            {Object.entries(strategy.parameters).map(([key, val]) => (
              <div key={key} className="flex items-baseline gap-1.5">
                <span className="text-xs font-medium text-tertiary">{formatParamName(key)}:</span>
                <span className="text-sm text-primary font-tabular">{formatParamValue(val)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent Signals */}
      {strategy.recent_signals?.length > 0 && (
        <div className="mt-5">
          <span className="text-[11px] font-semibold uppercase tracking-[0.8px] text-tertiary">Recent signals</span>
          <div className="mt-2 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="px-2 py-2 text-left text-xs font-semibold uppercase tracking-[0.5px] text-tertiary">Instrument</th>
                  <th className="px-2 py-2 text-left text-xs font-semibold uppercase tracking-[0.5px] text-tertiary">Direction</th>
                  <th className="px-2 py-2 text-left text-xs font-semibold uppercase tracking-[0.5px] text-tertiary">Confidence</th>
                  <th className="px-2 py-2 text-right text-xs font-semibold uppercase tracking-[0.5px] text-tertiary">Time</th>
                </tr>
              </thead>
              <tbody>
                {strategy.recent_signals.map((sig, i) => {
                  const meta = INSTRUMENT_META[sig.instrument]
                  const semantic = sig.direction === 'long' ? 'profitable' : sig.direction === 'short' ? 'loss' : 'cooldown'
                  return (
                    <tr key={i} className="border-b border-border-subtle">
                      <td className="px-2 py-2.5 font-medium text-primary">
                        {meta?.name || sig.instrument?.replace('_', '/')}
                      </td>
                      <td className="px-2 py-2.5">
                        <DirectionBadge direction={sig.direction} size="small" />
                      </td>
                      <td className="px-2 py-2.5">
                        <ConfidenceBar value={sig.confidence} semantic={semantic} />
                      </td>
                      <td className="px-2 py-2.5 text-right text-xs text-tertiary">
                        {sig.created_at ? timeAgo(sig.created_at) : ''}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Trade Stats */}
      {strategy.trade_stats && (
        <div className="mt-5 pt-4 border-t border-border-subtle">
          <span className="text-[11px] font-semibold uppercase tracking-[0.8px] text-tertiary">Trades from this strategy</span>
          <p className="text-sm text-secondary mt-1">
            <span className="font-tabular">{strategy.trade_stats.total}</span> total
            {' '}&middot;{' '}
            <span className="font-tabular text-profitable-text">{strategy.trade_stats.won} won</span>
            {' '}&middot;{' '}
            <span className="font-tabular text-loss-text">{strategy.trade_stats.lost} lost</span>
            {strategy.trade_stats.net_pnl != null && (
              <>
                {' '}&middot;{' '}
                <span className={`font-tabular ${strategy.trade_stats.net_pnl >= 0 ? 'text-profitable-text' : 'text-loss-text'}`}>
                  {formatPnlCurrency(strategy.trade_stats.net_pnl)}
                </span>
                {' '}net
              </>
            )}
          </p>
        </div>
      )}
    </div>
  )
}

function formatParamName(key) {
  return key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

function formatParamValue(val) {
  if (val == null) return '\u2014'
  if (typeof val === 'object') {
    return Object.entries(val).map(([k, v]) => `${k}: ${v}`).join(', ')
  }
  return String(val)
}
