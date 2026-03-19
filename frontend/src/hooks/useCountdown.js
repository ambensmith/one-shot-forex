import { useState, useEffect } from 'react'
import { isMarketOpen, getNextRunTime, getCurrentSessions } from '../lib/marketHours'

function getRemainingTime(target) {
  const diff = Math.max(0, target.getTime() - Date.now())
  const hours = Math.floor(diff / 3600000)
  const minutes = Math.floor((diff % 3600000) / 60000)
  const seconds = Math.floor((diff % 60000) / 1000)
  return { hours, minutes, seconds, total: diff }
}

export function useCountdown() {
  const [nextRun, setNextRun] = useState(() => getNextRunTime())
  const [remaining, setRemaining] = useState(() => getRemainingTime(getNextRunTime()))
  const [marketOpen, setMarketOpen] = useState(() => isMarketOpen())
  const [sessions, setSessions] = useState(() => getCurrentSessions())

  useEffect(() => {
    const interval = setInterval(() => {
      const now = new Date()

      if (now >= nextRun) {
        const newNext = getNextRunTime(now)
        setNextRun(newNext)
        setRemaining(getRemainingTime(newNext))
      } else {
        setRemaining(getRemainingTime(nextRun))
      }

      setMarketOpen(isMarketOpen(now))
      setSessions(getCurrentSessions(now))
    }, 1000)

    return () => clearInterval(interval)
  }, [nextRun])

  return { nextRun, remaining, marketOpen, sessions }
}
