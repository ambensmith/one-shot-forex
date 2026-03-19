import { useCountdown } from '../hooks/useCountdown'

const SESSION_COLORS = {
  Sydney: 'bg-purple-500/20 text-purple-300',
  Tokyo: 'bg-red-500/20 text-red-300',
  London: 'bg-blue-500/20 text-blue-300',
  'New York': 'bg-green-500/20 text-green-300',
}

function pad(n) {
  return String(n).padStart(2, '0')
}

export default function NextRunCountdown() {
  const { nextRun, remaining, marketOpen, sessions } = useCountdown()

  const formatCountdown = () => {
    const { hours, minutes, seconds } = remaining
    if (hours > 0) return `${hours}h ${pad(minutes)}m ${pad(seconds)}s`
    return `${pad(minutes)}:${pad(seconds)}`
  }

  const formatNextRun = () => {
    const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
    return `${days[nextRun.getUTCDay()]} ${pad(nextRun.getUTCHours())}:00 UTC`
  }

  return (
    <div className="space-y-2">
      {/* Market status */}
      <div className="flex items-center gap-2">
        <span className={`w-2 h-2 rounded-full ${marketOpen ? 'bg-green-400 animate-pulse' : 'bg-gray-500'}`} />
        <span className="text-xs text-gray-400">
          {marketOpen ? 'Market Open' : 'Market Closed'}
        </span>
      </div>

      {/* Countdown */}
      <div>
        <p className="text-xs text-gray-500 mb-0.5">Next run</p>
        <p className="text-sm font-mono font-semibold text-gray-200">
          {formatCountdown()}
        </p>
        <p className="text-xs text-gray-500 mt-0.5">
          {formatNextRun()}
        </p>
      </div>

      {/* Active sessions */}
      {sessions.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {sessions.map(s => (
            <span
              key={s}
              className={`text-[10px] px-1.5 py-0.5 rounded ${SESSION_COLORS[s] || 'bg-gray-700 text-gray-400'}`}
            >
              {s}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
