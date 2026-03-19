import { useState } from 'react'
import { useDashboard, useTrades, useEquity, useReview, useRunReviews, useConfig } from '../hooks/useStreamData'
import { triggerStream, pollWorkflow } from '../lib/api'
import MetricTile from '../components/MetricTile'
import EquityCurve from '../components/EquityCurve'
import TradeRow from '../components/TradeRow'
import HelpTooltip from '../components/HelpTooltip'
import HowItWorks from '../components/HowItWorks'
import RiskGauge from '../components/RiskGauge'
import TradeDetailModal from '../components/TradeDetailModal'
import { formatPnl, formatPnlCurrency, formatPercent, timeAgo, TRADE_STATUS_LABELS } from '../lib/constants'
import { RunCard } from './RunHistory'

const STREAM_FILTERS = ['all', 'news', 'strategy', 'hybrid']
const DIR_FILTERS = ['all', 'long', 'short']
const STATUS_FILTERS = ['all', 'open', 'won', 'lost']
const SORT_OPTIONS = ['date', 'pnl', 'instrument']

export default function Dashboard() {
  const { data: dashboard, loading, refresh: refreshDashboard } = useDashboard()
  const { trades, refresh: refreshTrades } = useTrades()
  const { curves, refresh: refreshEquity } = useEquity()
  const { review, refresh: refreshReview } = useReview()
  const { runs: recentRuns, refresh: refreshRuns } = useRunReviews()
  const { config } = useConfig()

  const [running, setRunning] = useState(false)
  const [resetting, setResetting] = useState(false)
  const [generatingReview, setGeneratingReview] = useState(false)
  const [statusMsg, setStatusMsg] = useState(null)
  const [showReview, setShowReview] = useState(false)
  const [expandedRunId, setExpandedRunId] = useState(null)

  // Trade filters
  const [streamFilter, setStreamFilter] = useState('all')
  const [dirFilter, setDirFilter] = useState('all')
  const [statusFilter, setStatusFilter] = useState('all')
  const [sortBy, setSortBy] = useState('date')
  const [showAllTrades, setShowAllTrades] = useState(false)
  const [selectedTrade, setSelectedTrade] = useState(null)

  function refreshAll() {
    refreshDashboard()
    refreshTrades()
    refreshEquity()
    refreshReview()
    refreshRuns()
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
  if (!dashboard) return <p className="text-gray-500">No dashboard data available. Run a trading cycle first, or visit the <a href="/guide" className="text-blue-400 hover:text-blue-300 underline">Guide</a> to get started.</p>

  const streams = dashboard.streams || []
  const instrumentBreakdown = dashboard.instrument_breakdown || []

  // Filter and sort trades
  let filteredTrades = [...trades]
  if (streamFilter !== 'all') {
    filteredTrades = filteredTrades.filter(t =>
      streamFilter === 'hybrid' ? t.stream?.startsWith('hybrid:') : t.stream === streamFilter
    )
  }
  if (dirFilter !== 'all') {
    filteredTrades = filteredTrades.filter(t => t.direction === dirFilter)
  }
  if (statusFilter === 'open') filteredTrades = filteredTrades.filter(t => t.status === 'open')
  else if (statusFilter === 'won') filteredTrades = filteredTrades.filter(t => t.status === 'closed_tp')
  else if (statusFilter === 'lost') filteredTrades = filteredTrades.filter(t => t.status === 'closed_sl')

  if (sortBy === 'pnl') filteredTrades.sort((a, b) => (b.pnl || 0) - (a.pnl || 0))
  else if (sortBy === 'instrument') filteredTrades.sort((a, b) => (a.instrument || '').localeCompare(b.instrument || ''))
  // else date (default, already sorted)

  const totalTrades = trades.length
  const displayTrades = showAllTrades ? filteredTrades : filteredTrades.slice(0, 20)

  // Risk config
  const maxDailyLoss = config?.risk?.max_daily_loss_per_stream || 0.03
  const maxPositions = config?.risk?.max_open_positions_per_stream || 5

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

      <HowItWorks>
        <p>This page shows aggregate performance across all your trading streams. Equity curves track the value of each stream over time.</p>
        <p>The stream comparison table shows which approach is performing best. Click any trade row to see the full details of why it was taken.</p>
        <p><strong>Run All Streams</strong> triggers a full trading cycle — news analysis, all 5 strategies, and any hybrids. <strong>Generate Review</strong> creates a detailed performance report.</p>
      </HowItWorks>

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

      {/* Risk Summary */}
      {streams.length > 0 && (
        <div className="bg-gray-800/50 rounded-lg border border-gray-700/50 p-5 mb-6">
          <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4 flex items-center">
            Risk Overview
            <HelpTooltip term="capital_at_risk" />
          </h3>
          <div className="space-y-3">
            {streams.map(s => {
              const allocation = s.capital_allocation || 33333
              const returnPct = allocation > 0 ? ((s.equity || allocation) - allocation) / allocation : 0
              return (
                <div key={s.id} className="flex items-center gap-4">
                  <span className="text-sm font-medium w-28 shrink-0">{s.name}</span>
                  <div className="flex-1 grid grid-cols-4 gap-3 text-xs">
                    <div>
                      <span className="text-gray-500">Equity: </span>
                      <span className={`font-mono ${returnPct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {formatPnlCurrency(s.equity || allocation)} ({returnPct >= 0 ? '+' : ''}{(returnPct * 100).toFixed(1)}%)
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-500">Positions: </span>
                      <span className="font-mono">{s.open_positions || 0} / {maxPositions}</span>
                    </div>
                    <div className="col-span-2">
                      <RiskGauge
                        label="Daily Loss"
                        used={Math.abs(Math.min(s.daily_pnl || 0, 0))}
                        limit={allocation * maxDailyLoss}
                      />
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Capital Allocation Overview */}
      {streams.length > 0 && (
        <div className="bg-gray-800/50 rounded-lg border border-gray-700/50 p-5 mb-6">
          <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4 flex items-center">
            Capital Allocation
            <HelpTooltip term="capital_allocation" />
          </h3>
          <div className="flex gap-2">
            {streams.map(s => {
              const allocation = s.capital_allocation || 33333
              const total = streams.reduce((sum, st) => sum + (st.capital_allocation || 33333), 0)
              const pct = total > 0 ? (allocation / total * 100) : 0
              const streamColor = s.id === 'news' ? '#4c6ef5' : s.id === 'strategy' ? '#37b24d' : '#f59f00'
              return (
                <div key={s.id} className="text-center" style={{ flex: pct }}>
                  <div className="h-3 rounded-full mb-2" style={{ backgroundColor: streamColor }} />
                  <div className="text-xs font-medium">{s.name}</div>
                  <div className="text-xs text-gray-500 font-mono">{formatPnlCurrency(allocation)}</div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Equity Curves */}
      <div className="bg-gray-800/50 rounded-lg border border-gray-700/50 p-5 mb-6">
        <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4 flex items-center">
          Equity Curves
          <HelpTooltip term="equity" />
        </h3>
        <EquityCurve curves={curves} height={300} />
      </div>

      {/* Stream Comparison Table */}
      <div className="bg-gray-800/50 rounded-lg border border-gray-700/50 p-5 mb-6 overflow-x-auto">
        <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">Stream Comparison</h3>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-700 text-left text-xs text-gray-500 uppercase">
              <th className="pb-2 pr-4">Stream</th>
              <th className="pb-2 pr-4">
                <span className="flex items-center">Return <HelpTooltip term="pnl" /></span>
              </th>
              <th className="pb-2 pr-4">
                <span className="flex items-center">Return % <HelpTooltip term="return_pct" /></span>
              </th>
              <th className="pb-2 pr-4">
                <span className="flex items-center">Sharpe <HelpTooltip term="sharpe_ratio" /></span>
              </th>
              <th className="pb-2 pr-4">
                <span className="flex items-center">Max DD <HelpTooltip term="max_drawdown" /></span>
              </th>
              <th className="pb-2 pr-4">
                <span className="flex items-center">Win % <HelpTooltip term="win_rate" /></span>
              </th>
              <th className="pb-2 pr-4">Trades</th>
              <th className="pb-2">Open</th>
            </tr>
          </thead>
          <tbody>
            {streams.map(s => {
              const allocation = s.capital_allocation || 33333
              const returnPct = allocation > 0 ? ((s.equity || allocation) - allocation) / allocation : 0
              return (
                <tr key={s.id} className="border-b border-gray-800/50">
                  <td className="py-2 pr-4 font-medium">{s.name}</td>
                  <td className={`py-2 pr-4 font-mono ${s.total_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {formatPnl(s.total_pnl)}
                  </td>
                  <td className={`py-2 pr-4 font-mono ${returnPct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {returnPct >= 0 ? '+' : ''}{(returnPct * 100).toFixed(1)}%
                  </td>
                  <td className="py-2 pr-4 font-mono">{s.sharpe_ratio.toFixed(2)}</td>
                  <td className="py-2 pr-4 font-mono">{formatPercent(s.max_drawdown)}</td>
                  <td className="py-2 pr-4 font-mono">{formatPercent(s.win_rate)}</td>
                  <td className="py-2 pr-4 font-mono">{s.trade_count}</td>
                  <td className="py-2 font-mono">{s.open_positions}</td>
                </tr>
              )
            })}
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

          {/* Filters */}
          <div className="flex flex-wrap gap-2 mb-3">
            <FilterPills label="Stream" options={STREAM_FILTERS} value={streamFilter} onChange={setStreamFilter} />
            <FilterPills label="Direction" options={DIR_FILTERS} value={dirFilter} onChange={setDirFilter} />
            <FilterPills label="Status" options={STATUS_FILTERS} value={statusFilter} onChange={setStatusFilter} />
            <select
              value={sortBy}
              onChange={e => setSortBy(e.target.value)}
              className="text-xs bg-gray-700 border border-gray-600 rounded px-2 py-1 text-gray-300"
            >
              {SORT_OPTIONS.map(s => (
                <option key={s} value={s}>Sort: {s}</option>
              ))}
            </select>
          </div>

          <div className="text-xs text-gray-500 mb-2">
            Showing {displayTrades.length} of {filteredTrades.length} trades
            {filteredTrades.length < totalTrades && ` (${totalTrades} total)`}
          </div>

          {displayTrades.length === 0 ? (
            <p className="text-gray-500 text-sm">No trades match your filters. {totalTrades === 0 && <><a href="/guide" className="text-blue-400 hover:text-blue-300 underline">Run a trading cycle</a> to generate trades.</>}</p>
          ) : (
            <>
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
                  {displayTrades.map(t => <TradeRow key={t.id} trade={t} onClick={() => setSelectedTrade(t)} />)}
                </tbody>
              </table>
              {!showAllTrades && filteredTrades.length > 20 && (
                <button
                  onClick={() => setShowAllTrades(true)}
                  className="mt-3 text-xs text-blue-400 hover:text-blue-300"
                >
                  Show all {filteredTrades.length} trades
                </button>
              )}
            </>
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

      {/* Recent Runs */}
      {recentRuns && recentRuns.length > 0 && (
        <div className="bg-gray-800/50 rounded-lg border border-gray-700/50 p-5 mb-6">
          <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">Recent Runs</h3>
          <div className="space-y-2">
            {recentRuns.slice(0, 3).map(run => (
              <RunCard
                key={run.run_id}
                run={run}
                expanded={expandedRunId === run.run_id}
                onToggle={() => setExpandedRunId(expandedRunId === run.run_id ? null : run.run_id)}
              />
            ))}
          </div>
        </div>
      )}

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
          <p className="text-gray-500 text-sm">No review generated yet. Click "Generate Review" above to create a detailed performance analysis.</p>
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

      {/* Trade Detail Modal */}
      {selectedTrade && (
        <TradeDetailModal trade={selectedTrade} onClose={() => setSelectedTrade(null)} />
      )}
    </div>
  )
}

function FilterPills({ label, options, value, onChange }) {
  return (
    <div className="flex items-center gap-1">
      <span className="text-[10px] text-gray-500 uppercase mr-1">{label}:</span>
      {options.map(opt => (
        <button
          key={opt}
          onClick={() => onChange(opt)}
          className={`text-xs px-2 py-0.5 rounded transition-colors capitalize ${
            value === opt
              ? 'bg-brand-500/20 text-brand-300 border border-brand-500/40'
              : 'bg-gray-700/50 text-gray-500 border border-gray-600/50 hover:text-gray-300'
          }`}
        >
          {opt}
        </button>
      ))}
    </div>
  )
}
