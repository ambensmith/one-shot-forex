import { useState } from 'react'
import { useDashboard, useTrades, useEquity, useReview, useRunReviews, useConfig } from '../hooks/useStreamData'
import { triggerStream, pollWorkflow } from '../lib/api'
import useLivePositions from '../hooks/useLivePositions'
import EquityCurve from '../components/EquityCurve'
import TradeRow from '../components/TradeRow'
import HelpTooltip from '../components/HelpTooltip'
import RiskGauge from '../components/RiskGauge'
import TradeDetailModal from '../components/TradeDetailModal'
import { formatPnl, formatPnlCurrency, formatPercent, timeAgo, TRADE_STATUS_LABELS } from '../lib/constants'

const STREAM_FILTERS = ['all', 'news', 'strategy', 'hybrid']
const DIR_FILTERS = ['all', 'long', 'short']
const STATUS_FILTERS = ['all', 'open', 'won', 'lost']
const SORT_OPTIONS = ['date', 'pnl', 'instrument']

export default function Dashboard() {
  const { data: dashboard, loading, refresh: refreshDashboard } = useDashboard()
  const { trades, refresh: refreshTrades } = useTrades()
  const { curves, refresh: refreshEquity } = useEquity()
  const { config } = useConfig()

  const { positions: livePositions, account: liveAccount, timestamp: liveTimestamp, loading: liveLoading, error: liveError, enabled: liveEnabled, setEnabled: setLiveEnabled, refresh: refreshLive } = useLivePositions({ interval: 30000 })

  const [running, setRunning] = useState(false)
  const [resetting, setResetting] = useState(false)
  const [statusMsg, setStatusMsg] = useState(null)

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
  }

  async function handleWorkflow(mode, stream, label) {
    const setter = mode === 'reset' ? setResetting : setRunning
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

  // Aggregate totals across all streams
  const totalPnl = streams.reduce((sum, s) => sum + (s.total_pnl || 0), 0)
  const totalAllocation = streams.reduce((sum, s) => sum + (s.capital_allocation || 100), 0)
  const totalEquity = streams.reduce((sum, s) => sum + (s.equity || s.capital_allocation || 100), 0)
  const totalReturnPct = totalAllocation > 0 ? (totalEquity - totalAllocation) / totalAllocation : 0
  const todayPnl = streams.reduce((sum, s) => sum + (s.daily_pnl || 0), 0)
  const totalOpenPositions = streams.reduce((sum, s) => sum + (s.open_positions || 0), 0)

  // Aggregate risk: total daily loss used vs total daily loss limit
  const maxDailyLoss = config?.risk?.max_daily_loss_per_stream || 0.03
  const maxPositions = config?.risk?.max_open_positions_per_stream || 5
  const totalDailyLossUsed = streams.reduce((sum, s) => sum + Math.abs(Math.min(s.daily_pnl || 0, 0)), 0)
  const totalDailyLossLimit = streams.reduce((sum, s) => (s.capital_allocation || 100) * maxDailyLoss + sum, 0)
  const totalMaxPositions = streams.length * maxPositions

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
  // else date (default, already sorted latest first)

  // Merge untracked broker positions into the trade list
  const shouldShowUntracked = streamFilter === 'all' || streamFilter === 'broker'
  const statusShowsOpen = statusFilter === 'all' || statusFilter === 'open'
  if (shouldShowUntracked && statusShowsOpen && dirFilter === 'all') {
    filteredTrades = [...filteredTrades, ...untrackedPositions]
  } else if (shouldShowUntracked && statusShowsOpen) {
    filteredTrades = [...filteredTrades, ...untrackedPositions.filter(t => t.direction === dirFilter)]
  }

  const totalTrades = trades.length
  const displayTrades = showAllTrades ? filteredTrades : filteredTrades.slice(0, 30)

  // Build live data lookups — prefer dealId matching, fallback to instrument+direction
  const liveByDealId = {}
  const liveByKey = {}
  for (const lp of livePositions) {
    if (lp.dealId) liveByDealId[lp.dealId] = lp
    const key = `${lp.instrument}_${lp.direction}`
    liveByKey[key] = lp
  }
  function getLiveForTrade(trade) {
    if (trade.status !== 'open') return null
    if (trade.broker_deal_id && liveByDealId[trade.broker_deal_id]) {
      return liveByDealId[trade.broker_deal_id]
    }
    return liveByKey[`${trade.instrument}_${trade.direction}`] || null
  }

  // Find live positions not matched to any DB trade (truly untracked)
  const matchedDealIds = new Set()
  for (const t of trades) {
    if (t.status === 'open' && t.broker_deal_id) matchedDealIds.add(t.broker_deal_id)
  }
  const untrackedPositions = livePositions
    .filter(lp => lp.dealId && !matchedDealIds.has(lp.dealId))
    .map(lp => ({
      id: `live-${lp.dealId}`,
      stream: 'broker',
      instrument: lp.instrument,
      direction: lp.direction,
      entry_price: lp.entryPrice,
      exit_price: null,
      stop_loss: lp.stopLevel,
      take_profit: lp.profitLevel,
      position_size: lp.size,
      pnl: lp.unrealizedPL,
      pnl_pips: null,
      status: 'open',
      opened_at: null,
      closed_at: null,
      _isUntracked: true,
      _liveData: lp,
    }))

  const pnlColor = totalPnl >= 0 ? 'text-green-400' : 'text-red-400'
  const todayColor = todayPnl >= 0 ? 'text-green-400' : todayPnl < 0 ? 'text-red-400' : 'text-gray-400'

  return (
    <div>
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

      {/* ── Live Status Bar ── */}
      <div className="flex items-center justify-between bg-gray-800/30 rounded-lg border border-gray-700/30 px-4 py-2 mb-4 text-xs">
        <div className="flex items-center gap-3">
          <button
            onClick={() => setLiveEnabled(!liveEnabled)}
            className={`flex items-center gap-1.5 px-2 py-1 rounded transition-colors ${
              liveEnabled
                ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
                : 'bg-gray-700/50 text-gray-500 border border-gray-600/50'
            }`}
          >
            {liveEnabled && (
              <span className="relative flex h-1.5 w-1.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-cyan-500"></span>
              </span>
            )}
            {liveEnabled ? 'Live' : 'Live Off'}
          </button>
          {liveTimestamp && (
            <span className="text-gray-500">
              Updated {timeAgo(liveTimestamp)}
            </span>
          )}
          {liveLoading && <span className="text-gray-500">Refreshing...</span>}
        </div>
        <div className="flex items-center gap-4">
          {liveAccount && (
            <>
              <span className="text-gray-400">
                Balance: <span className="font-mono text-gray-300">{liveAccount.currency === 'EUR' ? '\u20AC' : '$'}{liveAccount.balance?.toFixed(2)}</span>
              </span>
              <span className={liveAccount.unrealizedPL >= 0 ? 'text-green-400' : 'text-red-400'}>
                Unrealized: <span className="font-mono">{formatPnl(liveAccount.unrealizedPL)}</span>
              </span>
            </>
          )}
          {liveError && livePositions.length === 0 ? (
            <span className="text-amber-400" title={liveError}>Live: connection error</span>
          ) : (
            <span className="text-gray-500">{livePositions.length} live positions</span>
          )}
        </div>
      </div>

      {/* ── Section 1: The Headline ── */}
      <div className="bg-gray-800/50 rounded-lg border border-gray-700/50 p-6 mb-6">
        <div className="flex items-start justify-between mb-4">
          <div>
            <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">Total Return</div>
            <div className={`text-4xl font-bold font-mono ${pnlColor}`}>
              {formatPnlCurrency(totalPnl)}
            </div>
            <div className={`text-sm font-mono mt-1 ${pnlColor}`}>
              {totalReturnPct >= 0 ? '+' : ''}{(totalReturnPct * 100).toFixed(2)}% of {formatPnlCurrency(totalAllocation).replace('+', '')}
            </div>
            <div className={`text-xs font-mono mt-2 ${todayColor}`}>
              Today: {formatPnlCurrency(todayPnl)}
            </div>
          </div>

          {/* Action buttons */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                if (!confirm('Reset all data? This clears all signals, trades, and equity.')) return
                handleWorkflow('reset', 'all', 'Reset')
              }}
              disabled={resetting || running}
              className="px-3 py-2 bg-red-600/80 hover:bg-red-500 disabled:bg-gray-700 disabled:text-gray-500 text-xs font-medium rounded-lg transition-colors"
            >
              {resetting ? 'Resetting...' : 'Reset'}
            </button>
            <button
              onClick={() => handleWorkflow('tick', 'all', 'All Streams')}
              disabled={running || resetting}
              className="px-3 py-2 bg-green-600 hover:bg-green-500 disabled:bg-gray-700 disabled:text-gray-500 text-xs font-medium rounded-lg transition-colors"
            >
              {running ? 'Running...' : 'Run All Streams'}
            </button>
          </div>
        </div>

        {/* Compact equity curve */}
        <EquityCurve curves={curves} height={200} />
      </div>

      {/* ── Section 2: Stream Performance ── */}
      {streams.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          {streams.map(s => {
            const allocation = s.capital_allocation || 100
            const equity = s.equity || allocation
            const returnPct = allocation > 0 ? (equity - allocation) / allocation : 0
            const pnl = s.total_pnl || 0
            const color = pnl >= 0 ? 'text-green-400' : 'text-red-400'
            return (
              <div key={s.id} className="bg-gray-800/50 rounded-lg border border-gray-700/50 p-4">
                <div className="text-xs text-gray-500 uppercase tracking-wider mb-2">{s.name}</div>
                <div className={`text-2xl font-bold font-mono ${color}`}>
                  {formatPnlCurrency(pnl)}
                </div>
                <div className={`text-xs font-mono mt-1 ${color}`}>
                  {returnPct >= 0 ? '+' : ''}{(returnPct * 100).toFixed(1)}%
                </div>
                <div className="flex gap-4 mt-3 text-xs text-gray-400">
                  <span>{formatPercent(s.win_rate)} wins</span>
                  <span>{s.trade_count} trades</span>
                  <span>{s.open_positions || 0} open</span>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* ── Section 3: Safety at a Glance ── */}
      <div className="bg-gray-800/50 rounded-lg border border-gray-700/50 p-5 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-center">
          <div>
            <RiskGauge
              label="Daily loss budget"
              used={totalDailyLossUsed}
              limit={totalDailyLossLimit}
              helpTerm="daily_loss_limit"
            />
          </div>
          <div className="flex items-center gap-2 text-sm">
            <span className="text-gray-500">Open positions:</span>
            <span className="font-mono font-medium">
              {totalOpenPositions}
            </span>
            <span className="text-gray-600">/ {totalMaxPositions}</span>
            <HelpTooltip term="max_positions" />
          </div>
        </div>
      </div>

      {/* ── Section 3: All Trades ── */}
      <div className="bg-gray-800/50 rounded-lg border border-gray-700/50 p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">Trades</h3>
          <div className="text-xs text-gray-500">
            {filteredTrades.length === totalTrades
              ? `${totalTrades} trades`
              : `${filteredTrades.length} of ${totalTrades} trades`
            }
          </div>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-2 mb-4">
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

        {totalTrades === 0 ? (
          <p className="text-gray-500 text-sm py-8 text-center">
            No trades yet. Click <strong>Run All Streams</strong> above to start a trading cycle,
            or visit the <a href="/guide" className="text-blue-400 hover:text-blue-300 underline">Guide</a> to learn how.
          </p>
        ) : filteredTrades.length === 0 ? (
          <p className="text-gray-500 text-sm py-4 text-center">No trades match your filters.</p>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-700 text-left text-xs text-gray-500">
                    <th className="pb-2 px-3">Stream</th>
                    <th className="pb-2 px-3">Instrument</th>
                    <th className="pb-2 px-3">Dir</th>
                    <th className="pb-2 px-3">Entry</th>
                    <th className="pb-2 px-3">Current/Exit</th>
                    <th className="pb-2 px-3">P&L</th>
                    <th className="pb-2 px-3">Status</th>
                    <th className="pb-2 px-3">Age/When</th>
                    <th className="pb-2 px-3">SL/TP</th>
                  </tr>
                </thead>
                <tbody>
                  {displayTrades.map(t => <TradeRow key={t.id} trade={t} onClick={() => setSelectedTrade(t)} liveData={getLiveForTrade(t) || t._liveData} />)}
                </tbody>
              </table>
            </div>
            {!showAllTrades && filteredTrades.length > 30 && (
              <button
                onClick={() => setShowAllTrades(true)}
                className="mt-3 text-xs text-blue-400 hover:text-blue-300 w-full text-center py-2"
              >
                Show all {filteredTrades.length} trades
              </button>
            )}
          </>
        )}
      </div>

      {/* Trade Detail Modal */}
      {selectedTrade && (
        <TradeDetailModal trade={selectedTrade} liveData={getLiveForTrade(selectedTrade) || selectedTrade._liveData} onClose={() => setSelectedTrade(null)} />
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
