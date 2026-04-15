import { useState, useEffect, useCallback } from 'react'
import { fetchLLMActivity, fetchStrategies, fetchPrompts, updatePrompt, fetchStatus } from '../lib/api'

export function useLLMActivity() {
  const [data, setData] = useState({ headlines_by_source: {}, relevance_assessments: [], signals: [], summary: {} })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchLLMActivity(12)
      .then(d => { setData(d); setError(null) })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  return { data, loading, error }
}

export function usePrompts() {
  const [prompts, setPrompts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [saving, setSaving] = useState(null)

  const load = useCallback(() => {
    fetchPrompts()
      .then(d => { setPrompts(d); setError(null) })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { load() }, [load])

  const save = useCallback(async (name, template, currentVersion) => {
    setSaving(name)
    try {
      await updatePrompt(name, template, currentVersion)
      await load()
      return true
    } catch (err) {
      setError(err.message)
      return false
    } finally {
      setSaving(null)
    }
  }, [load])

  return { prompts, loading, error, save, saving }
}

export function useStrategies() {
  const [strategies, setStrategies] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchStrategies()
      .then(d => { setStrategies(d); setError(null) })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  return { strategies, loading, error }
}

export function useSystemStatus() {
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchStatus()
      .then(d => setStatus(d))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  return { status, loading }
}
