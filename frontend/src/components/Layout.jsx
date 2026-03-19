import { NavLink } from 'react-router-dom'
import { BookOpen, Newspaper, BarChart3, Wrench, LayoutDashboard, GitCompare, Settings, History } from 'lucide-react'
import NextRunCountdown from './NextRunCountdown'
import { useDashboard } from '../hooks/useStreamData'

const NAV_ITEMS = [
  { to: '/guide', icon: BookOpen, label: 'Guide' },
  { to: '/news', icon: Newspaper, label: 'News Stream', streamId: 'news' },
  { to: '/strategies', icon: BarChart3, label: 'Strategies', streamId: 'strategy' },
  { to: '/hybrid', icon: Wrench, label: 'Custom Hybrid', streamId: 'hybrid' },
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/runs', icon: History, label: 'Run History' },
  { to: '/models', icon: GitCompare, label: 'Models' },
  { to: '/settings', icon: Settings, label: 'Settings' },
]

function StreamDot({ streamId, streams }) {
  if (!streamId || !streams) return null

  const isHybrid = streamId === 'hybrid'
  const streamData = isHybrid
    ? streams.find(s => s.id?.startsWith('hybrid:'))
    : streams.find(s => s.id === streamId)

  if (!streamData) {
    // Stream exists in config but no data — enabled, no activity
    return <span className="w-2 h-2 rounded-full bg-gray-500 shrink-0" title="No recent activity" />
  }

  const hasActivity = streamData.trade_count > 0 || streamData.signal_count > 0

  if (hasActivity) {
    return (
      <span className="relative w-2 h-2 shrink-0" title="Active">
        <span className="absolute inset-0 rounded-full bg-green-400 animate-pulse" />
        <span className="absolute inset-0 rounded-full bg-green-400" />
      </span>
    )
  }

  return <span className="w-2 h-2 rounded-full bg-gray-500 shrink-0" title="Enabled, no activity" />
}

export default function Layout({ children }) {
  const { data: dashboard } = useDashboard()
  const streams = dashboard?.streams || []

  return (
    <div className="flex h-screen">
      <nav className="w-56 bg-gray-900 border-r border-gray-800 flex flex-col">
        <div className="p-4 border-b border-gray-800">
          <h1 className="text-lg font-bold text-brand-500">Forex Sentinel</h1>
          <p className="text-xs text-gray-500 mt-1">Trading System</p>
        </div>
        <div className="flex-1 py-2">
          {NAV_ITEMS.map(({ to, icon: Icon, label, streamId }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-3 text-sm transition-colors ${
                  isActive
                    ? 'bg-brand-500/10 text-brand-500 border-r-2 border-brand-500'
                    : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800/50'
                }`
              }
            >
              <Icon size={18} />
              <span className="flex-1">{label}</span>
              <StreamDot streamId={streamId} streams={streams} />
            </NavLink>
          ))}
        </div>
        <div className="px-4 py-3 border-t border-gray-800">
          <NextRunCountdown />
        </div>
        <div className="p-4 border-t border-gray-800 text-xs text-gray-600">
          v0.1.0
        </div>
      </nav>
      <main className="flex-1 overflow-y-auto p-6">
        {children}
      </main>
    </div>
  )
}
