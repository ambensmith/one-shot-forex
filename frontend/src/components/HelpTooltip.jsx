import { useState, useRef, useEffect } from 'react'
import GLOSSARY from '../lib/glossary'

/**
 * HelpTooltip — inline (i) icon that shows a plain-English explanation on hover/click.
 *
 * Usage:
 *   <HelpTooltip term="sharpe_ratio" />           — looks up from GLOSSARY
 *   <HelpTooltip text="Custom explanation" />      — inline text
 *   <HelpTooltip term="atr" hint={false} />        — suppress the hint line
 */
export default function HelpTooltip({ term, text, hint = true }) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  const entry = term ? GLOSSARY[term] : null
  const displayText = text || entry?.definition
  const hintText = hint && entry?.hint

  // Close on outside click
  useEffect(() => {
    if (!open) return
    function handleClick(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [open])

  if (!displayText) return null

  return (
    <span className="relative inline-flex items-center" ref={ref}>
      <button
        type="button"
        onClick={(e) => { e.preventDefault(); e.stopPropagation(); setOpen(!open) }}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        className="ml-1 w-3.5 h-3.5 rounded-full bg-gray-600/60 text-gray-400 hover:bg-gray-500/60 hover:text-gray-300 inline-flex items-center justify-center text-[9px] font-bold leading-none transition-colors cursor-help shrink-0"
        aria-label={entry?.term || 'Help'}
      >
        i
      </button>
      {open && (
        <div className="absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 bg-gray-800 border border-gray-600/50 rounded-lg shadow-xl p-3 text-left pointer-events-none">
          {entry?.term && (
            <div className="text-xs font-semibold text-gray-200 mb-1">{entry.term}</div>
          )}
          <p className="text-xs text-gray-300 leading-relaxed">{displayText}</p>
          {hintText && (
            <p className="text-xs text-gray-500 mt-1.5 leading-relaxed italic">{hintText}</p>
          )}
          {/* Arrow */}
          <div className="absolute top-full left-1/2 -translate-x-1/2 w-2 h-2 bg-gray-800 border-r border-b border-gray-600/50 transform rotate-45 -mt-1" />
        </div>
      )}
    </span>
  )
}
