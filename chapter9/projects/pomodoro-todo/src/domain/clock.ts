export interface Clock {
  now(): number
}

export const systemClock: Clock = {
  now: () => Date.now(),
}

export interface FakeClock extends Clock {
  advance(ms: number): void
  set(ms: number): void
}

export function createFakeClock(start: number): FakeClock {
  let current = start
  return {
    now: () => current,
    advance(ms: number) {
      current += ms
    },
    set(ms: number) {
      current = ms
    },
  }
}
