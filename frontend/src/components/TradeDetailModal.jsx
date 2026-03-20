import { TRADE_STATUS_LABELS } from '../lib/constants'
import { formatPnl, formatPnlCurrency, timeAgo } from '../lib/constants'
import SignalBadge from './SignalBadge'
import HelpTooltip from './HelpTooltip'

/**
 * TradeDetailModal — full detail view for a single trade.
 * Shown when a user clicks a trade row.
 */
export default function TradeDetailModal({ trade, liveData, onClose }) {
  if (!trade) return null

  const statusInfo = TRADE_STATUS_LABELS[trade.status] || { label: trade.status, desc: '', color: 'text-gray-400' }
  const isOpen = trade.status === 'open'
  const live = isOpen && liveData ? liveData : null
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
                {/* Current price marker (live) */}
                {live?.currentPrice && (
                  <div
                    className="absolute top-0 bottom-0 w-1 bg-cyan-400/80"
                    style={{ left: `${Math.max(0, Math.min(100, ((live.currentPrice - minPrice) / range) * 100))}%` }}
                  />
                )}
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
                {live?.currentPrice && (
                  <span className="text-cyan-400">Now: {live.currentPrice.toFixed(5)}</span>
                )}
                <span className="text-green-500">TP: {trade.take_profit?.toFixed(5)}</span>
              </div>
            </div>
          )}

          {/* Key metrics grid */}
          <div className="grid grid-cols-2 gap-3">
            <DetailRow label="Entry Price" value={trade.entry_price?.toFixed(5)} />
            {live ? (
              <DetailRow label="Current Price" value={live.currentPrice?.toFixed(5)} valueClass="text-cyan-400" />
            ) : (
              <DetailRow label="Exit Price" value={trade.exit_price?.toFixed(5) || '—'} />
            )}
            <DetailRow label="Stop Loss" value={trade.stop_loss?.toFixed(5)} />
            <DetailRow label="Take Profit" value={trade.take_profit?.toFixed(5)} />
            {live ? (
              <DetailRow
                label="Unrealized P&L"
                value={formatPnlCurrency(live.unrealizedPL)}
                valueClass={live.unrealizedPL >= 0 ? 'text-green-400' : 'text-red-400'}
              />
            ) : (
              <DetailRow
                label="P&L"
                value={formatPnlCurrency(trade.pnl)}
                valueClass={trade.pnl >= 0 ? 'text-green-400' : 'text-red-400'}
              />
            )}
            {live ? (
              <DetailRow label="SL/TP Distance" value={`SL: ${live.distanceToSL_pips?.toFixed(1)}p / TP: ${live.distanceToTP_pips?.toFixed(1)}p`} />
            ) : (
              <DetailRow
                label="P&L (pips)"
                value={trade.pnl_pips != null ? `${trade.pnl_pips.toFixed(1)} pips` : '—'}
                helpTerm="pips"
              />
            )}
            <DetailRow label="Position Size" value={trade.position_size?.toFixed(0) || '—'} helpTerm="position_size" />
            <DetailRow label="Duration" value={duration} />
            <DetailRow label="Stream" value={trade._isUntracked ? 'broker (untracked)' : trade.stream} />
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

          {/* Trade Timeline */}
          {trade.events && trade.events.length > 0 && (
            <div>
              <div className="text-xs text-gray-500 mb-2 uppercase tracking-wider">Trade Timeline</div>
              <div className="space-y-2">
                {trade.events.map((event, i) => (
                  <TradeEvent key={i} event={event} />
                ))}
              </div>
            </div>
          )}

          {/* Close Context */}
          {trade.close_context && (
            <div>
              <div className="text-xs text-gray-500 mb-2 uppercase tracking-wider">Market Context at Close</div>
              <div className="bg-gray-800/50 rounded-lg p-3 space-y-2 text-sm">
                {trade.close_context.trade_duration_hours != null && (
                  <div className="text-gray-400">
                    Duration: <span className="text-gray-200">{trade.close_context.trade_duration_hours.toFixed(1)}h</span>
                  </div>
                )}
                {trade.close_context.atr_14 != null && (
                  <div className="text-gray-400">
                    ATR(14): <span className="font-mono text-gray-200">{trade.close_context.atr_14.toFixed(5)}</span>
                  </div>
                )}
                {(trade.close_context.max_favorable_pips != null || trade.close_context.max_adverse_pips != null) && (
                  <div className="flex gap-4">
                    <span className="text-green-400">
                      MFE: {trade.close_context.max_favorable_pips?.toFixed(1)} pips
                    </span>
                    <span className="text-red-400">
                      MAE: {trade.close_context.max_adverse_pips?.toFixed(1)} pips
                    </span>
                  </div>
                )}
                {trade.close_context.active_signals_at_close?.length > 0 && (
                  <div>
                    <div className="text-xs text-gray-500 mb-1">Active signals at close:</div>
                    {trade.close_context.active_signals_at_close.map((s, i) => (
                      <div key={i} className="text-xs text-gray-300">
                        {s.stream} / {s.instrument}: {s.direction} ({(s.confidence * 100).toFixed(0)}%)
                      </div>
                    ))}
                  </div>
                )}
                {trade.close_context.recent_headlines?.length > 0 && (
                  <div>
                    <div className="text-xs text-gray-500 mb-1">Recent headlines:</div>
                    {trade.close_context.recent_headlines.map((h, i) => (
                      <div key={i} className="text-xs text-gray-300">{h.headline}</div>
                    ))}
                  </div>
                )}
              </div>
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

function TradeEvent({ event }) {
  const labels = {
    opened: { icon: '>', color: 'text-blue-400', label: 'Opened' },
    snapshot: { icon: '.', color: 'text-gray-500', label: 'Snapshot' },
    closed_sl: { icon: 'x', color: 'text-red-400', label: 'Stopped Out' },
    closed_tp: { icon: '+', color: 'text-green-400', label: 'Target Hit' },
    closed_reconciled: { icon: '~', color: 'text-gray-400', label: 'Reconciled' },
    sl_updated: { icon: '!', color: 'text-yellow-400', label: 'SL Updated' },
    tp_updated: { icon: '!', color: 'text-yellow-400', label: 'TP Updated' },
    size_adjusted: { icon: '#', color: 'text-yellow-400', label: 'Size Adjusted' },
    close_context: { icon: '*', color: 'text-purple-400', label: 'Context Captured' },
    imported: { icon: '+', color: 'text-amber-400', label: 'Imported from Broker' },
  }
  const info = labels[event.event_type] || { icon: '?', color: 'text-gray-400', label: event.event_type }
  const data = event.data || {}

  // Skip snapshot events in timeline (too many), only show them in aggregate
  if (event.event_type === 'snapshot') return null

  return (
    <div className="flex items-start gap-2 text-xs">
      <span className={`font-mono font-bold ${info.color}`}>{info.icon}</span>
      <div className="flex-1">
        <span className={info.color}>{info.label}</span>
        <span className="text-gray-600 ml-2">
          {event.created_at ? new Date(event.created_at).toLocaleString() : ''}
        </span>
        {data.exit_price != null && (
          <span className="text-gray-400 ml-2">@ {data.exit_price.toFixed(5)}</span>
        )}
        {data.pnl != null && (
          <span className={`ml-2 font-mono ${data.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
            {data.pnl >= 0 ? '+' : ''}{data.pnl.toFixed(2)}
          </span>
        )}
        {data.old_value != null && data.new_value != null && (
          <span className="text-gray-400 ml-2">
            {data.old_value} &rarr; {data.new_value}
          </span>
        )}
      </div>
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
