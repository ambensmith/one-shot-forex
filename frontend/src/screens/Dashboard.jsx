import { useDashboard, useTrades, useEquity } from '../hooks/useStreamData'
import MetricTile from '../components/MetricTile'
import EquityCurve from '../components/EquityCurve'
import TradeRow from '../components/TradeRow'
import { formatPnl, formatPercent } from '../lib/constants'

export default function Dashboard() {
  const { data: dashboard, loading } = useDashboard()
  const { trades } = useTrades()
  const { curves } = useEquity()

  if (loading) return <p className="text-gray-500">Loading dashboard...</p>
  if (!dashboard) return <p className="text-gray-500">No dashboard data available. Run a trading cycle first.</p>

  const streams = dashboard.streams || []
  const instrumentBreakdown = dashboard.instrument_breakdown || []
  const recentTrades = trades.slice(0, 20)

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Dashboard</h2>

      {/* Equity Curves */}
      <div className="bg-gray-800/50 rounded-lg border border-gray-700/50 p-5 mb-6">
        <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">Equity Curves</h3>
        <EquityCurve curves={curves} height={300} />
      </div>

      {/* Stream Comparison Table */}
      <div className="bg-gray-800/50 rounded-lg border border-gray-700/50 p-5 mb-6 overflow-x-auto">
        <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">Stream Comparison</h3>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-700 text-left text-xs text-gray-500 uppercase">
              <th className="pb-2 pr-4">Stream</th>
              <th className="pb-2 pr-4">Return</th>
              <th className="pb-2 pr-4">Sharpe</th>
              <th className="pb-2 pr-4">Max DD</th>
              <th className="pb-2 pr-4">Win %</th>
              <th className="pb-2 pr-4">Trades</th>
              <th className="pb-2">Open</th>
            </tr>
          </thead>
          <tbody>
            {streams.map(s => (
              <tr key={s.id} className="border-b border-gray-800/50">
                <td className="py-2 pr-4 font-medium">{s.name}</td>
                <td className={`py-2 pr-4 font-mono ${s.total_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {formatPnl(s.total_pnl)}
                </td>
                <td className="py-2 pr-4 font-mono">{s.sharpe_ratio.toFixed(2)}</td>
                <td className="py-2 pr-4 font-mono">{formatPercent(s.max_drawdown)}</td>
                <td className="py-2 pr-4 font-mono">{formatPercent(s.win_rate)}</td>
                <td className="py-2 pr-4 font-mono">{s.trade_count}</td>
                <td className="py-2 font-mono">{s.open_positions}</td>
              </tr>
            ))}
          </tbody>
        </table>

        {/* Strategy breakdown sub-rows */}
        {dashboard.strategy_breakdown?.length > 0 && (
          <>
            <h4 className="text-xs text-gray-500 mt-4 mb-2">Strategy Breakdown</h4>
            <table className="w-full text-sm">
              <tbody>
                {dashboard.strategy_breakdown.map(s => (
                  <tr key={s.name} className="border-b border-gray-800/30">
                    <td className="py-1.5 pr-4 pl-6 text-gray-400 capitalize">{s.name.replace('_', ' ')}</td>
                    <td className={`py-1.5 pr-4 font-mono text-xs ${s.total_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {formatPnl(s.total_pnl)}
                    </td>
                    <td className="py-1.5 pr-4 font-mono text-xs">{formatPercent(s.win_rate)}</td>
                    <td className="py-1.5 pr-4 font-mono text-xs">{s.trade_count} trades</td>
                    <td className="py-1.5 font-mono text-xs">{s.signal_count} signals</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Trades */}
        <div className="bg-gray-800/50 rounded-lg border border-gray-700/50 p-5 overflow-x-auto">
          <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">Recent Trades</h3>
          {recentTrades.length === 0 ? (
            <p className="text-gray-500 text-sm">No trades yet</p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-700 text-left text-xs text-gray-500">
                  <th className="pb-2">Stream</th>
                  <th className="pb-2">Instrument</th>
                  <th className="pb-2">Dir</th>
                  <th className="pb-2">Entry</th>
                  <th className="pb-2">Exit</th>
                  <th className="pb-2">P&L</th>
                  <th className="pb-2">Status</th>
                  <th className="pb-2">When</th>
                </tr>
              </thead>
              <tbody>
                {recentTrades.map(t => <TradeRow key={t.id} trade={t} />)}
              </tbody>
            </table>
          )}
        </div>

        {/* Instrument Breakdown */}
        <div className="bg-gray-800/50 rounded-lg border border-gray-700/50 p-5">
          <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">Instrument P&L</h3>
          {instrumentBreakdown.length === 0 ? (
            <p className="text-gray-500 text-sm">No data yet</p>
          ) : (
            <div className="space-y-2">
              {instrumentBreakdown.map(inst => {
                const maxPnl = Math.max(...instrumentBreakdown.map(i => Math.abs(i.total_pnl)), 1)
                const width = (Math.abs(inst.total_pnl) / maxPnl) * 100
                return (
                  <div key={inst.instrument} className="flex items-center gap-3">
                    <span className="font-mono text-xs w-24">{inst.instrument}</span>
                    <div className="flex-1 bg-gray-700/50 rounded h-4 relative">
                      <div
                        className="h-4 rounded transition-all"
                        style={{
                          width: `${Math.max(width, 2)}%`,
                          backgroundColor: inst.total_pnl >= 0 ? '#37b24d' : '#f03e3e',
                        }}
                      />
                    </div>
                    <span className={`font-mono text-xs w-20 text-right ${
                      inst.total_pnl >= 0 ? 'text-green-400' : 'text-red-400'
                    }`}>
                      {formatPnl(inst.total_pnl)}
                    </span>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
