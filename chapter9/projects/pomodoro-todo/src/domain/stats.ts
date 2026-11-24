import type { PomodoroRecord } from './types'

/** 브라우저 로컬 시간대 기준, now가 속한 날의 completedAt 개수. */
export function countToday(records: PomodoroRecord[], now: number): number {
  const start = new Date(now)
  start.setHours(0, 0, 0, 0)
  const end = new Date(start)
  end.setDate(end.getDate() + 1)
  const from = start.getTime()
  const to = end.getTime()
  return records.filter((r) => r.completedAt >= from && r.completedAt < to).length
}
