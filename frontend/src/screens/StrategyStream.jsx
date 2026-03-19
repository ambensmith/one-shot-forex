import { useState } from 'react'
import { useSignals, useTrades, useDashboard } from '../hooks/useStreamData'
import MetricTile from '../components/MetricTile'
import SignalBadge from '../components/SignalBadge'
import ConfidenceMeter from '../components/ConfidenceMeter'
import { formatPnl, formatPercent, STRATEGY_INFO } from '../lib/constants'

export default function StrategyStream() {
  const { signals, refresh: refreshSignals } = useSignals('strategy')
  const { trades, refresh: refreshTrades } = useTrades('strategy')
  const { data: dashboard, refresh: refreshDashboard } = useDashboard()

  const [running, setRunning] = useState(false)
  const [result, setResult] = useState(null)

  const stream = dashboard?.streams?.find(s => s.id === 'strategy')
  const breakdown = dashboard?.strategy_breakdown || []

  async function handleRunStrategy() {
    setRunning(true)
    setResult(null)
    try {
      const resp = await fetch('/api/run-stream/strategy', { method: 'POST' })
      const data = await resp.json()
      setResult(data)
      refreshSignals()
      refreshTrades()
      refreshDashboard()
    } catch (e) {
      setResult({ status: 'error', error: e.message })
    } finally {
      setRunning(false)
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold">Strategy Stream</h2>
          <p className="text-sm text-gray-500 mt-1">Peer-reviewed mechanical strategies</p>
        </div>
        <button
          onClick={handleRunStrategy}
          disabled={running}
          className="px-4 py-2 bg-green-600 hover:bg-green-500 disabled:bg-gray-700 disabled:text-gray-500 text-sm font-medium rounded-lg transition-colors"
        >
          {running ? 'Running Strategies...' : 'Run Strategy Stream'}
        </button>
      </div>

      {/* Run result banner */}
      {result && (
        <div className={`rounded-lg p-4 mb-6 text-sm border ${
          result.status === 'ok'
            ? 'bg-green-900/20 border-green-800/50 text-green-300'
            : 'bg-red-900/20 border-red-800/50 text-red-300'
        }`}>
          {result.status === 'ok' ? (
            <div>
              <span className="font-semibold">Strategy stream complete:</span>{' '}
              {result.new_signals} signals generated, {result.new_trades} trades executed, {result.open_positions} open positions
              {result.rejections?.length > 0 && (
                <div className="mt-1 text-xs text-gray-400">
                  Rejections: {result.rejections.map(r => `${r.instrument} (${r.reason})`).join(', ')}
                </div>
              )}
            </div>
          ) : (
            <span>Error: {result.error}</span>
          )}
        </div>
      )}

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
