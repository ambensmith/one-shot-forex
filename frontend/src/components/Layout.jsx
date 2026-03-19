import { NavLink } from 'react-router-dom'
import { Newspaper, BarChart3, Wrench, LayoutDashboard, GitCompare } from 'lucide-react'

const NAV_ITEMS = [
  { to: '/news', icon: Newspaper, label: 'News Stream' },
  { to: '/strategies', icon: BarChart3, label: 'Strategies' },
  { to: '/hybrid', icon: Wrench, label: 'Custom Hybrid' },
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/models', icon: GitCompare, label: 'Models' },
]

export default function Layout({ children }) {
  return (
    <div className="flex h-screen">
      <nav className="w-56 bg-gray-900 border-r border-gray-800 flex flex-col">
        <div className="p-4 border-b border-gray-800">
          <h1 className="text-lg font-bold text-brand-500">Forex Sentinel</h1>
          <p className="text-xs text-gray-500 mt-1">Trading System</p>
        </div>
        <div className="flex-1 py-2">
          {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
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
              {label}
            </NavLink>
          ))}
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
