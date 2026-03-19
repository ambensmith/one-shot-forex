import { useSignals, useTrades, useDashboard } from '../hooks/useStreamData'
import MetricTile from '../components/MetricTile'
import SignalBadge from '../components/SignalBadge'
import ConfidenceMeter from '../components/ConfidenceMeter'
import { formatPnl, formatPercent, STRATEGY_INFO } from '../lib/constants'

export default function StrategyStream() {
  const { signals } = useSignals('strategy')
  const { trades } = useTrades('strategy')
  const { data: dashboard } = useDashboard()

  const stream = dashboard?.streams?.find(s => s.id === 'strategy')
  const breakdown = dashboard?.strategy_breakdown || []

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold">Strategy Stream</h2>
          <p className="text-sm text-gray-500 mt-1">Peer-reviewed mechanical strategies</p>
        </div>
      </div>

      {/* Overall Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
        <MetricTile label="P&L" value={formatPnl(stream?.total_pnl || 0)} positive={stream?.total_pnl > 0} />
        <MetricTile label="Trades" value={stream?.trade_count || 0} />
        <MetricTile label="Win Rate" value={formatPercent(stream?.win_rate || 0)} />
        <MetricTile label="Sharpe" value={(stream?.sharpe_ratio || 0).toFixed(2)} />
        <MetricTile label="Max DD" value={formatPercent(stream?.max_drawdown || 0)} />
      </div>

      {/* Strategy Cards */}
      <div className="space-y-4">
        {Object.entries(STRATEGY_INFO).map(([name, info]) => {
          const stats = breakdown.find(b => b.name === name) || {}
          const stratSignals = signals.filter(s => s.source === name).slice(0, 5)
          const activePositions = trades.filter(t => t.status === 'open')

          return (
            <div key={name} className="bg-gray-800/50 rounded-lg border border-gray-700/50 p-5">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <h3 className="font-semibold text-lg capitalize">
                    {name.replace('_', ' ')}
                  </h3>
                  <p className="text-xs text-gray-500">{info.desc} ({info.paper})</p>
                </div>
                <span className="text-xs bg-green-500/20 text-green-400 px-2 py-0.5 rounded">ON</span>
              </div>

              <div className="grid grid-cols-4 gap-4 mb-3">
                <div>
                  <div className="text-xs text-gray-500">P&L</div>
                  <div className={`font-mono text-sm ${stats.total_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {formatPnl(stats.total_pnl || 0)}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-gray-500">Win Rate</div>
                  <div className="font-mono text-sm">{formatPercent(stats.win_rate || 0)}</div>
                </div>
                <div>
                  <div className="text-xs text-gray-500">Trades</div>
                  <div className="font-mono text-sm">{stats.trade_count || 0}</div>
                </div>
                <div>
                  <div className="text-xs text-gray-500">Signals</div>
                  <div className="font-mono text-sm">{stats.signal_count || 0}</div>
                </div>
              </div>

              {/* Recent signals for this strategy */}
              {stratSignals.length > 0 && (
                <div className="flex gap-2 flex-wrap">
                  {stratSignals.map(s => (
                    <div key={s.id} className="flex items-center gap-1.5 text-xs bg-gray-900/50 px-2 py-1 rounded">
                      <SignalBadge direction={s.direction} size="sm" />
                      <span className="font-mono">{s.instrument}</span>
                      <ConfidenceMeter value={s.confidence} width={40} />
                    </div>
                  ))}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
