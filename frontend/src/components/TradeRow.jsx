import SignalBadge from './SignalBadge'
import { formatPnl, timeAgo, INSTRUMENT_META, TRADE_STATUS_LABELS } from '../lib/constants'

export default function TradeRow({ trade, onClick }) {
  const meta = INSTRUMENT_META[trade.instrument] || { name: trade.instrument }
  const pnlColor = trade.pnl > 0 ? 'text-green-400' : trade.pnl < 0 ? 'text-red-400' : 'text-gray-400'
  const statusInfo = TRADE_STATUS_LABELS[trade.status] || { label: trade.status, color: 'text-gray-400' }

  return (
    <tr
      className={`border-b border-gray-800/50 hover:bg-gray-800/30 transition-colors ${onClick ? 'cursor-pointer' : ''}`}
      onClick={onClick}
      title={onClick ? 'Click to view trade details' : undefined}
    >
      <td className="py-2 px-3 text-xs text-gray-400">{trade.stream}</td>
      <td className="py-2 px-3 font-mono text-sm">{meta.name}</td>
      <td className="py-2 px-3"><SignalBadge direction={trade.direction} size="sm" /></td>
      <td className="py-2 px-3 font-mono text-xs">{trade.entry_price?.toFixed(5)}</td>
      <td className="py-2 px-3 font-mono text-xs">{trade.exit_price?.toFixed(5) || '—'}</td>
      <td className={`py-2 px-3 font-mono text-sm ${pnlColor}`}>
        {trade.pnl != null ? formatPnl(trade.pnl) : '—'}
      </td>
      <td className="py-2 px-3">
        <span className={`text-xs px-2 py-0.5 rounded ${
          trade.status === 'open' ? 'bg-blue-500/20 text-blue-400' :
          trade.status === 'closed_tp' ? 'bg-green-500/20 text-green-400' :
          trade.status === 'closed_sl' ? 'bg-red-500/20 text-red-400' :
          trade.status === 'failed' ? 'bg-yellow-500/20 text-yellow-400' :
          'bg-gray-500/20 text-gray-400'
        }`}>
          {statusInfo.label}
        </span>
      </td>
      <td className="py-2 px-3 text-xs text-gray-500">{timeAgo(trade.opened_at)}</td>
    </tr>
  )
}
