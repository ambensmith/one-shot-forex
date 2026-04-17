import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, ReferenceLine } from 'recharts'
import { usePerformance } from '../hooks/useDashboardData'

const COLORS = {
  LLM: '#0EA5E9',
  Momentum: '#4F46E5',
  Carry: '#F59E0B',
  Breakout: '#10B981',
  'Mean reversion': '#EC4899',
  'Volatility breakout': '#8B5CF6',
}

export default function PerformanceChart() {
  const { series, loading } = usePerformance()

  if (loading) {
    return <Wrapper><p className="text-sm italic text-tertiary">Loading performance data...</p></Wrapper>
  }

  const hasAny = series.some(s => s.points && s.points.length > 0)
  if (!hasAny) {
    return (
      <Wrapper>
        <p className="text-sm italic text-tertiary">
          Performance lines will appear after the first trade closes in each series.
        </p>
      </Wrapper>
    )
  }

  // Merge all series onto a single shared time axis so Recharts can draw
  // multiple lines over a common X-axis. Each timestamp carries the latest
  // cumulative PnL for every series (so lines look connected rather than
  // sampled only where they have data).
  const allTimestamps = new Set()
  for (const s of series) {
    for (const p of s.points) allTimestamps.add(p.timestamp)
  }
  const sortedTimestamps = [...allTimestamps].sort()

  const lastValue = {}
  const chartData = sortedTimestamps.map(ts => {
    const row = {
      timestamp: ts,
      label: new Date(ts).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' }),
    }
    for (const s of series) {
      const point = s.points.find(p => p.timestamp === ts)
      if (point) lastValue[s.name] = point.pnl
      if (s.name in lastValue) row[s.name] = lastValue[s.name]
    }
    return row
  })

  const activeSeries = series.filter(s => s.points.length > 0)

  return (
    <Wrapper>
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={chartData} margin={{ top: 8, right: 16, bottom: 0, left: 8 }}>
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
            tickFormatter={v => `${v >= 0 ? '+' : ''}€${v.toFixed(2)}`}
            domain={['auto', 'auto']}
          />
          <ReferenceLine y={0} stroke="#A8A29E" strokeDasharray="4 4" />
          <Tooltip content={<CustomTooltip />} />
          <Legend wrapperStyle={{ fontSize: 11, paddingTop: 8 }} iconType="line" />
          {activeSeries.map(s => (
            <Line
              key={s.name}
              type="stepAfter"
              dataKey={s.name}
              stroke={COLORS[s.name] || '#6B7280'}
              strokeWidth={2}
              dot={false}
              connectNulls
              activeDot={{ r: 4, fill: COLORS[s.name] || '#6B7280', stroke: '#FFFFFF', strokeWidth: 2 }}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </Wrapper>
  )
}

function Wrapper({ children }) {
  return (
    <div className="bg-surface border border-border rounded-card p-6 shadow-whisper">
      {children}
    </div>
  )
}

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-surface border border-border rounded-button px-3 py-2 shadow-lifted">
      <p className="text-xs text-tertiary mb-1">{label}</p>
      {payload.map(entry => (
        <p key={entry.dataKey} className="text-sm font-tabular" style={{ color: entry.color }}>
          {entry.dataKey}: {entry.value >= 0 ? '+' : ''}€{entry.value?.toFixed(2)}
        </p>
      ))}
    </div>
  )
}
