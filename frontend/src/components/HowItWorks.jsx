/**
 * HowItWorks — collapsible explainer section for each page.
 * Uses <details> element for native expand/collapse.
 */
export default function HowItWorks({ children }) {
  return (
    <details className="bg-blue-900/10 border border-blue-800/30 rounded-lg mb-6 group">
      <summary className="px-4 py-3 cursor-pointer text-sm text-blue-300 hover:text-blue-200 transition-colors flex items-center gap-2 select-none">
        <svg className="w-4 h-4 shrink-0 transition-transform group-open:rotate-90" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
        </svg>
        How this works
      </summary>
      <div className="px-4 pb-4 text-sm text-gray-300 leading-relaxed space-y-2">
        {children}
      </div>
    </details>
  )
}
