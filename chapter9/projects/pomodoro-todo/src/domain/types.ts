export interface Task {
  id: string
  title: string
  done: boolean
  order: number
  pomodoroCount: number
  createdAt: number
}

export interface PomodoroRecord {
  taskId: string
  completedAt: number
}

export interface TimerState {
  phase: 'idle' | 'focus' | 'break'
  paused: boolean
  taskId: string | null
  endsAt: number | null
  remainingMs: number | null
}

export const FOCUS_MS = 25 * 60 * 1000
export const BREAK_MS = 5 * 60 * 1000
