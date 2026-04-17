import { useState, useEffect, useRef, useCallback } from 'react'
import { fetchOpenTrades, fetchClosedTrades, fetchTradeDetail, fetchBias, fetchEquity, fetchPerformance } from '../lib/api'

export function useOpenTrades(pollInterval = 30000) {
  const [trades, setTrades] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const intervalRef = useRef(null)

  const refresh = useCallback(async () => {
    try {
      const data = await fetchOpenTrades()
      setTrades(data)
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refresh()
    intervalRef.current = setInterval(refresh, pollInterval)
    return () => clearInterval(intervalRef.current)
  }, [refresh, pollInterval])

  return { trades, loading, error, refresh }
}

export function useClosedTrades(filters = {}) {
  const [trades, setTrades] = useState([])
  const [count, setCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [limit, setLimit] = useState(20)

  const load = useCallback(async (currentLimit) => {
    setLoading(true)
    try {
      const data = await fetchClosedTrades({ ...filters, limit: currentLimit })
      setTrades(data.trades)
      setCount(data.count)
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [filters.filter, filters.instrument, filters.source])

  useEffect(() => {
    setLimit(20)
    load(20)
  }, [load])

  const loadMore = useCallback(() => {
    const newLimit = limit + 20
    setLimit(newLimit)
    load(newLimit)
  }, [limit, load])

  return { trades, count, loading, error, loadMore, hasMore: count >= limit }
}

export function useBias() {
  const [instruments, setInstruments] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchBias()
      .then(data => { setInstruments(data); setError(null) })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  return { instruments, loading, error }
}

export function useEquity(stream) {
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchEquity(stream)
      .then(d => { setData(d); setError(null) })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [stream])

  return { data, loading, error }
}

export function usePerformance() {
  const [series, setSeries] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchPerformance()
      .then(s => { setSeries(s); setError(null) })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  return { series, loading, error }
}

export function useTradeDetail(tradeId) {
  const [record, setRecord] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!tradeId) {
      setRecord(null)
      return
    }
    setLoading(true)
    fetchTradeDetail(tradeId)
      .then(data => { setRecord(data); setError(null) })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [tradeId])

  return { record, loading, error }
}
