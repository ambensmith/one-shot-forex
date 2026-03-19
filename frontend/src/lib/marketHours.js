/**
 * Market hours utilities.
 * Forex market: Sunday 22:00 UTC — Friday 22:00 UTC.
 */

export function isMarketOpen(date = new Date()) {
  const day = date.getUTCDay()     // 0=Sun, 6=Sat
  const hour = date.getUTCHours()

  if (day === 6) return false                    // Saturday
  if (day === 0 && hour < 22) return false       // Sunday before 22:00
  if (day === 5 && hour >= 22) return false      // Friday after 22:00
  return true
}

export function getNextRunTime(from = new Date()) {
  const next = new Date(from)
  next.setUTCMinutes(0, 0, 0)
  next.setUTCHours(next.getUTCHours() + 1)

  let safety = 0
  while (!isMarketOpen(next) && safety < 200) {
    next.setUTCHours(next.getUTCHours() + 1)
    safety++
  }

  return next
}

export function getCurrentSessions(date = new Date()) {
  const h = date.getUTCHours()
  const sessions = []
  if (h >= 22 || h < 7) sessions.push('Sydney')
  if (h >= 0 && h < 9) sessions.push('Tokyo')
  if (h >= 7 && h < 16) sessions.push('London')
  if (h >= 12 && h < 22) sessions.push('New York')
  return sessions
}
