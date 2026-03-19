import { useSignals, useTrades, useDashboard } from '../hooks/useStreamData'
import StreamCard from '../components/StreamCard'
import MetricTile from '../components/MetricTile'
import SignalBadge from '../components/SignalBadge'
import { formatPnl, formatPercent, timeAgo } from '../lib/constants'

export default function NewsStream() {
  const { signals, loading: sigLoading } = useSignals('news')
  const { trades } = useTrades('news')
  const { data: dashboard } = useDashboard()

  const stream = dashboard?.streams?.find(s => s.id === 'news')
  const openTrades = trades.filter(t => t.status === 'open')
  const latestSignals = signals.filter(s => !s.is_comparison).slice(0, 10)

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold">News Stream</h2>
          <p className="text-sm text-gray-500 mt-1">LLM-driven trading from live news</p>
        </div>
        {signals[0] && (
          <span className="text-xs text-gray-500">Last cycle: {timeAgo(signals[0].created_at)}</span>
        )}
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
        <MetricTile label="P&L" value={formatPnl(stream?.total_pnl || 0)} positive={stream?.total_pnl > 0} />
        <MetricTile label="Trades" value={stream?.trade_count || 0} />
        <MetricTile label="Win Rate" value={formatPercent(stream?.win_rate || 0)} />
        <MetricTile label="Sharpe" value={(stream?.sharpe_ratio || 0).toFixed(2)} />
        <MetricTile label="Max DD" value={formatPercent(stream?.max_drawdown || 0)} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Signals */}
        <div className="lg:col-span-2 space-y-3">
          <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">Latest Signals</h3>
          {sigLoading ? (
            <p className="text-gray-500 text-sm">Loading...</p>
          ) : latestSignals.length === 0 ? (
            <p className="text-gray-500 text-sm">No signals yet. Run a trading cycle to generate signals.</p>
          ) : (
            latestSignals.map(sig => (
              <StreamCard key={sig.id} signal={sig} />
            ))
          )}
        </div>

        {/* Active Positions */}
        <div className="space-y-3">
          <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">Active Positions</h3>
          {openTrades.length === 0 ? (
            <p className="text-gray-500 text-sm">No open positions</p>
          ) : (
            openTrades.map(t => (
              <div key={t.id} className="bg-gray-800/50 rounded-lg p-3 border border-gray-700/50">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-sm">{t.instrument}</span>
                  <SignalBadge direction={t.direction} size="sm" />
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  Entry: {t.entry_price?.toFixed(5)}
                </div>
                <div className="text-xs text-gray-500">
                  SL: {t.stop_loss?.toFixed(5)} | TP: {t.take_profit?.toFixed(5)}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
