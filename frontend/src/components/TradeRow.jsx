import SignalBadge from './SignalBadge'
import { formatPnl, timeAgo, INSTRUMENT_META, TRADE_STATUS_LABELS } from '../lib/constants'

function formatDuration(dateStr) {
  if (!dateStr) return ''
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 60) return `${mins}m`
  const hours = Math.floor(mins / 60)
  const remMins = mins % 60
  if (hours < 24) return `${hours}h ${remMins}m`
  const days = Math.floor(hours / 24)
  const remHours = hours % 24
  return `${days}d ${remHours}h`
}

export default function TradeRow({ trade, onClick, liveData }) {
  const meta = INSTRUMENT_META[trade.instrument] || { name: trade.instrument }
  const isOpen = trade.status === 'open'
  const statusInfo = TRADE_STATUS_LABELS[trade.status] || { label: trade.status, color: 'text-gray-400' }

  // Use live data for open trades if available
  const live = isOpen && liveData ? liveData : null
  const displayPnl = live ? live.unrealizedPL : trade.pnl
  const pnlColor = displayPnl > 0 ? 'text-green-400' : displayPnl < 0 ? 'text-red-400' : 'text-gray-400'

  return (
    <tr
      className={`border-b border-gray-800/50 hover:bg-gray-800/30 transition-colors ${onClick ? 'cursor-pointer' : ''}`}
      onClick={onClick}
      title={onClick ? 'Click to view trade details' : undefined}
    >
      <td className="py-2 px-3 text-xs">
        {trade._isUntracked ? (
          <span className="text-amber-400">broker</span>
        ) : (
          <span className="text-gray-400">{trade.stream}</span>
        )}
      </td>
      <td className="py-2 px-3 font-mono text-sm">{meta.name}</td>
      <td className="py-2 px-3"><SignalBadge direction={trade.direction} size="sm" /></td>
      <td className="py-2 px-3 font-mono text-xs">{trade.entry_price?.toFixed(5)}</td>
      <td className="py-2 px-3 font-mono text-xs">
        {isOpen && live ? (
          <span className="text-cyan-400" title="Live price">
            {live.currentPrice?.toFixed(5)}
          </span>
        ) : (
          trade.exit_price?.toFixed(5) || '—'
        )}
      </td>
      <td className={`py-2 px-3 font-mono text-sm ${pnlColor}`}>
        {displayPnl != null ? formatPnl(displayPnl) : '—'}
      </td>
      <td className="py-2 px-3">
        {trade._isUntracked ? (
          <div className="flex items-center gap-1.5">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-500"></span>
            </span>
            <span className="text-xs px-2 py-0.5 rounded bg-amber-500/20 text-amber-400">
              Untracked
            </span>
          </div>
        ) : isOpen && live ? (
          <div className="flex items-center gap-1.5">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-cyan-500"></span>
            </span>
            <span className="text-xs px-2 py-0.5 rounded bg-blue-500/20 text-blue-400">
              Live
            </span>
          </div>
        ) : (
          <span className={`text-xs px-2 py-0.5 rounded ${
            trade.status === 'open' ? 'bg-blue-500/20 text-blue-400' :
            trade.status === 'closed_tp' ? 'bg-green-500/20 text-green-400' :
            trade.status === 'closed_sl' ? 'bg-red-500/20 text-red-400' :
            trade.status === 'failed' ? 'bg-yellow-500/20 text-yellow-400' :
            'bg-gray-500/20 text-gray-400'
          }`}>
            {statusInfo.label}
          </span>
        )}
      </td>
      <td className="py-2 px-3 text-xs text-gray-500">
        {isOpen ? formatDuration(trade.opened_at) : timeAgo(trade.closed_at || trade.opened_at)}
      </td>
      {/* SL/TP distance for open trades */}
      {isOpen && live ? (
        <td className="py-2 px-3">
          <div className="flex gap-2 text-xs font-mono">
            <span className="text-red-400" title="Distance to SL">
              SL {live.distanceToSL_pips?.toFixed(1)}p
            </span>
            <span className="text-green-400" title="Distance to TP">
              TP {live.distanceToTP_pips?.toFixed(1)}p
            </span>
          </div>
        </td>
      ) : (
        <td className="py-2 px-3"></td>
      )}
    </tr>
  )
}
