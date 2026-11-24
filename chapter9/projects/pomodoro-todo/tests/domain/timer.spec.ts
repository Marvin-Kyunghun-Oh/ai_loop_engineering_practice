import { describe, it, expect } from 'vitest'
import { BREAK_MS, FOCUS_MS, type TimerState } from '../../src/domain/types'
import {
  idleTimer,
  startFocus,
  pause,
  resume,
  cancel,
  advance,
  remainingMs,
  formatMmSs,
  clickTask,
  confirmSwitch,
  restore,
} from '../../src/domain/timer'

const MIN = 60 * 1000
const T0 = 1_000_000_000

describe('restore', () => {
  const exists = () => true
  it('집중 중 저장 → 10분 뒤: focus, 남은 15분', () => {
    const r = restore(startFocus('a', T0), T0 + 10 * MIN, exists)
    expect(r.state.phase).toBe('focus')
    expect(remainingMs(r.state, T0 + 10 * MIN)).toBe(15 * MIN)
    expect(r.completed).toEqual([])
  })
  it('종료 예정 +2분 → break 남은 3분, 완료 1건', () => {
    const r = restore(startFocus('a', T0), T0 + FOCUS_MS + 2 * MIN, exists)
    expect(r.state.phase).toBe('break')
    expect(remainingMs(r.state, T0 + FOCUS_MS + 2 * MIN)).toBe(3 * MIN)
    expect(r.completed).toEqual([{ taskId: 'a', completedAt: T0 + FOCUS_MS }])
  })
  it('종료 예정 +10분 → idle, 완료 1건', () => {
    const r = restore(startFocus('a', T0), T0 + FOCUS_MS + 10 * MIN, exists)
    expect(r.state).toEqual(idleTimer())
    expect(r.completed).toEqual([{ taskId: 'a', completedAt: T0 + FOCUS_MS }])
  })
  it('일시정지 저장 → 1시간 뒤에도 남은 7분 일시정지', () => {
    const p = pause(startFocus('a', T0), T0 + FOCUS_MS - 7 * MIN)
    const r = restore(p, T0 + 3 * 60 * MIN, exists)
    expect(r.state.paused).toBe(true)
    expect(remainingMs(r.state, T0 + 3 * 60 * MIN)).toBe(7 * MIN)
    expect(r.completed).toEqual([])
  })
  it('대상 할 일 삭제 → idle', () => {
    const r = restore(startFocus('a', T0), T0 + MIN, () => false)
    expect(r.state).toEqual(idleTimer())
    expect(r.completed).toEqual([])
  })
})

describe('clickTask / confirmSwitch', () => {
  it('idle에서 클릭 → started', () => {
    const r = clickTask(idleTimer(), 'A', T0)
    expect(r.kind).toBe('started')
    if (r.kind === 'started') {
      expect(r.state.taskId).toBe('A')
      expect(r.state.phase).toBe('focus')
      expect(r.state.endsAt).toBe(T0 + 25 * MIN)
    }
  })

  it('focus 중 같은 할 일 클릭 → noop (일시정지 포함)', () => {
    const s = startFocus('A', T0)
    expect(clickTask(s, 'A', T0 + MIN)).toEqual({ kind: 'noop' })
    const p = pause(s, T0 + MIN)
    expect(clickTask(p, 'A', T0 + 2 * MIN)).toEqual({ kind: 'noop' })
  })

  it('focus 중 다른 할 일 → confirmNeeded, confirmSwitch는 새 할 일로 시작', () => {
    const s = startFocus('A', T0)
    expect(clickTask(s, 'B', T0 + MIN)).toEqual({ kind: 'confirmNeeded' })
    const n = confirmSwitch('B', T0 + MIN)
    expect(n.taskId).toBe('B')
    expect(n.phase).toBe('focus')
    expect(n.endsAt).toBe(T0 + MIN + 25 * MIN)
  })

  it('break 중(일시정지 포함) 클릭 → started, 새 할 일로 focus', () => {
    const b = advance(startFocus('A', T0), T0 + 26 * MIN).state
    expect(b.phase).toBe('break')
    const r1 = clickTask(b, 'B', T0 + 26 * MIN)
    expect(r1.kind).toBe('started')
    if (r1.kind === 'started') {
      expect(r1.state.phase).toBe('focus')
      expect(r1.state.taskId).toBe('B')
    }
    const pb = pause(b, T0 + 27 * MIN)
    const r2 = clickTask(pb, 'A', T0 + 28 * MIN)
    expect(r2.kind).toBe('started')
    if (r2.kind === 'started') {
      expect(r2.state.phase).toBe('focus')
      expect(r2.state.paused).toBe(false)
      expect(r2.state.endsAt).toBe(T0 + 28 * MIN + 25 * MIN)
    }
  })
})

describe('constants', () => {
  it('FOCUS_MS, BREAK_MS', () => {
    expect(FOCUS_MS).toBe(1_500_000)
    expect(BREAK_MS).toBe(300_000)
  })
})

describe('idleTimer / startFocus', () => {
  it('idleTimer', () => {
    expect(idleTimer()).toEqual({
      phase: 'idle',
      paused: false,
      taskId: null,
      endsAt: null,
      remainingMs: null,
    })
  })

  it('startFocus 후 7분 경과 시 남은 18분', () => {
    const s = startFocus('a', T0)
    expect(s.phase).toBe('focus')
    expect(s.paused).toBe(false)
    expect(s.taskId).toBe('a')
    expect(s.endsAt).toBe(T0 + FOCUS_MS)
    expect(s.remainingMs).toBeNull()
    expect(remainingMs(s, T0 + 7 * MIN)).toBe(18 * MIN)
  })
})

describe('pause / resume', () => {
  it('일시정지 후 재개하면 남은 시간이 보존된다', () => {
    const s0 = startFocus('a', T0)
    const s1 = pause(s0, T0 + 10 * MIN)
    expect(s1.paused).toBe(true)
    expect(s1.endsAt).toBeNull()
    expect(s1.remainingMs).toBe(15 * MIN)
    expect(remainingMs(s1, T0 + 15 * MIN)).toBe(15 * MIN)
    const s2 = resume(s1, T0 + 15 * MIN)
    expect(s2.paused).toBe(false)
    expect(s2.remainingMs).toBeNull()
    expect(remainingMs(s2, T0 + 30 * MIN)).toBe(0)
    expect(remainingMs(s2, T0 + 29 * MIN)).toBe(1 * MIN)
  })

  it('idle에서 pause/resume은 불변', () => {
    const s = idleTimer()
    expect(pause(s, T0)).toEqual(s)
    expect(resume(s, T0)).toEqual(s)
  })

  it('이미 일시정지면 pause는 불변', () => {
    const p = pause(startFocus('a', T0), T0 + MIN)
    expect(pause(p, T0 + 5 * MIN)).toEqual(p)
  })

  it('진행 중이면 resume은 불변', () => {
    const s = startFocus('a', T0)
    expect(resume(s, T0 + MIN)).toEqual(s)
  })

  it('break도 일시정지할 수 있다', () => {
    const b: TimerState = { phase: 'break', paused: false, taskId: 'a', endsAt: T0 + BREAK_MS, remainingMs: null }
    const p = pause(b, T0 + MIN)
    expect(p.paused).toBe(true)
    expect(p.remainingMs).toBe(4 * MIN)
  })

  it('종료 시각 이후 pause 시 remainingMs는 0 이상', () => {
    const p = pause(startFocus('a', T0), T0 + 40 * MIN)
    expect(p.remainingMs).toBe(0)
  })
})

describe('cancel', () => {
  it('모든 상태에서 idleTimer와 같다', () => {
    const f = startFocus('a', T0)
    const states: TimerState[] = [
      idleTimer(),
      f,
      pause(f, T0 + MIN),
      { phase: 'break', paused: false, taskId: 'a', endsAt: T0, remainingMs: null },
    ]
    for (const s of states) expect(cancel(s)).toEqual(idleTimer())
  })
})

describe('remainingMs', () => {
  it('idle은 0', () => {
    expect(remainingMs(idleTimer(), T0)).toBe(0)
  })
  it('종료 후에도 음수가 되지 않는다', () => {
    expect(remainingMs(startFocus('a', T0), T0 + 99 * MIN)).toBe(0)
  })
})

describe('불변성', () => {
  it('입력 state를 변경하지 않는다', () => {
    const f = startFocus('a', T0)
    const p = pause(f, T0 + MIN)
    const fSnap = structuredClone(f)
    const pSnap = structuredClone(p)
    pause(f, T0 + 2 * MIN)
    resume(p, T0 + 3 * MIN)
    cancel(f)
    cancel(p)
    remainingMs(f, T0)
    expect(f).toEqual(fSnap)
    expect(p).toEqual(pSnap)
  })
})

describe('advance', () => {
  it('24:59 경과 시 변화 없음', () => {
    const s = startFocus('a', T0)
    const r = advance(s, T0 + 25 * MIN - 1000)
    expect(r.state).toEqual(s)
    expect(r.completed).toEqual([])
    expect(r.events).toEqual([])
  })

  it('25:00 경과 시 break로 전환, 1건 집계', () => {
    const r = advance(startFocus('a', T0), T0 + 25 * MIN)
    expect(r.state.phase).toBe('break')
    expect(r.state.taskId).toBe('a')
    expect(r.state.endsAt).toBe(T0 + 30 * MIN)
    expect(r.completed).toEqual([{ taskId: 'a', completedAt: T0 + 25 * MIN }])
    expect(r.events).toEqual(['focusCompleted'])
  })

  it('break 5분 경과 시 idle, 집계 없음', () => {
    const b = advance(startFocus('a', T0), T0 + 25 * MIN).state
    const r = advance(b, T0 + 30 * MIN)
    expect(r.state).toEqual(idleTimer())
    expect(r.events).toEqual(['breakCompleted'])
    expect(r.completed).toEqual([])
  })

  it('31분 경과를 한 번에 처리', () => {
    const r = advance(startFocus('a', T0), T0 + 31 * MIN)
    expect(r.state).toEqual(idleTimer())
    expect(r.completed).toEqual([{ taskId: 'a', completedAt: T0 + 25 * MIN }])
    expect(r.events).toEqual(['focusCompleted', 'breakCompleted'])
  })

  it('27분 경과 시 break, 남은 3분', () => {
    const r = advance(startFocus('a', T0), T0 + 27 * MIN)
    expect(r.state.phase).toBe('break')
    expect(remainingMs(r.state, T0 + 27 * MIN)).toBe(3 * MIN)
  })

  it('일시정지/idle은 시간이 흘러도 불변', () => {
    const p = pause(startFocus('a', T0), T0 + MIN)
    const r = advance(p, T0 + 60 * MIN)
    expect(r).toEqual({ state: p, completed: [], events: [] })
    const i = advance(idleTimer(), T0 + 60 * MIN)
    expect(i).toEqual({ state: idleTimer(), completed: [], events: [] })
  })

  it('입력 state를 변경하지 않는다', () => {
    const s = startFocus('a', T0)
    const snap = structuredClone(s)
    advance(s, T0 + 40 * MIN)
    expect(s).toEqual(snap)
  })
})

describe('formatMmSs', () => {
  it('예시', () => {
    expect(formatMmSs(1_500_000)).toBe('25:00')
    expect(formatMmSs(1)).toBe('00:01')
    expect(formatMmSs(0)).toBe('00:00')
  })
  it('초 단위 올림', () => {
    expect(formatMmSs(59_001)).toBe('01:00')
    expect(formatMmSs(61_000)).toBe('01:01')
  })
})
