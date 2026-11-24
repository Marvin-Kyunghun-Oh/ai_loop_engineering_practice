import { BREAK_MS, FOCUS_MS, type PomodoroRecord, type TimerState } from './types'

export function idleTimer(): TimerState {
  return { phase: 'idle', paused: false, taskId: null, endsAt: null, remainingMs: null }
}

export function startFocus(taskId: string, now: number): TimerState {
  return { phase: 'focus', paused: false, taskId, endsAt: now + FOCUS_MS, remainingMs: null }
}

export function remainingMs(state: TimerState, now: number): number {
  if (state.phase === 'idle') return 0
  if (state.paused) return state.remainingMs ?? 0
  return Math.max(0, (state.endsAt ?? now) - now)
}

export function pause(state: TimerState, now: number): TimerState {
  if (state.phase === 'idle' || state.paused) return state
  return { ...state, paused: true, remainingMs: remainingMs(state, now), endsAt: null }
}

export function resume(state: TimerState, now: number): TimerState {
  if (state.phase === 'idle' || !state.paused) return state
  return { ...state, paused: false, endsAt: now + (state.remainingMs ?? 0), remainingMs: null }
}

export function cancel(_state: TimerState): TimerState {
  return idleTimer()
}

export type TimerEvent = 'focusCompleted' | 'breakCompleted'

export interface AdvanceResult {
  state: TimerState
  completed: PomodoroRecord[]
  events: TimerEvent[]
}

export function advance(state: TimerState, now: number): AdvanceResult {
  const completed: PomodoroRecord[] = []
  const events: TimerEvent[] = []
  let current = state

  if (current.phase === 'focus' && !current.paused && current.endsAt !== null && now >= current.endsAt) {
    completed.push({ taskId: current.taskId as string, completedAt: current.endsAt })
    events.push('focusCompleted')
    current = {
      phase: 'break',
      paused: false,
      taskId: current.taskId,
      endsAt: current.endsAt + BREAK_MS,
      remainingMs: null,
    }
  }

  if (current.phase === 'break' && !current.paused && current.endsAt !== null && now >= current.endsAt) {
    events.push('breakCompleted')
    current = idleTimer()
  }

  return { state: current, completed, events }
}

export type ClickResult =
  | { kind: 'started'; state: TimerState }
  | { kind: 'noop' }
  | { kind: 'confirmNeeded' }

export function clickTask(state: TimerState, taskId: string, now: number): ClickResult {
  if (state.phase === 'idle' || state.phase === 'break') {
    return { kind: 'started', state: startFocus(taskId, now) }
  }
  return state.taskId === taskId ? { kind: 'noop' } : { kind: 'confirmNeeded' }
}

export function confirmSwitch(taskId: string, now: number): TimerState {
  return startFocus(taskId, now)
}

export function restore(
  saved: TimerState,
  now: number,
  taskExists: (id: string) => boolean,
): { state: TimerState; completed: PomodoroRecord[] } {
  if (saved.phase === 'idle' || saved.taskId === null || !taskExists(saved.taskId)) {
    return { state: idleTimer(), completed: [] }
  }
  const { state, completed } = advance(saved, now)
  return { state, completed }
}

export function formatMmSs(ms: number): string {
  const totalSec = Math.ceil(Math.max(0, ms) / 1000)
  const mm = Math.floor(totalSec / 60)
  const ss = totalSec % 60
  return `${String(mm).padStart(2, '0')}:${String(ss).padStart(2, '0')}`
}
