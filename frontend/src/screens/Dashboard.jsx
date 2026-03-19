import { useState } from 'react'
import { useDashboard, useTrades, useEquity, useReview } from '../hooks/useStreamData'
import { triggerStream, pollWorkflow } from '../lib/api'
import MetricTile from '../components/MetricTile'
import EquityCurve from '../components/EquityCurve'
import TradeRow from '../components/TradeRow'
import { formatPnl, formatPercent } from '../lib/constants'

export default function Dashboard() {
  const { data: dashboard, loading, refresh: refreshDashboard } = useDashboard()
  const { trades, refresh: refreshTrades } = useTrades()
  const { curves, refresh: refreshEquity } = useEquity()
  const { review, refresh: refreshReview } = useReview()

  const [running, setRunning] = useState(false)
  const [resetting, setResetting] = useState(false)
  const [generatingReview, setGeneratingReview] = useState(false)
  const [statusMsg, setStatusMsg] = useState(null)
  const [showReview, setShowReview] = useState(false)

  function refreshAll() {
    refreshDashboard()
    refreshTrades()
    refreshEquity()
    refreshReview()
  }

  async function handleWorkflow(mode, stream, label) {
    const setter = mode === 'reset' ? setResetting : mode === 'review' ? setGeneratingReview : setRunning
    setter(true)
    setStatusMsg({ type: 'info', text: `Dispatching ${label}...` })
    try {
      const { run_id } = await triggerStream({ mode, stream })
      if (run_id) {
        setStatusMsg({ type: 'info', text: `Workflow started (run ${run_id}). Waiting for completion...` })
        const result = await pollWorkflow(run_id, (status) => {
          setStatusMsg({ type: 'info', text: `Workflow ${status}...` })
        })
        if (result.conclusion === 'success' || result.status === 'completed') {
          setStatusMsg({ type: 'ok', text: `${label} complete! Data will update shortly.` })
          // Wait for Vercel to rebuild with new data
          setTimeout(refreshAll, 5000)
        } else {
          setStatusMsg({ type: 'error', text: `Workflow ${result.conclusion || result.status}` })
        }
      } else {
        setStatusMsg({ type: 'ok', text: `${label} dispatched. Refresh page in ~2 min to see results.` })
      }
    } catch (e) {
      setStatusMsg({ type: 'error', text: e.message })
    } finally {
      setter(false)
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
        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              if (!confirm('Reset all data? This clears all signals, trades, and equity.')) return
              handleWorkflow('reset', 'all', 'Reset')
            }}
            disabled={resetting || running || generatingReview}
            className="px-3 py-2 bg-red-600/80 hover:bg-red-500 disabled:bg-gray-700 disabled:text-gray-500 text-xs font-medium rounded-lg transition-colors"
          >
            {resetting ? 'Resetting...' : 'Reset Data'}
          </button>
          <button
            onClick={() => handleWorkflow('review', 'all', 'Review Generation')}
            disabled={generatingReview || running || resetting}
            className="px-3 py-2 bg-purple-600 hover:bg-purple-500 disabled:bg-gray-700 disabled:text-gray-500 text-xs font-medium rounded-lg transition-colors"
          >
            {generatingReview ? 'Generating...' : 'Generate Review'}
          </button>
          <button
            onClick={() => handleWorkflow('tick', 'all', 'All Streams')}
            disabled={running || resetting || generatingReview}
            className="px-3 py-2 bg-green-600 hover:bg-green-500 disabled:bg-gray-700 disabled:text-gray-500 text-xs font-medium rounded-lg transition-colors"
          >
            {running ? 'Running...' : 'Run All Streams'}
          </button>
        </div>
      </div>

      {/* Status banner */}
      {statusMsg && (
        <div className={`rounded-lg p-4 mb-6 text-sm border ${
          statusMsg.type === 'ok' ? 'bg-green-900/20 border-green-800/50 text-green-300'
          : statusMsg.type === 'error' ? 'bg-red-900/20 border-red-800/50 text-red-300'
          : 'bg-blue-900/20 border-blue-800/50 text-blue-300'
        }`}>
          {statusMsg.text}
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

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
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

      {/* Cowork Review Section */}
      <div className="bg-gray-800/50 rounded-lg border border-gray-700/50 p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">Cowork Review</h3>
          {review?.has_review && (
            <button
              onClick={() => setShowReview(!showReview)}
              className="text-xs text-blue-400 hover:text-blue-300"
            >
              {showReview ? 'Hide' : 'Show'} Review
            </button>
          )}
        </div>
        {!review?.has_review ? (
          <p className="text-gray-500 text-sm">No review generated yet. Click "Generate Review" above.</p>
        ) : showReview ? (
          <div className="prose prose-invert prose-sm max-w-none">
            <pre className="whitespace-pre-wrap text-xs text-gray-300 bg-gray-900/50 rounded-lg p-4 overflow-x-auto">
              {review.review_md}
            </pre>
          </div>
        ) : (
          <p className="text-gray-500 text-sm">Review available. Click "Show" to view.</p>
        )}
      </div>
    </div>
  )
}
