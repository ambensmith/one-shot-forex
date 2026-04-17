import { useState } from 'react'
import BiasCardRow from '../components/BiasCardRow'
import TradeTable from '../components/TradeTable'
import TradeFilters from '../components/TradeFilters'
import EquityCurve from '../components/EquityCurve'
import PerformanceChart from '../components/PerformanceChart'
import { useOpenTrades, useClosedTrades } from '../hooks/useDashboardData'
import { timeAgo } from '../lib/constants'

export default function Dashboard() {
  const { trades: openTrades, loading: openLoading, refresh } = useOpenTrades(30000)
  const [closedFilters, setClosedFilters] = useState({ filter: null, instrument: null, source: null })
  const { trades: closedTrades, loading: closedLoading, loadMore, hasMore } = useClosedTrades(closedFilters)

  // Last updated timestamp — use the most recent data fetch
  const lastUpdated = openTrades.length > 0
    ? timeAgo(new Date().toISOString())
    : null

  return (
    <div className="space-y-10">
      {/* Page title */}
      <div>
        <h1 className="font-display text-4xl font-bold tracking-tight text-primary" style={{ letterSpacing: '-0.5px', lineHeight: 1.15 }}>
          Dashboard
        </h1>
        {lastUpdated && (
          <p className="text-xs text-tertiary mt-1">Last updated {lastUpdated}</p>
        )}
      </div>

      {/* Bias cards */}
      <section>
        <BiasCardRow />
      </section>

      {/* Open trades */}
      <section>
        <h2 className="font-display text-[28px] font-semibold tracking-tight text-primary mb-4" style={{ letterSpacing: '-0.3px', lineHeight: 1.2 }}>
          Open Trades
        </h2>
        <div className="bg-surface border border-border rounded-card shadow-whisper overflow-hidden">
          <TradeTable
            trades={openTrades}
            variant="open"
            emptyMessage="No open trades. The system is monitoring for signals."
          />
        </div>
      </section>

      {/* Closed trades */}
      <section>
        <h2 className="font-display text-[28px] font-semibold tracking-tight text-primary mb-4" style={{ letterSpacing: '-0.3px', lineHeight: 1.2 }}>
          Closed Trades
        </h2>
        <div className="mb-4">
          <TradeFilters filters={closedFilters} onChange={setClosedFilters} />
        </div>
        <div className="bg-surface border border-border rounded-card shadow-whisper overflow-hidden">
          <TradeTable
            trades={closedTrades}
            variant="closed"
            emptyMessage="No closed trades match your filters."
          />
        </div>
        {hasMore && (
          <div className="text-center mt-4">
            <button
              onClick={loadMore}
              disabled={closedLoading}
              className="px-5 py-2.5 text-sm font-medium text-secondary bg-surface border border-border rounded-button hover:bg-hover hover:border-border-strong transition-all"
            >
              {closedLoading ? 'Loading...' : 'Load more'}
            </button>
          </div>
        )}
      </section>

      {/* Equity curve — total account value (broker balance) */}
      <section>
        <h2 className="font-display text-[28px] font-semibold tracking-tight text-primary mb-4" style={{ letterSpacing: '-0.3px', lineHeight: 1.2 }}>
          Total account value
        </h2>
        <EquityCurve />
      </section>

      {/* Strategy performance — per-strategy cumulative PnL vs LLM */}
      <section>
        <h2 className="font-display text-[28px] font-semibold tracking-tight text-primary mb-4" style={{ letterSpacing: '-0.3px', lineHeight: 1.2 }}>
          Strategy performance
        </h2>
        <PerformanceChart />
      </section>
    </div>
  )
}
