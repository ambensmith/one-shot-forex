import { useState } from 'react'
import PillNav from './PillNav'
import AccountPanel from './AccountPanel'

export default function Layout({ children }) {
  const [panelExpanded, setPanelExpanded] = useState(false)

  return (
    <div className="min-h-screen bg-canvas">
      <main className="max-w-content mx-auto px-8 pt-12 pb-24 max-sm:px-5 max-sm:pt-8">
        <div className="font-serif text-[11px] tracking-[0.22em] uppercase text-tertiary mb-2">
          One Shot Forex
        </div>
        {children}
      </main>
      <AccountPanel expanded={panelExpanded} />
      <PillNav
        expanded={panelExpanded}
        onToggleExpand={() => setPanelExpanded(prev => !prev)}
      />
    </div>
  )
}
