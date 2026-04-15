import { useEquity } from '../hooks/useDashboardData'

export default function AccountPanel({ expanded }) {
  const { data } = useEquity()

  // Derive latest equity and P&L % from equity history
  let equity = null
  let pnlPct = null
  if (data && data.length > 0) {
    const latest = data[data.length - 1]
    equity = latest.equity
    if (data.length > 1) {
      const first = data[0]
      if (first.equity && first.equity > 0) {
        pnlPct = ((latest.equity - first.equity) / first.equity) * 100
      }
    }
  }

  const pnlColor = pnlPct == null
    ? 'text-[#A8A29E]'
    : pnlPct >= 0
      ? 'text-profitable-text'
      : 'text-loss-text'

  return (
    <div
      className="fixed left-1/2 -translate-x-1/2 z-40 max-w-[480px] w-full px-6 py-4 pb-5 transition-all"
      style={{
        bottom: '20px',
        background: '#292524',
        borderRadius: '14px 14px 16px 16px',
        transform: expanded
          ? 'translateX(-50%) translateY(-8px)'
          : 'translateX(-50%) translateY(100%)',
        opacity: expanded ? 1 : 0,
        transitionProperty: 'transform, opacity',
        transitionDuration: '300ms, 200ms',
        transitionTimingFunction: 'cubic-bezier(0.4, 0, 0.2, 1), ease',
      }}
    >
      <div className="flex items-center justify-between">
        <div>
          <p className="text-[11px] font-semibold tracking-[0.8px] uppercase text-[rgba(250,250,249,0.5)]">
            Account
          </p>
          <p className="text-lg font-semibold text-[#FAFAF9] font-tabular">
            {equity != null ? `€${equity.toLocaleString('en-IE', { minimumFractionDigits: 2 })}` : '\u2014'}
          </p>
        </div>
        <div className="text-right">
          <p className="text-[11px] font-semibold tracking-[0.8px] uppercase text-[rgba(250,250,249,0.5)]">
            All Time
          </p>
          <p className={`text-sm font-medium font-tabular ${pnlColor}`}>
            {pnlPct != null ? `${pnlPct >= 0 ? '+' : ''}${pnlPct.toFixed(1)}%` : '\u2014'}
          </p>
        </div>
      </div>
    </div>
  )
}
