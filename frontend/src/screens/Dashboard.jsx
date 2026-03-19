import { useState } from 'react'
import { useDashboard, useTrades, useEquity } from '../hooks/useStreamData'
import MetricTile from '../components/MetricTile'
import EquityCurve from '../components/EquityCurve'
import TradeRow from '../components/TradeRow'
import { formatPnl, formatPercent } from '../lib/constants'

export default function Dashboard() {
  const { data: dashboard, loading, refresh: refreshDashboard } = useDashboard()
  const { trades, refresh: refreshTrades } = useTrades()
  const { curves, refresh: refreshEquity } = useEquity()

  const [running, setRunning] = useState(false)
  const [resetting, setResetting] = useState(false)
  const [result, setResult] = useState(null)

  function refreshAll() {
    refreshDashboard()
    refreshTrades()
    refreshEquity()
  }

  async function handleRunAll() {
    setRunning(true)
    setResult(null)
    try {
      const resp = await fetch('/api/run-all', { method: 'POST' })
      const data = await resp.json()
      setResult(data)
      refreshAll()
    } catch (e) {
      setResult({ status: 'error', error: e.message })
    } finally {
      setRunning(false)
    }
  }

  async function handleReset() {
    if (!confirm('Reset all data? This will clear all signals, trades, and equity history.')) return
    setResetting(true)
    setResult(null)
    try {
      const resp = await fetch('/api/reset', { method: 'POST' })
      const data = await resp.json()
      setResult(data)
      refreshAll()
    } catch (e) {
      setResult({ status: 'error', error: e.message })
    } finally {
      setResetting(false)
    }
  }

  if (loading) return <p className="text-gray-500">Loading dashboard...</p>
  if (!dashboard) return <p className="text-gray-500">No dashboard data available. Run a trading cycle first.</p>

  const streams = dashboard.streams || []
  const instrumentBreakdown = dashboard.instrument_breakdown || []
  const recentTrades = trades.slice(0, 20)

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold">Dashboard</h2>
        <div className="flex items-center gap-3">
          <button
            onClick={handleReset}
            disabled={resetting || running}
            className="px-4 py-2 bg-red-600/80 hover:bg-red-500 disabled:bg-gray-700 disabled:text-gray-500 text-sm font-medium rounded-lg transition-colors"
          >
            {resetting ? 'Resetting...' : 'Reset Data'}
          </button>
          <button
            onClick={handleRunAll}
            disabled={running || resetting}
            className="px-4 py-2 bg-green-600 hover:bg-green-500 disabled:bg-gray-700 disabled:text-gray-500 text-sm font-medium rounded-lg transition-colors"
          >
            {running ? 'Running All Streams...' : 'Run All Streams'}
          </button>
        </div>
      </div>

      {/* Result banner */}
      {result && (
        <div className={`rounded-lg p-4 mb-6 text-sm border ${
          result.status === 'ok'
            ? 'bg-green-900/20 border-green-800/50 text-green-300'
            : 'bg-red-900/20 border-red-800/50 text-red-300'
        }`}>
          {result.status === 'ok' ? (
            result.message ? (
              <span>{result.message}</span>
            ) : (
              <div>
                <span className="font-semibold">All streams complete. </span>
                {result.results?.news && (
                  <span>News: {result.results.news.new_signals}sig/{result.results.news.new_trades}trades. </span>
                )}
                {result.results?.strategy && (
                  <span>Strategy: {result.results.strategy.new_signals}sig/{result.results.strategy.new_trades}trades. </span>
                )}
                {result.results?.hybrid?.length > 0 && (
                  <span>Hybrid: {result.results.hybrid.map(h => `${h.stream}: ${h.new_trades}trades`).join(', ')}. </span>
                )}
              </div>
            )
          ) : (
            <span>Error: {result.error}</span>
          )}
        </div>
      )}

      {/* Equity Curves */}
      <div className="bg-gray-800/50 rounded-lg border border-gray-700/50 p-5 mb-6">
        <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">Equity Curves</h3>
        <EquityCurve curves={curves} height={300} />
      </div>

      {/* Stream Comparison Table */}
      <div className="bg-gray-800/50 rounded-lg border border-gray-700/50 p-5 mb-6 overflow-x-auto">
        <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">Stream Comparison</h3>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-700 text-left text-xs text-gray-500 uppercase">
              <th className="pb-2 pr-4">Stream</th>
              <th className="pb-2 pr-4">Return</th>
              <th className="pb-2 pr-4">Sharpe</th>
              <th className="pb-2 pr-4">Max DD</th>
              <th className="pb-2 pr-4">Win %</th>
              <th className="pb-2 pr-4">Trades</th>
              <th className="pb-2">Open</th>
            </tr>
          </thead>
          <tbody>
            {streams.map(s => (
              <tr key={s.id} className="border-b border-gray-800/50">
                <td className="py-2 pr-4 font-medium">{s.name}</td>
                <td className={`py-2 pr-4 font-mono ${s.total_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {formatPnl(s.total_pnl)}
                </td>
                <td className="py-2 pr-4 font-mono">{s.sharpe_ratio.toFixed(2)}</td>
                <td className="py-2 pr-4 font-mono">{formatPercent(s.max_drawdown)}</td>
                <td className="py-2 pr-4 font-mono">{formatPercent(s.win_rate)}</td>
                <td className="py-2 pr-4 font-mono">{s.trade_count}</td>
                <td className="py-2 font-mono">{s.open_positions}</td>
              </tr>
            ))}
          </tbody>
        </table>

        {/* Strategy breakdown sub-rows */}
        {dashboard.strategy_breakdown?.length > 0 && (
          <>
            <h4 className="text-xs text-gray-500 mt-4 mb-2">Strategy Breakdown</h4>
            <table className="w-full text-sm">
              <tbody>
                {dashboard.strategy_breakdown.map(s => (
                  <tr key={s.name} className="border-b border-gray-800/30">
                    <td className="py-1.5 pr-4 pl-6 text-gray-400 capitalize">{s.name.replace('_', ' ')}</td>
                    <td className={`py-1.5 pr-4 font-mono text-xs ${s.total_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {formatPnl(s.total_pnl)}
                    </td>
                    <td className="py-1.5 pr-4 font-mono text-xs">{formatPercent(s.win_rate)}</td>
                    <td className="py-1.5 pr-4 font-mono text-xs">{s.trade_count} trades</td>
                    <td className="py-1.5 font-mono text-xs">{s.signal_count} signals</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Trades */}
        <div className="bg-gray-800/50 rounded-lg border border-gray-700/50 p-5 overflow-x-auto">
          <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">Recent Trades</h3>
          {recentTrades.length === 0 ? (
            <p className="text-gray-500 text-sm">No trades yet</p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-700 text-left text-xs text-gray-500">
                  <th className="pb-2">Stream</th>
                  <th className="pb-2">Instrument</th>
                  <th className="pb-2">Dir</th>
                  <th className="pb-2">Entry</th>
                  <th className="pb-2">Exit</th>
                  <th className="pb-2">P&L</th>
                  <th className="pb-2">Status</th>
                  <th className="pb-2">When</th>
                </tr>
              </thead>
              <tbody>
                {recentTrades.map(t => <TradeRow key={t.id} trade={t} />)}
              </tbody>
            </table>
          )}
        </div>

        {/* Instrument Breakdown */}
        <div className="bg-gray-800/50 rounded-lg border border-gray-700/50 p-5">
          <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">Instrument P&L</h3>
          {instrumentBreakdown.length === 0 ? (
            <p className="text-gray-500 text-sm">No data yet</p>
          ) : (
            <div className="space-y-2">
              {instrumentBreakdown.map(inst => {
                const maxPnl = Math.max(...instrumentBreakdown.map(i => Math.abs(i.total_pnl)), 1)
                const width = (Math.abs(inst.total_pnl) / maxPnl) * 100
                return (
                  <div key={inst.instrument} className="flex items-center gap-3">
                    <span className="font-mono text-xs w-24">{inst.instrument}</span>
                    <div className="flex-1 bg-gray-700/50 rounded h-4 relative">
                      <div
                        className="h-4 rounded transition-all"
                        style={{
                          width: `${Math.max(width, 2)}%`,
                          backgroundColor: inst.total_pnl >= 0 ? '#37b24d' : '#f03e3e',
                        }}
                      />
                    </div>
                    <span className={`font-mono text-xs w-20 text-right ${
                      inst.total_pnl >= 0 ? 'text-green-400' : 'text-red-400'
                    }`}>
                      {formatPnl(inst.total_pnl)}
                    </span>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
