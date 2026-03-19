import { useState } from 'react'
import { useRunReviews } from '../hooks/useStreamData'
import { timeAgo, formatPnl } from '../lib/constants'

export default function RunHistory() {
  const { runs, loading } = useRunReviews()
  const [expandedId, setExpandedId] = useState(null)

  if (loading) return <p className="text-gray-500">Loading run history...</p>
  if (!runs || runs.length === 0) {
    return <p className="text-gray-500">No runs recorded yet. Trigger a trading cycle to see run history.</p>
  }

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Run History</h2>
      <div className="space-y-3">
        {runs.map(run => (
          <RunCard
            key={run.run_id}
            run={run}
            expanded={expandedId === run.run_id}
            onToggle={() => setExpandedId(expandedId === run.run_id ? null : run.run_id)}
          />
        ))}
      </div>
    </div>
  )
}

function RunCard({ run, expanded, onToggle }) {
  const signalCount = run.signals_generated?.length || 0
  const openedCount = run.trades_opened?.length || 0
  const closedCount = run.trades_closed?.length || 0
  const carriedCount = run.trades_carried?.length || 0
  const isSkipped = run.status === 'skipped'

  return (
    <div className="bg-gray-800/50 rounded-lg border border-gray-700/50 overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full px-5 py-4 flex items-center justify-between text-left hover:bg-gray-800/80 transition-colors"
      >
        <div className="flex items-center gap-4">
          <StatusBadge status={run.status} reason={run.skipped_reason} />
          <div>
            <p className="text-sm font-mono text-gray-200">{run.run_id}</p>
            <p className="text-xs text-gray-500">{timeAgo(run.started_at)}</p>
          </div>
        </div>
        <div className="flex items-center gap-6 text-xs text-gray-400">
          {!isSkipped && (
            <>
              <span>{signalCount} signals</span>
              <span className="text-green-400">+{openedCount} opened</span>
              <span className="text-red-400">{closedCount} closed</span>
              <span>{carriedCount} carried</span>
            </>
          )}
          <span className="text-gray-500">{expanded ? '▲' : '▼'}</span>
        </div>
      </button>
      {expanded && run.review_md && (
        <div className="border-t border-gray-700/50 px-5 py-4">
          <pre className="whitespace-pre-wrap text-xs text-gray-300 bg-gray-900/50 rounded-lg p-4 overflow-x-auto font-mono">
            {run.review_md}
          </pre>
        </div>
      )}
    </div>
  )
}

function StatusBadge({ status, reason }) {
  if (status === 'skipped') {
    return (
      <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-yellow-500/20 text-yellow-300">
        {reason === 'market_closed' ? 'MARKET CLOSED' : reason === 'paused' ? 'PAUSED' : 'SKIPPED'}
      </span>
    )
  }
  if (status === 'completed') {
    return (
      <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-green-500/20 text-green-300">
        COMPLETED
      </span>
    )
  }
  return (
    <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-blue-500/20 text-blue-300">
      {(status || 'unknown').toUpperCase()}
    </span>
  )
}

export { RunCard }
