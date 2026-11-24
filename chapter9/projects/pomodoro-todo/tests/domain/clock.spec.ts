import { describe, it, expect } from 'vitest'
import { createFakeClock, systemClock } from '../../src/domain/clock'

describe('fake clock', () => {
  it('시작 시각을 반환한다', () => {
    expect(createFakeClock(1000).now()).toBe(1000)
  })
  it('advance로 시간을 진행시킨다', () => {
    const c = createFakeClock(1000)
    c.advance(500)
    c.advance(250)
    expect(c.now()).toBe(1750)
  })
  it('set으로 시각을 지정한다', () => {
    const c = createFakeClock(1000)
    c.set(42)
    expect(c.now()).toBe(42)
  })
})

describe('systemClock', () => {
  it('number를 반환한다', () => {
    expect(typeof systemClock.now()).toBe('number')
  })
})
