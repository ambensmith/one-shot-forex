import HelpTooltip from './HelpTooltip'

export default function MetricTile({ label, value, subtext, positive, helpTerm }) {
  const valueColor = positive === true
    ? 'text-green-400'
    : positive === false
      ? 'text-red-400'
      : 'text-gray-100'

  return (
    <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700/50">
      <div className="text-xs text-gray-500 uppercase tracking-wider flex items-center">
        {label}
        {helpTerm && <HelpTooltip term={helpTerm} />}
      </div>
      <div className={`text-xl font-semibold mt-1 ${valueColor}`}>{value}</div>
      {subtext && <div className="text-xs text-gray-500 mt-1">{subtext}</div>}
    </div>
  )
}
