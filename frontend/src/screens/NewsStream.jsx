import { useState } from 'react'
import { useSignals, useTrades, useDashboard } from '../hooks/useStreamData'
import StreamCard from '../components/StreamCard'
import MetricTile from '../components/MetricTile'
import SignalBadge from '../components/SignalBadge'
import { formatPnl, formatPercent, timeAgo } from '../lib/constants'

function NewsFeedPanel({ data, loading, error }) {
  if (loading) {
    return (
      <div className="flex items-center gap-3 py-12 justify-center text-gray-400">
        <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
        <span>Fetching live news from BBC, Reuters, GDELT, Calendar...</span>
      </div>
    )
  }
  if (error) {
    return <div className="text-red-400 text-sm bg-red-900/20 rounded-lg p-4 border border-red-800/50">{error}</div>
  }
  if (!data) return null

  const { summary, instruments, unmapped } = data

  return (
    <div className="space-y-4">
      {/* Summary bar */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
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
      </div>

      {/* Source breakdown */}
      <div className="flex gap-2 flex-wrap">
        {Object.entries(summary.source_counts || {}).map(([source, count]) => (
          <span key={source} className="text-xs bg-gray-700/50 px-2 py-1 rounded">
            {source}: {count}
          </span>
        ))}
      </div>

      {/* Instrument cards */}
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
  const { signals, loading: sigLoading } = useSignals('news')
  const { trades } = useTrades('news')
  const { data: dashboard } = useDashboard()

  const [newsData, setNewsData] = useState(null)
  const [newsLoading, setNewsLoading] = useState(false)
  const [newsError, setNewsError] = useState(null)
  const [lastFetched, setLastFetched] = useState(null)

  const stream = dashboard?.streams?.find(s => s.id === 'news')
  const openTrades = trades.filter(t => t.status === 'open')
  const latestSignals = signals.filter(s => !s.is_comparison).slice(0, 10)

  async function handleFetchNews() {
    setNewsLoading(true)
    setNewsError(null)
    try {
      const resp = await fetch('/api/news-fetch')
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
      const data = await resp.json()
      setNewsData(data)
      setLastFetched(new Date().toLocaleTimeString())
    } catch (e) {
      setNewsError(`Failed to fetch news: ${e.message}`)
    } finally {
      setNewsLoading(false)
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
            disabled={newsLoading}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:text-gray-500 text-sm font-medium rounded-lg transition-colors"
          >
            {newsLoading ? 'Fetching...' : 'Fetch News'}
          </button>
        </div>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
        <MetricTile label="P&L" value={formatPnl(stream?.total_pnl || 0)} positive={stream?.total_pnl > 0} />
        <MetricTile label="Trades" value={stream?.trade_count || 0} />
        <MetricTile label="Win Rate" value={formatPercent(stream?.win_rate || 0)} />
        <MetricTile label="Sharpe" value={(stream?.sharpe_ratio || 0).toFixed(2)} />
        <MetricTile label="Max DD" value={formatPercent(stream?.max_drawdown || 0)} />
      </div>

      {/* Live News Feed */}
      {(newsData || newsLoading || newsError) && (
        <div className="mb-6">
          <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">Live News Feed</h3>
          <NewsFeedPanel data={newsData} loading={newsLoading} error={newsError} />
        </div>
      )}

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
