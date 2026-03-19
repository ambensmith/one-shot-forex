import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import { STREAM_COLORS } from '../lib/constants'

export default function EquityCurve({ curves, height = 300 }) {
  // Merge all curves into a single dataset
  const allTimes = new Set()
  const streamIds = Object.keys(curves)

  streamIds.forEach(sid => {
    curves[sid]?.forEach(pt => allTimes.add(pt.time))
  })

  const sortedTimes = [...allTimes].sort()
  const data = sortedTimes.map(time => {
    const point = { time: new Date(time).toLocaleDateString() }
    streamIds.forEach(sid => {
      const match = curves[sid]?.find(p => p.time === time)
      if (match) point[sid] = match.equity
    })
    return point
  })

  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-gray-500 text-sm">
        No equity data yet. Run a trading cycle to generate data.
      </div>
    )
  }

  const colors = ['#4c6ef5', '#37b24d', '#f59f00', '#f03e3e', '#ae3ec9']

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#333" />
        <XAxis dataKey="time" tick={{ fill: '#888', fontSize: 11 }} />
        <YAxis tick={{ fill: '#888', fontSize: 11 }} />
        <Tooltip
          contentStyle={{ backgroundColor: '#1a1a2e', border: '1px solid #333', borderRadius: 8 }}
          labelStyle={{ color: '#aaa' }}
        />
        <Legend />
        {streamIds.map((sid, i) => (
          <Line
            key={sid}
            type="monotone"
            dataKey={sid}
            stroke={colors[i % colors.length]}
            strokeWidth={2}
            dot={false}
            name={sid}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  )
}
