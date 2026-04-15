import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { useEquity } from '../hooks/useDashboardData'

export default function EquityCurve() {
  const { data, loading } = useEquity()

  if (loading) {
    return <EquityWrapper><p className="text-sm italic text-tertiary">Loading equity data...</p></EquityWrapper>
  }

  if (!data || data.length === 0) {
    return (
      <EquityWrapper>
        <p className="text-sm italic text-tertiary">
          Equity data will appear after the first trade closes.
        </p>
      </EquityWrapper>
    )
  }

  // Format data for Recharts
  const chartData = data.map(d => ({
    timestamp: d.timestamp,
    equity: d.equity,
    label: new Date(d.timestamp).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' }),
  }))

  return (
    <EquityWrapper>
      <ResponsiveContainer width="100%" height={240}>
        <AreaChart data={chartData} margin={{ top: 8, right: 8, bottom: 0, left: 8 }}>
          <defs>
            <linearGradient id="equityFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="rgba(79, 70, 229, 0.06)" />
              <stop offset="100%" stopColor="rgba(79, 70, 229, 0.01)" />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="#F5F5F4" strokeDasharray="" vertical={false} />
          <XAxis
            dataKey="label"
            tick={{ fontSize: 11, fill: '#A8A29E', fontFamily: 'Inter' }}
            axisLine={{ stroke: '#E7E5E4' }}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 11, fill: '#A8A29E', fontFamily: 'Inter' }}
            axisLine={false}
            tickLine={false}
            width={60}
            tickFormatter={v => `\u00a3${v.toLocaleString()}`}
          />
          <Tooltip content={<CustomTooltip />} />
          <Area
            type="monotone"
            dataKey="equity"
            stroke="#4F46E5"
            strokeWidth={2}
            fill="url(#equityFill)"
            dot={false}
            activeDot={{ r: 4, fill: '#4F46E5', stroke: '#FFFFFF', strokeWidth: 2 }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </EquityWrapper>
  )
}

function EquityWrapper({ children }) {
  return (
    <div className="bg-surface border border-border rounded-card p-6 shadow-whisper">
      {children}
    </div>
  )
}

function CustomTooltip({ active, payload }) {
  if (!active || !payload?.[0]) return null
  const data = payload[0].payload
  return (
    <div className="bg-surface border border-border rounded-button px-3 py-2 shadow-lifted">
      <p className="text-xs text-tertiary">{data.label}</p>
      <p className="text-sm font-medium text-primary font-tabular">
        &pound;{data.equity?.toLocaleString('en-GB', { minimumFractionDigits: 2 })}
      </p>
    </div>
  )
}
