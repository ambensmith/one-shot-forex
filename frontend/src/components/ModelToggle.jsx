export default function ModelToggle({ label, enabled, onToggle }) {
  return (
    <button
      onClick={onToggle}
      className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
        enabled
          ? 'bg-brand-500/20 text-brand-500 border border-brand-500/30'
          : 'bg-gray-800 text-gray-500 border border-gray-700'
      }`}
    >
      <span className={`w-2 h-2 rounded-full ${enabled ? 'bg-brand-500' : 'bg-gray-600'}`} />
      {label}
    </button>
  )
}
