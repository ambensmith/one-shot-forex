import { useTradeDetail } from '../hooks/useDashboardData'
import { semanticStatus, formatDuration, INSTRUMENT_META } from '../lib/constants'
import TimelineChapter, { ConfidenceBar } from './TimelineChapter'

export default function NarrativeTimeline({ tradeId, trade }) {
  const { record, loading, error } = useTradeDetail(tradeId)

  if (loading) {
    return <p className="text-sm italic text-tertiary py-4">Loading trade details...</p>
  }
  if (error || !record) {
    return <p className="text-sm italic text-tertiary py-4">Could not load trade details.</p>
  }

  const rec = record.record || {}
  const semantic = semanticStatus(trade)
  const isLLM = !trade?.source?.startsWith('strategy:')

  if (isLLM) {
    return <LLMTimeline rec={rec} trade={trade} semantic={semantic} />
  }
  return <StrategyTimeline rec={rec} trade={trade} semantic={semantic} />
}

function LLMTimeline({ rec, trade, semantic }) {
  const headlines = rec.headlines_analysed
  const signal = rec.signal
  const challenge = rec.challenge
  const priceCtx = rec.price_context_at_signal
  const bias = rec.bias_at_trade
  const risk = rec.risk_decision
  const entry = rec.entry
  const exit = rec.exit

  const chapters = [
    {
      title: 'Headlines Analysed',
      status: headlines ? 'completed' : 'pending',
      content: headlines ? (
        <ul className="space-y-2">
          {(Array.isArray(headlines) ? headlines : []).map((h, i) => (
            <li key={i}>
              <span className="font-medium text-primary">&ldquo;{h.headline}&rdquo;</span>
              <span className="text-xs text-tertiary ml-2">({h.source})</span>
              {h.relevance_reasoning && (
                <p className="text-xs text-tertiary mt-0.5">{h.relevance_reasoning}</p>
              )}
            </li>
          ))}
        </ul>
      ) : 'Awaiting headline analysis...',
    },
    {
      title: 'Market Context',
      status: priceCtx ? 'completed' : 'pending',
      content: priceCtx ? (
        <div className="flex flex-wrap gap-4 text-sm">
          <span>Price: <strong className="text-primary font-tabular">{priceCtx.current_price}</strong></span>
          <span>24h: <strong className="text-primary font-tabular">{priceCtx.daily_change_pct != null ? `${priceCtx.daily_change_pct >= 0 ? '+' : ''}${priceCtx.daily_change_pct}%` : '\u2014'}</strong></span>
          <span>Trend: <strong className="text-primary">{priceCtx.trend || '\u2014'}</strong></span>
        </div>
      ) : 'Awaiting market context...',
    },
    {
      title: 'Signal Generation',
      status: signal ? 'completed' : 'pending',
      content: signal ? (
        <div>
          <div className="flex items-center gap-3 mb-2">
            <DirectionBadge direction={signal.direction} />
            <ConfidenceBar value={signal.confidence} semantic={semantic} />
          </div>
          {signal.reasoning && <p className="mb-2">{signal.reasoning}</p>}
          {signal.key_factors && (
            <div className="mt-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-tertiary">Key Factors</span>
              <ul className="mt-1 flex flex-wrap gap-2">
                {(Array.isArray(signal.key_factors) ? signal.key_factors : []).map((f, i) => (
                  <li key={i} className="text-xs bg-hover text-secondary px-2 py-0.5 rounded-md">{f}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      ) : 'Awaiting signal generation...',
    },
    {
      title: 'Counter-Argument Challenge',
      status: challenge ? 'completed' : 'pending',
      content: challenge ? (
        <div className="space-y-2 bg-hover rounded-button p-3">
          <div className="flex items-center gap-3">
            <span className="text-xs font-semibold uppercase tracking-wider text-tertiary">Recommendation</span>
            <RecommendationBadge recommendation={challenge.recommendation} />
          </div>
          <ConfidenceBar value={challenge.conviction_after_challenge} semantic={semantic} />
          {challenge.counter_argument && (
            <div>
              <span className="text-xs font-semibold uppercase tracking-wider text-tertiary">Counter-Argument</span>
              <p className="mt-1">{challenge.counter_argument}</p>
            </div>
          )}
          {challenge.alternative_interpretation && (
            <div>
              <span className="text-xs font-semibold uppercase tracking-wider text-tertiary">Alternative Interpretation</span>
              <p className="mt-1">{challenge.alternative_interpretation}</p>
            </div>
          )}
        </div>
      ) : 'Awaiting challenge...',
    },
    biasChapter(bias),
    riskChapter(risk),
    entryChapter(entry),
    outcomeChapter(exit, trade),
  ]

  return renderTimeline(chapters, semantic)
}

function StrategyTimeline({ rec, trade, semantic }) {
  const signal = rec.signal
  const priceCtx = rec.price_context_at_signal
  const bias = rec.bias_at_trade
  const risk = rec.risk_decision
  const entry = rec.entry
  const exit = rec.exit

  const strategyName = trade?.source?.replace('strategy:', '') || 'Strategy'

  const chapters = [
    {
      title: `Strategy: ${strategyName.charAt(0).toUpperCase() + strategyName.slice(1)}`,
      status: signal ? 'completed' : 'pending',
      content: signal ? (
        <div>
          {signal.parameters && (
            <div className="flex flex-wrap gap-3 mb-2 text-xs">
              {Object.entries(signal.parameters || {}).map(([k, v]) => (
                <span key={k} className="text-tertiary">
                  <span className="font-medium text-secondary">{k}:</span> {String(v)}
                </span>
              ))}
            </div>
          )}
          <div className="flex items-center gap-3 mb-2">
            <DirectionBadge direction={signal.direction} />
            <ConfidenceBar value={signal.confidence} semantic={semantic} />
          </div>
          {signal.reasoning && <p>{signal.reasoning}</p>}
        </div>
      ) : 'Awaiting strategy signal...',
    },
    {
      title: 'Market Context',
      status: priceCtx ? 'completed' : 'pending',
      content: priceCtx ? (
        <div className="flex flex-wrap gap-4 text-sm">
          <span>Price: <strong className="text-primary font-tabular">{priceCtx.current_price}</strong></span>
          <span>24h: <strong className="text-primary font-tabular">{priceCtx.daily_change_pct != null ? `${priceCtx.daily_change_pct >= 0 ? '+' : ''}${priceCtx.daily_change_pct}%` : '\u2014'}</strong></span>
          <span>Trend: <strong className="text-primary">{priceCtx.trend || '\u2014'}</strong></span>
        </div>
      ) : 'Awaiting market context...',
    },
    biasChapter(bias),
    riskChapter(risk),
    entryChapter(entry),
    outcomeChapter(exit, trade),
  ]

  return renderTimeline(chapters, semantic)
}

// Shared chapter builders

function biasChapter(bias) {
  return {
    title: 'Directional Bias',
    status: bias ? 'completed' : 'pending',
    content: bias ? (
      <div className="flex flex-wrap gap-4 text-sm">
        <span>
          {bias.direction?.charAt(0).toUpperCase() + bias.direction?.slice(1)}
          {bias.strength != null && <span className="text-tertiary"> ({bias.strength.toFixed(2)})</span>}
        </span>
        {bias.bias_since && (
          <span className="text-tertiary">since {new Date(bias.bias_since).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })}</span>
        )}
        <span>Aligned: <strong className="text-primary">{bias.aligned ? 'Yes' : 'No'}</strong></span>
        {bias.contributing_signals_count != null && (
          <span className="text-tertiary">{bias.contributing_signals_count} contributing signals</span>
        )}
      </div>
    ) : 'Awaiting bias check...',
  }
}

function riskChapter(risk) {
  return {
    title: 'Risk Decision',
    status: risk ? 'completed' : 'pending',
    content: risk ? (
      <div>
        <div className="flex flex-wrap gap-4 text-sm mb-1">
          <span>{risk.approved ? 'Approved' : 'Rejected'}</span>
          {risk.position_size != null && <span>Size: <strong className="text-primary font-tabular">{risk.position_size} units</strong></span>}
          {risk.risk_amount != null && <span>Risk: <strong className="text-primary font-tabular">&pound;{risk.risk_amount.toFixed(2)}</strong></span>}
        </div>
        {risk.stop_loss != null && risk.take_profit != null && (
          <p className="text-xs text-tertiary font-tabular">
            SL: {risk.stop_loss} &middot; TP: {risk.take_profit}
          </p>
        )}
        {risk.checks_passed && (
          <p className="text-xs text-tertiary mt-1">
            Checks: {risk.checks_passed.join(', ')}
          </p>
        )}
        {risk.rejection_reason && (
          <p className="text-xs text-loss-text mt-1">Rejected: {risk.rejection_reason}</p>
        )}
      </div>
    ) : 'Awaiting risk decision...',
  }
}

function entryChapter(entry) {
  return {
    title: 'Entry',
    status: entry ? 'completed' : 'pending',
    content: entry ? (
      <div className="flex flex-wrap gap-4 text-sm">
        <span>Price: <strong className="text-primary font-tabular">{entry.price}</strong></span>
        {entry.time && (
          <span className="text-tertiary">
            {new Date(entry.time).toLocaleString('en-GB', { hour: '2-digit', minute: '2-digit', day: 'numeric', month: 'short' })}
          </span>
        )}
        {entry.broker_deal_id && (
          <span className="text-xs text-tertiary">Ref: {entry.broker_deal_id}</span>
        )}
      </div>
    ) : 'Awaiting entry...',
  }
}

function outcomeChapter(exit, trade) {
  const isOpen = trade?.status === 'open'
  return {
    title: 'Outcome',
    status: exit ? 'completed' : 'pending',
    content: exit ? (
      <div>
        <div className="flex flex-wrap gap-4 text-sm">
          {exit.pnl != null && (
            <span className={exit.pnl >= 0 ? 'text-profitable-text font-tabular' : 'text-loss-text font-tabular'}>
              {exit.pnl >= 0 ? '+' : ''}&pound;{Math.abs(exit.pnl).toFixed(2)}
              {exit.pnl_pips != null && ` (${exit.pnl_pips >= 0 ? '+' : ''}${exit.pnl_pips} pips)`}
            </span>
          )}
          {exit.close_reason && (
            <span className="text-tertiary">{exit.close_reason.replace(/_/g, ' ')}</span>
          )}
        </div>
        {exit.time && (
          <p className="text-xs text-tertiary mt-1">
            Closed: {new Date(exit.time).toLocaleString('en-GB', { hour: '2-digit', minute: '2-digit', day: 'numeric', month: 'short' })}
          </p>
        )}
      </div>
    ) : isOpen ? 'Trade still open \u2014 managed by SL/TP.' : 'Awaiting outcome...',
  }
}

// Shared render helper

function renderTimeline(chapters, semantic) {
  return (
    <div className="pl-3 py-4">
      {chapters.map((ch, i) => (
        <TimelineChapter
          key={i}
          title={ch.title}
          status={ch.status}
          semantic={semantic}
          isLast={i === chapters.length - 1}
        >
          {ch.content}
        </TimelineChapter>
      ))}
    </div>
  )
}

// Shared small components

function DirectionBadge({ direction }) {
  if (!direction) return null
  const isLong = direction === 'long'
  return (
    <span
      className="text-[11px] font-semibold tracking-[0.3px] px-2 py-0.5 rounded-md"
      style={{
        background: isLong ? 'rgba(34, 197, 94, 0.08)' : direction === 'short' ? 'rgba(239, 68, 68, 0.08)' : 'rgba(148, 163, 184, 0.08)',
        color: isLong ? '#15803D' : direction === 'short' ? '#DC2626' : '#64748B',
      }}
    >
      {direction.toUpperCase()} {isLong ? '\u25b2' : direction === 'short' ? '\u25bc' : ''}
    </span>
  )
}

function RecommendationBadge({ recommendation }) {
  if (!recommendation) return null
  const colors = {
    proceed: { bg: 'rgba(34, 197, 94, 0.08)', text: '#15803D' },
    reduce_size: { bg: 'rgba(245, 158, 11, 0.08)', text: '#B45309' },
    reject: { bg: 'rgba(239, 68, 68, 0.08)', text: '#DC2626' },
  }
  const c = colors[recommendation] || colors.reduce_size
  return (
    <span
      className="text-[11px] font-semibold tracking-[0.3px] px-2 py-0.5 rounded-md"
      style={{ background: c.bg, color: c.text }}
    >
      {recommendation.replace(/_/g, ' ')}
    </span>
  )
}
