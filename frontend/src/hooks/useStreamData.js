import { useState, useEffect, useCallback } from 'react'
import { loadDashboard, loadTrades, loadEquity, loadSignals, loadModels, loadReview, loadHybrids } from '../lib/api'

export function useDashboard() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const refresh = useCallback(() => {
    setLoading(true)
    loadDashboard().then(d => { setData(d); setLoading(false) })
  }, [])
  useEffect(() => { refresh() }, [refresh])
  return { data, loading, refresh }
}

export function useTrades(stream) {
  const [trades, setTrades] = useState([])
  const [loading, setLoading] = useState(true)
  const refresh = useCallback(() => {
    setLoading(true)
    loadTrades().then(t => {
      setTrades(stream ? t.filter(tr => tr.stream === stream) : t)
      setLoading(false)
    })
  }, [stream])
  useEffect(() => { refresh() }, [refresh])
  return { trades, loading, refresh }
}

export function useEquity() {
  const [curves, setCurves] = useState({})
  const [loading, setLoading] = useState(true)
  const refresh = useCallback(() => {
    setLoading(true)
    loadEquity().then(c => { setCurves(c); setLoading(false) })
  }, [])
  useEffect(() => { refresh() }, [refresh])
  return { curves, loading, refresh }
}

export function useSignals(stream) {
  const [signals, setSignals] = useState([])
  const [loading, setLoading] = useState(true)
  const refresh = useCallback(() => {
    setLoading(true)
    loadSignals().then(s => {
      setSignals(stream ? s.filter(sig => sig.stream === stream) : s)
      setLoading(false)
    })
  }, [stream])
  useEffect(() => { refresh() }, [refresh])
  return { signals, loading, refresh }
}

export function useModels() {
  const [models, setModels] = useState([])
  const [loading, setLoading] = useState(true)
  const refresh = useCallback(() => {
    setLoading(true)
    loadModels().then(m => { setModels(m); setLoading(false) })
  }, [])
  useEffect(() => { refresh() }, [refresh])
  return { models, loading, refresh }
}

export function useReview() {
  const [review, setReview] = useState(null)
  const [loading, setLoading] = useState(true)
  const refresh = useCallback(() => {
    setLoading(true)
    loadReview().then(r => { setReview(r); setLoading(false) })
  }, [])
  useEffect(() => { refresh() }, [refresh])
  return { review, loading, refresh }
}

export function useHybrids() {
  const [hybrids, setHybrids] = useState([])
  const [loading, setLoading] = useState(true)
  const refresh = useCallback(() => {
    setLoading(true)
    loadHybrids().then(h => { setHybrids(h); setLoading(false) })
  }, [])
  useEffect(() => { refresh() }, [refresh])
  return { hybrids, loading, refresh }
}
