import { useState, useEffect, useCallback, useRef } from 'react'
import { loadLivePositions } from '../lib/api'

/**
 * Hook for auto-refreshing live position data from Capital.com.
 * @param {Object} options
 * @param {number} options.interval - Refresh interval in ms (default 30000)
 * @param {boolean} options.enabled - Whether auto-refresh is active (default true)
 * @returns {{ positions, account, timestamp, loading, error, refresh, enabled, setEnabled }}
 */
export default function useLivePositions({ interval = 30000, enabled: initialEnabled = true } = {}) {
  const [data, setData] = useState({ positions: [], account: null, timestamp: null })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [enabled, setEnabled] = useState(initialEnabled)
  const intervalRef = useRef(null)

  const refresh = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await loadLivePositions()
      if (result) {
        setData(result)
      } else {
        setError('Failed to fetch live positions')
      }
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (!enabled) {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
      return
    }

    // Initial fetch
    refresh()

    // Set up interval
    intervalRef.current = setInterval(refresh, interval)

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
    }
  }, [enabled, interval, refresh])

  return {
    positions: data.positions || [],
    account: data.account,
    timestamp: data.timestamp,
    loading,
    error,
    refresh,
    enabled,
    setEnabled,
  }
}
