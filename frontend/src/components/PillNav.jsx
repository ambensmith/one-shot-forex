import { NavLink } from 'react-router-dom'
import { Settings, ChevronUp } from 'lucide-react'

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard' },
  { to: '/llm', label: 'LLM Analysis' },
  { to: '/strategies', label: 'Strategies' },
]

export default function PillNav({ expanded, onToggleExpand }) {
  return (
    <nav
      className="fixed bottom-5 left-1/2 -translate-x-1/2 z-50 flex items-center gap-1 px-2 py-1.5 rounded-pill max-w-[480px]"
      style={{
        background: 'rgba(28, 25, 23, 0.92)',
        backdropFilter: 'blur(12px)',
        WebkitBackdropFilter: 'blur(12px)',
        boxShadow: '0 8px 32px rgba(0,0,0,0.08), 0 2px 8px rgba(0,0,0,0.04)',
      }}
    >
      {NAV_ITEMS.map(({ to, label }) => (
        <NavLink
          key={to}
          to={to}
          end={to === '/'}
          className={({ isActive }) =>
            `px-4 py-2.5 text-[13px] font-medium transition-colors duration-150 rounded-[10px] whitespace-nowrap ${
              isActive
                ? 'text-[#FAFAF9]'
                : 'text-[rgba(250,250,249,0.5)] hover:text-[rgba(250,250,249,0.75)]'
            }`
          }
          style={({ isActive }) =>
            isActive ? { background: 'rgba(250, 250, 249, 0.12)' } : undefined
          }
        >
          {label}
        </NavLink>
      ))}

      <NavLink
        to="/settings"
        className={({ isActive }) =>
          `p-2.5 transition-colors duration-150 rounded-[10px] ${
            isActive
              ? 'text-[#FAFAF9]'
              : 'text-[rgba(250,250,249,0.5)] hover:text-[rgba(250,250,249,0.75)]'
          }`
        }
        style={({ isActive }) =>
          isActive ? { background: 'rgba(250, 250, 249, 0.12)' } : undefined
        }
      >
        <Settings size={18} />
      </NavLink>

      <button
        onClick={onToggleExpand}
        className="p-2.5 text-[rgba(250,250,249,0.5)] hover:text-[rgba(250,250,249,0.75)] transition-all duration-300 rounded-[10px]"
        aria-label="Toggle account summary"
      >
        <ChevronUp
          size={18}
          className="transition-transform duration-300"
          style={{
            transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)',
          }}
        />
      </button>
    </nav>
  )
}
