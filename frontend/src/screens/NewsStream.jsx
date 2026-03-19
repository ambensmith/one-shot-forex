import { useState } from 'react'
import { useSignals, useTrades, useDashboard } from '../hooks/useStreamData'
import { saveModelComparison, triggerStream, pollWorkflow } from '../lib/api'
import StreamCard from '../components/StreamCard'
import MetricTile from '../components/MetricTile'
import SignalBadge from '../components/SignalBadge'
import { formatPnl, formatPercent, timeAgo } from '../lib/constants'

const DIRECTION_STYLES = {
  long: 'bg-green-500/20 text-green-400 border-green-500/30',
  short: 'bg-red-500/20 text-red-400 border-red-500/30',
  neutral: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
}

function SignalCard({ signal }) {
  const dirStyle = DIRECTION_STYLES[signal.direction] || DIRECTION_STYLES.neutral
  const confPct = ((signal.confidence || 0) * 100).toFixed(0)
  const confColor = signal.confidence >= 0.7 ? '#37b24d' : signal.confidence >= 0.5 ? '#f59f00' : '#868e96'

  return (
    <div className={`rounded-lg p-4 border ${dirStyle}`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className={`text-xs font-bold uppercase px-2 py-0.5 rounded ${dirStyle}`}>
            {signal.direction}
          </span>
          <span className="font-mono font-semibold">{signal.display_name}</span>
          <span className="text-xs text-gray-500">{signal.instrument}</span>
        </div>
        <span className="text-xs text-gray-500">{signal.headline_count} headlines</span>
      </div>

      {/* Confidence bar */}
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xs text-gray-400">Confidence:</span>
        <div className="flex-1 bg-gray-700 rounded-full h-2">
          <div
            className="h-2 rounded-full transition-all"
            style={{ width: `${confPct}%`, backgroundColor: confColor }}
          />
        </div>
        <span className="text-xs font-mono">{confPct}%</span>
      </div>

      {/* Reasoning */}
      {signal.reasoning && (
        <p className="text-sm text-gray-300 mb-2">{signal.reasoning}</p>
      )}

      {/* Key factors */}
      {signal.key_factors?.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-2">
          {signal.key_factors.map((f, i) => (
            <span key={i} className="text-xs bg-gray-700/50 px-2 py-0.5 rounded">{f}</span>
          ))}
        </div>
      )}

      {/* Meta */}
      <div className="flex items-center gap-3 text-xs text-gray-500">
        <span>Model: {signal.model}</span>
        <span>Horizon: {signal.time_horizon}</span>
      </div>
    </div>
  )
}

function NewsFeedPanel({ data, loading, error, loadingPhase }) {
  if (loading) {
    return (
      <div className="flex items-center gap-3 py-12 justify-center text-gray-400">
        <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
        <span>{loadingPhase || 'Fetching live news and generating signals...'}</span>
      </div>
    )
  }
  if (error) {
    return <div className="text-red-400 text-sm bg-red-900/20 rounded-lg p-4 border border-red-800/50">{error}</div>
  }
  if (!data) return null

  const { summary, instruments, signals, unmapped } = data

  return (
    <div className="space-y-6">
      {/* Summary bar */}
      <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
        <div className="bg-gray-800/50 rounded-lg p-3 border border-gray-700/50 text-center">
          <div className="text-lg font-bold">{summary.total_fetched}</div>
          <div className="text-xs text-gray-500">Fetched</div>
        </div>
        <div className="bg-gray-800/50 rounded-lg p-3 border border-gray-700/50 text-center">
          <div className="text-lg font-bold">{summary.after_dedup}</div>
          <div className="text-xs text-gray-500">After Dedup</div>
        </div>
        <div className="bg-gray-800/50 rounded-lg p-3 border border-gray-700/50 text-center">
          <div className="text-lg font-bold text-green-400">{summary.mapped_count}</div>
          <div className="text-xs text-gray-500">Mapped</div>
        </div>
        <div className="bg-gray-800/50 rounded-lg p-3 border border-gray-700/50 text-center">
          <div className="text-lg font-bold text-gray-500">{summary.unmapped_count}</div>
          <div className="text-xs text-gray-500">Discarded</div>
        </div>
        <div className="bg-gray-800/50 rounded-lg p-3 border border-gray-700/50 text-center">
          <div className="text-lg font-bold text-blue-400">{summary.instruments_active}</div>
          <div className="text-xs text-gray-500">Instruments</div>
        </div>
        <div className="bg-gray-800/50 rounded-lg p-3 border border-gray-700/50 text-center">
          <div className="text-lg font-bold text-purple-400">{summary.signals_generated || 0}</div>
          <div className="text-xs text-gray-500">Signals</div>
        </div>
      </div>

      {/* Source breakdown */}
      <div className="flex gap-2 flex-wrap">
        {Object.entries(summary.source_counts || {}).map(([source, count]) => (
          <span key={source} className="text-xs bg-gray-700/50 px-2 py-1 rounded">
            {source}: {count}
          </span>
        ))}
      </div>

      {/* LLM Signals */}
      {signals && signals.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">LLM Trading Signals</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {signals
              .sort((a, b) => b.confidence - a.confidence)
              .map((sig) => (
                <SignalCard key={sig.instrument} signal={sig} />
              ))}
          </div>
        </div>
      )}

      {/* Instrument headline cards */}
      <details open>
        <summary className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3 cursor-pointer">
          News by Instrument
        </summary>
        <div className="space-y-3 mt-3">
          {instruments.map((inst) => (
            <div key={inst.symbol} className="bg-gray-800/50 rounded-lg p-4 border border-gray-700/50">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <span className={`text-xs px-2 py-0.5 rounded font-medium ${
                    inst.type === 'commodity' ? 'bg-yellow-500/20 text-yellow-400' : 'bg-blue-500/20 text-blue-400'
                  }`}>
                    {inst.type.toUpperCase()}
                  </span>
                  <span className="font-mono font-semibold">{inst.display_name}</span>
                  <span className="text-xs text-gray-500">{inst.symbol}</span>
                </div>
                <span className="text-xs text-gray-500">{inst.headline_count} headlines</span>
              </div>
              <div className="space-y-1.5">
                {inst.headlines.slice(0, 5).map((h, i) => (
                  <div key={i} className="flex items-start gap-2 text-sm">
                    <span className="text-xs text-gray-600 shrink-0 w-16 text-right">
                      {h.published_at ? new Date(h.published_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''}
                    </span>
                    <span className="text-xs text-gray-500 shrink-0 w-24 truncate">{h.source}</span>
                    {h.source_count > 1 && (
                      <span className="text-xs bg-amber-500/20 text-amber-400 px-1.5 py-0.5 rounded font-medium shrink-0">
                        {h.source_count} sources
                      </span>
                    )}
                    <span className="text-gray-300 text-xs leading-relaxed">
                      {h.url ? <a href={h.url} target="_blank" rel="noopener noreferrer" className="hover:text-blue-400 transition-colors">{h.headline}</a> : h.headline}
                    </span>
                  </div>
                ))}
                {inst.headline_count > 5 && (
                  <div className="text-xs text-gray-600 pl-[10.5rem]">...and {inst.headline_count - 5} more</div>
                )}
              </div>
            </div>
          ))}
        </div>
      </details>

      {/* Unmapped */}
      {unmapped.length > 0 && (
        <details className="bg-gray-800/30 rounded-lg p-4 border border-gray-700/30">
          <summary className="text-sm text-gray-500 cursor-pointer">
            {unmapped.length} unmapped headlines (no instrument match)
          </summary>
          <div className="mt-2 space-y-1">
            {unmapped.slice(0, 10).map((h, i) => (
              <div key={i} className="text-xs text-gray-600 flex gap-2">
                <span className="shrink-0 w-24 truncate">{h.source}</span>
                <span>{h.headline}</span>
              </div>
            ))}
          </div>
        </details>
      )}
    </div>
  )
}

export default function NewsStream() {
  const { signals, loading: sigLoading, refresh: refreshSignals } = useSignals('news')
  const { trades, refresh: refreshTrades } = useTrades('news')
  const { data: dashboard, refresh: refreshDashboard } = useDashboard()

  const [newsData, setNewsData] = useState(null)
  const [newsLoading, setNewsLoading] = useState(false)
  const [newsError, setNewsError] = useState(null)
  const [lastFetched, setLastFetched] = useState(null)
  const [loadingPhase, setLoadingPhase] = useState('')
  const [tradingRunning, setTradingRunning] = useState(false)
  const [tradingResult, setTradingResult] = useState(null)

  const stream = dashboard?.streams?.find(s => s.id === 'news')
  const openTrades = trades.filter(t => t.status === 'open')
  const latestSignals = signals.filter(s => !s.is_comparison).slice(0, 10)

  async function handleRunTradingCycle() {
    setTradingRunning(true)
    setTradingResult(null)
    try {
      const { run_id } = await triggerStream({ mode: 'tick', stream: 'news' })
      if (run_id) {
        setTradingResult({ status: 'info', text: `Workflow started (run ${run_id}). Analyzing news...` })
        const result = await pollWorkflow(run_id, (status) => {
          setTradingResult({ status: 'info', text: `Workflow ${status}...` })
        })
        if (result.conclusion === 'success' || result.status === 'completed') {
          setTradingResult({ status: 'ok', text: 'News trading cycle complete! Data updating shortly.' })
          setTimeout(() => { refreshSignals(); refreshTrades(); refreshDashboard() }, 5000)
        } else {
          setTradingResult({ status: 'error', error: `Workflow ${result.conclusion || result.status}` })
        }
      } else {
        setTradingResult({ status: 'ok', text: 'Workflow dispatched. Refresh in ~2 min.' })
      }
    } catch (e) {
      setTradingResult({ status: 'error', error: e.message })
    } finally {
      setTradingRunning(false)
    }
  }

  async function handleFetchNews() {
    setNewsLoading(true)
    setNewsError(null)
    setLoadingPhase('Fetching news from BBC, Reuters, GDELT, Calendar...')

    // Brief delay then update phase message
    const phaseTimer = setTimeout(() => {
      setLoadingPhase('News fetched. Generating signals across all models...')
    }, 5000)

    try {
      const resp = await fetch('/api/news-fetch')
      clearTimeout(phaseTimer)
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
      const data = await resp.json()
      setNewsData(data)
      setLastFetched(new Date().toLocaleTimeString())
      // Cache model comparison data for the ModelComparison page
      if (data.model_comparison) {
        saveModelComparison(data.model_comparison)
      }
    } catch (e) {
      clearTimeout(phaseTimer)
      setNewsError(`Failed to fetch news: ${e.message}`)
    } finally {
      setNewsLoading(false)
      setLoadingPhase('')
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold">News Stream</h2>
          <p className="text-sm text-gray-500 mt-1">LLM-driven trading from live news</p>
        </div>
        <div className="flex items-center gap-3">
          {lastFetched && (
            <span className="text-xs text-gray-500">Last fetch: {lastFetched}</span>
          )}
          <button
            onClick={handleFetchNews}
            disabled={newsLoading || tradingRunning}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:text-gray-500 text-sm font-medium rounded-lg transition-colors"
          >
            {newsLoading ? 'Fetching & Analyzing...' : 'Fetch News & Generate Signals'}
          </button>
          <button
            onClick={handleRunTradingCycle}
            disabled={tradingRunning || newsLoading}
            className="px-4 py-2 bg-green-600 hover:bg-green-500 disabled:bg-gray-700 disabled:text-gray-500 text-sm font-medium rounded-lg transition-colors"
          >
            {tradingRunning ? 'Running Trading Cycle...' : 'Run News Trading Cycle'}
          </button>
        </div>
      </div>

      {/* Trading cycle result banner */}
      {tradingResult && (
        <div className={`rounded-lg p-4 mb-6 text-sm border ${
          tradingResult.status === 'ok' ? 'bg-green-900/20 border-green-800/50 text-green-300'
          : tradingResult.status === 'error' ? 'bg-red-900/20 border-red-800/50 text-red-300'
          : 'bg-blue-900/20 border-blue-800/50 text-blue-300'
        }`}>
          {tradingResult.text || tradingResult.error || 'Processing...'}
        </div>
      )}

      {/* Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
        <MetricTile label="P&L" value={formatPnl(stream?.total_pnl || 0)} positive={stream?.total_pnl > 0} />
        <MetricTile label="Trades" value={stream?.trade_count || 0} />
        <MetricTile label="Win Rate" value={formatPercent(stream?.win_rate || 0)} />
        <MetricTile label="Sharpe" value={(stream?.sharpe_ratio || 0).toFixed(2)} />
        <MetricTile label="Max DD" value={formatPercent(stream?.max_drawdown || 0)} />
      </div>

      {/* Live News Feed + Signals */}
      {(newsData || newsLoading || newsError) && (
        <div className="mb-6">
          <NewsFeedPanel data={newsData} loading={newsLoading} error={newsError} loadingPhase={loadingPhase} />
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Historical Signals */}
        <div className="lg:col-span-2 space-y-3">
          <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">Historical Signals</h3>
          {sigLoading ? (
            <p className="text-gray-500 text-sm">Loading...</p>
          ) : latestSignals.length === 0 ? (
            <p className="text-gray-500 text-sm">No historical signals yet.</p>
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
