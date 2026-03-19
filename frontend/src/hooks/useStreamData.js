import { useState, useEffect } from 'react'
import { loadDashboard, loadTrades, loadEquity, loadSignals, loadModels } from '../lib/api'

export function useDashboard() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    loadDashboard().then(d => { setData(d); setLoading(false) })
  }, [])
  return { data, loading }
}

export function useTrades(stream) {
  const [trades, setTrades] = useState([])
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    loadTrades().then(t => {
      setTrades(stream ? t.filter(tr => tr.stream === stream) : t)
      setLoading(false)
    })
  }, [stream])
  return { trades, loading }
}

export function useEquity() {
  const [curves, setCurves] = useState({})
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    loadEquity().then(c => { setCurves(c); setLoading(false) })
  }, [])
  return { curves, loading }
}

export function useSignals(stream) {
  const [signals, setSignals] = useState([])
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    loadSignals().then(s => {
      setSignals(stream ? s.filter(sig => sig.stream === stream) : s)
      setLoading(false)
    })
  }, [stream])
  return { signals, loading }
}

export function useModels() {
  const [models, setModels] = useState([])
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    loadModels().then(m => { setModels(m); setLoading(false) })
  }, [])
  return { models, loading }
}
