import { TRADE_STATUS_LABELS } from '../lib/constants'
import { formatPnl, formatPnlCurrency, timeAgo } from '../lib/constants'
import SignalBadge from './SignalBadge'
import HelpTooltip from './HelpTooltip'

/**
 * TradeDetailModal — full detail view for a single trade.
 * Shown when a user clicks a trade row.
 */
export default function TradeDetailModal({ trade, onClose }) {
  if (!trade) return null

  const statusInfo = TRADE_STATUS_LABELS[trade.status] || { label: trade.status, desc: '', color: 'text-gray-400' }
  const duration = trade.opened_at && trade.closed_at
    ? formatDuration(new Date(trade.opened_at), new Date(trade.closed_at))
    : trade.opened_at ? 'Still open' : '—'

  // SL/TP price bar visualization
  const prices = [trade.stop_loss, trade.entry_price, trade.take_profit].filter(Boolean)
  const minPrice = Math.min(...prices)
  const maxPrice = Math.max(...prices)
  const range = maxPrice - minPrice || 1

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div
        className="bg-gray-900 border border-gray-700 rounded-xl shadow-2xl max-w-lg w-full mx-4 max-h-[90vh] overflow-y-auto"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-gray-800">
          <div className="flex items-center gap-3">
            <span className="font-mono text-lg font-semibold">{trade.instrument}</span>
            <SignalBadge direction={trade.direction} size="sm" />
            <span className={`text-xs px-2 py-0.5 rounded font-medium ${statusInfo.color} bg-gray-800`}>
              {statusInfo.label}
            </span>
          </div>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-300 text-lg">x</button>
        </div>

        <div className="p-5 space-y-5">
          {/* Status explanation */}
          <div className="bg-gray-800/50 rounded-lg p-3 text-sm text-gray-300">
            {statusInfo.desc}
          </div>

          {/* Price levels visualization */}
          {trade.stop_loss && trade.take_profit && (
            <div>
              <div className="text-xs text-gray-500 mb-2 flex items-center">
                Price Levels
                <HelpTooltip term="stop_loss" />
              </div>
              <div className="relative bg-gray-800 rounded-lg h-8 overflow-hidden">
                {/* SL marker */}
                <div
                  className="absolute top-0 bottom-0 w-0.5 bg-red-500"
                  style={{ left: `${((trade.stop_loss - minPrice) / range) * 100}%` }}
                />
                {/* Entry marker */}
                <div
                  className="absolute top-0 bottom-0 w-0.5 bg-blue-400"
                  style={{ left: `${((trade.entry_price - minPrice) / range) * 100}%` }}
                />
                {/* TP marker */}
                <div
                  className="absolute top-0 bottom-0 w-0.5 bg-green-500"
                  style={{ left: `${((trade.take_profit - minPrice) / range) * 100}%` }}
                />
                {/* Exit marker */}
                {trade.exit_price && (
                  <div
                    className="absolute top-0 bottom-0 w-1 bg-yellow-400/60"
                    style={{ left: `${((trade.exit_price - minPrice) / range) * 100}%` }}
                  />
                )}
              </div>
              <div className="flex justify-between text-[10px] text-gray-500 mt-1">
                <span className="text-red-400">SL: {trade.stop_loss?.toFixed(5)}</span>
                <span className="text-blue-400">Entry: {trade.entry_price?.toFixed(5)}</span>
                <span className="text-green-500">TP: {trade.take_profit?.toFixed(5)}</span>
              </div>
            </div>
          )}

          {/* Key metrics grid */}
          <div className="grid grid-cols-2 gap-3">
            <DetailRow label="Entry Price" value={trade.entry_price?.toFixed(5)} />
            <DetailRow label="Exit Price" value={trade.exit_price?.toFixed(5) || '—'} />
            <DetailRow label="Stop Loss" value={trade.stop_loss?.toFixed(5)} />
            <DetailRow label="Take Profit" value={trade.take_profit?.toFixed(5)} />
            <DetailRow
              label="P&L"
              value={formatPnlCurrency(trade.pnl)}
              valueClass={trade.pnl >= 0 ? 'text-green-400' : 'text-red-400'}
            />
            <DetailRow
              label="P&L (pips)"
              value={trade.pnl_pips != null ? `${trade.pnl_pips.toFixed(1)} pips` : '—'}
              helpTerm="pips"
            />
            <DetailRow label="Position Size" value={trade.position_size?.toFixed(0) || '—'} helpTerm="position_size" />
            <DetailRow label="Duration" value={duration} />
            <DetailRow label="Stream" value={trade.stream} />
            <DetailRow label="Opened" value={trade.opened_at ? new Date(trade.opened_at).toLocaleString() : '—'} />
          </div>

          {/* Signal reasoning (if available in metadata) */}
          {trade.reasoning && (
            <div>
              <div className="text-xs text-gray-500 mb-1">Signal Reasoning</div>
              <p className="text-sm text-gray-300 bg-gray-800/50 rounded-lg p-3">{trade.reasoning}</p>
            </div>
          )}

          {trade.source && (
            <div>
              <div className="text-xs text-gray-500 mb-1">Source</div>
              <p className="text-sm text-gray-300">{trade.source}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function DetailRow({ label, value, valueClass = 'text-gray-200', helpTerm }) {
  return (
    <div>
      <div className="text-xs text-gray-500 flex items-center">
        {label}
        {helpTerm && <HelpTooltip term={helpTerm} />}
      </div>
      <div className={`text-sm font-mono ${valueClass}`}>{value}</div>
    </div>
  )
}

function formatDuration(start, end) {
  const ms = end - start
  const mins = Math.floor(ms / 60000)
  if (mins < 60) return `${mins}m`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ${mins % 60}m`
  const days = Math.floor(hours / 24)
  return `${days}d ${hours % 24}h`
}
