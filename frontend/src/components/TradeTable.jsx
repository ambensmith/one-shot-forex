import { useState, Fragment } from 'react'
import { ChevronDown } from 'lucide-react'
import { INSTRUMENT_META, formatPnl, formatPnlCurrency, formatDuration, semanticStatus } from '../lib/constants'
import NarrativeTimeline from './NarrativeTimeline'

export default function TradeTable({ trades, variant = 'open', emptyMessage }) {
  const [expandedId, setExpandedId] = useState(null)

  if (!trades || trades.length === 0) {
    return (
      <p className="text-sm italic text-tertiary py-6">
        {emptyMessage || 'No trades to display.'}
      </p>
    )
  }

  const isOpen = variant === 'open'

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border">
            <Th>Instrument</Th>
            <Th>Direction</Th>
            {isOpen && <Th align="right">Entry</Th>}
            {isOpen && <Th align="right">Current</Th>}
            <Th align="right">P&L (pips)</Th>
            <Th align="right">P&L</Th>
            <Th>Source</Th>
            <Th align="right">Duration</Th>
            {!isOpen && <Th align="right">Closed</Th>}
            <Th align="center" className="w-10" />
          </tr>
        </thead>
        <tbody>
          {trades.map(trade => {
            const isExpanded = expandedId === trade.id
            const semantic = semanticStatus(trade)
            const meta = INSTRUMENT_META[trade.instrument]
            const pnlPips = isOpen ? trade.unrealized_pnl_pips : trade.pnl_pips
            const pnlVal = isOpen ? trade.unrealized_pnl : trade.pnl
            const pnlColor = pnlVal == null ? 'text-tertiary' : pnlVal >= 0 ? 'text-profitable-text' : 'text-loss-text'
            const dirColor = trade.direction === 'long' ? 'text-profitable-text' : trade.direction === 'short' ? 'text-loss-text' : 'text-tertiary'
            const dirArrow = trade.direction === 'long' ? ' \u25b2' : trade.direction === 'short' ? ' \u25bc' : ''

            return (
              <Fragment key={trade.id}>
                <tr
                  className="border-b border-border-subtle hover:bg-hover transition-colors cursor-pointer"
                  onClick={() => setExpandedId(isExpanded ? null : trade.id)}
                  style={isExpanded ? { background: `var(--tint-${semantic})` } : undefined}
                >
                  <Td>
                    <span className="font-medium text-primary">
                      {meta?.name || trade.instrument?.replace('_', '/')}
                    </span>
                  </Td>
                  <Td>
                    <span className={`font-medium ${dirColor}`}>
                      {trade.direction?.toUpperCase()}{dirArrow}
                    </span>
                  </Td>
                  {isOpen && <Td align="right" mono>{trade.entry_price ?? '\u2014'}</Td>}
                  {isOpen && <Td align="right" mono>{trade.current_price ?? '\u2014'}</Td>}
                  <Td align="right" mono className={pnlColor}>
                    {formatPnl(pnlPips)}
                  </Td>
                  <Td align="right" mono className={pnlColor}>
                    {formatPnlCurrency(pnlVal)}
                  </Td>
                  <Td>
                    <SourceBadge source={trade.source} />
                  </Td>
                  <Td align="right" className="text-tertiary">
                    {formatDuration(trade.duration_seconds)}
                  </Td>
                  {!isOpen && (
                    <Td align="right" className="text-tertiary text-xs">
                      {trade.closed_at ? new Date(trade.closed_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' }) : '\u2014'}
                    </Td>
                  )}
                  <Td align="center">
                    <ChevronDown
                      size={16}
                      className={`text-tertiary transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`}
                    />
                  </Td>
                </tr>
                {isExpanded && (
                  <tr>
                    <td colSpan={99}>
                      <div
                        className="border-b border-border"
                        style={{
                          boxShadow: `var(--shadow-${semantic})`,
                        }}
                      >
                        <NarrativeTimeline tradeId={trade.id} trade={trade} />
                      </div>
                    </td>
                  </tr>
                )}
              </Fragment>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}


function Th({ children, align = 'left', className = '' }) {
  return (
    <th
      className={`px-3 py-3 text-left text-xs font-semibold uppercase tracking-[0.5px] text-tertiary ${
        align === 'right' ? 'text-right' : align === 'center' ? 'text-center' : ''
      } ${className}`}
    >
      {children}
    </th>
  )
}

function Td({ children, align = 'left', mono = false, className = '' }) {
  return (
    <td
      className={`px-3 py-4 ${
        align === 'right' ? 'text-right' : align === 'center' ? 'text-center' : ''
      } ${mono ? 'font-tabular' : ''} ${className}`}
    >
      {children}
    </td>
  )
}

function SourceBadge({ source }) {
  if (!source) return <span className="text-tertiary">\u2014</span>
  const isLLM = source === 'llm'
  const label = isLLM ? 'LLM' : source.replace('strategy:', '').replace(/_/g, ' ')
  return (
    <span
      className="text-[11px] font-semibold tracking-[0.3px] px-2 py-0.5 rounded-md capitalize"
      style={{
        background: isLLM ? 'rgba(99, 102, 241, 0.08)' : 'rgba(34, 197, 94, 0.08)',
        color: isLLM ? '#4F46E5' : '#15803D',
      }}
    >
      {label}
    </span>
  )
}
