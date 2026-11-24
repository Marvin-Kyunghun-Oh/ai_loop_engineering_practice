import { describe, expect, it } from 'vitest'
import { countToday } from '../../src/domain/stats'

const at = (d: number, h: number, m: number, s: number, ms: number) =>
  new Date(2026, 5, d, h, m, s, ms).getTime()
const rec = (completedAt: number) => ({ taskId: 'a', completedAt })

describe('countToday', () => {
  const now = at(10, 12, 0, 0, 0)

  it('빈 배열이면 0', () => {
    expect(countToday([], now)).toBe(0)
  })

  it('오늘 경계(00:00:00.000, 23:59:59.999)는 포함한다', () => {
    expect(countToday([rec(at(10, 0, 0, 0, 0)), rec(at(10, 23, 59, 59, 999))], now)).toBe(2)
  })

  it('어제 23:59:59.999와 내일 00:00:00.000은 제외한다', () => {
    expect(countToday([rec(at(9, 23, 59, 59, 999)), rec(at(11, 0, 0, 0, 0))], now)).toBe(0)
  })
})
