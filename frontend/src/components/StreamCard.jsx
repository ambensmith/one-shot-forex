import SignalBadge from './SignalBadge'
import { timeAgo } from '../lib/constants'

export default function StreamCard({ signal }) {
  const { instrument, direction, confidence, reasoning, sources, created_at } = signal

  return (
    <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700/50">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <SignalBadge direction={direction} />
          <span className="font-mono text-sm font-semibold">{instrument}</span>
        </div>
        <span className="text-xs text-gray-500">{timeAgo(created_at)}</span>
      </div>
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xs text-gray-400">Confidence:</span>
        <div className="flex-1 bg-gray-700 rounded-full h-2">
          <div
            className="h-2 rounded-full transition-all"
            style={{
              width: `${(confidence || 0) * 100}%`,
              backgroundColor: confidence >= 0.7 ? '#37b24d' : confidence >= 0.5 ? '#f59f00' : '#868e96',
            }}
          />
        </div>
        <span className="text-xs font-mono">{((confidence || 0) * 100).toFixed(0)}%</span>
      </div>
      {reasoning && (
        <p className="text-xs text-gray-400 line-clamp-2">{reasoning}</p>
      )}
      {sources?.length > 0 && (
        <div className="mt-2 flex gap-1">
          {sources.map(s => (
            <span key={s} className="text-xs bg-gray-700/50 px-2 py-0.5 rounded">{s}</span>
          ))}
        </div>
      )}
    </div>
  )
}
