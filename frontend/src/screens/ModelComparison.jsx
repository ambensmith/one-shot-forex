import { useModels, useSignals } from '../hooks/useStreamData'
import MetricTile from '../components/MetricTile'

export default function ModelComparison() {
  const { models, loading } = useModels()
  const { signals } = useSignals('news')

  if (loading) return <p className="text-gray-500">Loading model data...</p>

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-2xl font-bold">Model Comparison</h2>
        <p className="text-sm text-gray-500 mt-1">Compare LLM performance across providers</p>
      </div>

      {/* Model Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        {models.map(model => (
          <div key={model.key} className="bg-gray-800/50 rounded-lg border border-gray-700/50 p-5">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold text-sm">{model.key}</h3>
              <span className={`text-xs px-2 py-0.5 rounded ${
                model.signal_count > 0 ? 'bg-green-500/20 text-green-400' : 'bg-gray-500/20 text-gray-400'
              }`}>
                {model.signal_count > 0 ? 'Active' : 'Inactive'}
              </span>
            </div>

            <div className="space-y-2 text-xs text-gray-400">
              <div className="flex justify-between">
                <span>Provider</span>
                <span className="text-gray-300">{model.provider}</span>
              </div>
              <div className="flex justify-between">
                <span>Model</span>
                <span className="text-gray-300 font-mono">{model.model}</span>
              </div>
              <div className="flex justify-between">
                <span>Cost</span>
                <span className="text-green-400">Free</span>
              </div>
              <div className="flex justify-between">
                <span>Rate Limit</span>
                <span className="text-gray-300">{model.rate_limit}</span>
              </div>
              <div className="flex justify-between">
                <span>Signals</span>
                <span className="text-gray-300">{model.signal_count}</span>
              </div>
            </div>

            {model.direction_breakdown && (
              <div className="mt-3 pt-3 border-t border-gray-700/50">
                <div className="text-xs text-gray-500 mb-1">Signal Breakdown</div>
                <div className="flex gap-2">
                  {Object.entries(model.direction_breakdown).map(([dir, count]) => (
                    <span key={dir} className={`text-xs px-2 py-0.5 rounded ${
                      dir === 'long' ? 'bg-green-500/10 text-green-400' :
                      dir === 'short' ? 'bg-red-500/10 text-red-400' :
                      'bg-gray-500/10 text-gray-400'
                    }`}>
                      {dir}: {count}
                    </span>
                  ))}
                </div>
              </div>
            )}

            <p className="text-xs text-gray-600 mt-3">{model.notes}</p>
          </div>
        ))}
      </div>

      {/* Comparison Table */}
      {models.some(m => m.signal_count > 0) && (
        <div className="bg-gray-800/50 rounded-lg border border-gray-700/50 p-5">
          <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">
            Signal Agreement Analysis
          </h3>
          <p className="text-xs text-gray-500 mb-4">
            Showing how different LLMs trade the same news. Data updates when you fetch news on the News Stream page.
          </p>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-700 text-left text-xs text-gray-500 uppercase">
                <th className="pb-2">Model</th>
                <th className="pb-2">Total Signals</th>
                <th className="pb-2">Long %</th>
                <th className="pb-2">Short %</th>
                <th className="pb-2">Neutral %</th>
              </tr>
            </thead>
            <tbody>
              {models.filter(m => m.signal_count > 0).map(model => {
                const total = model.signal_count
                const bd = model.direction_breakdown || {}
                return (
                  <tr key={model.key} className="border-b border-gray-800/50">
                    <td className="py-2 font-mono text-xs">{model.key}</td>
                    <td className="py-2">{total}</td>
                    <td className="py-2 text-green-400">{total ? ((bd.long || 0) / total * 100).toFixed(0) : 0}%</td>
                    <td className="py-2 text-red-400">{total ? ((bd.short || 0) / total * 100).toFixed(0) : 0}%</td>
                    <td className="py-2 text-gray-400">{total ? ((bd.neutral || 0) / total * 100).toFixed(0) : 0}%</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
