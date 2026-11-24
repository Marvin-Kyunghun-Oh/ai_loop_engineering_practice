import type { PomodoroRecord, Task, TimerState } from '../domain/types'
import { idleTimer } from '../domain/timer'

export const STORAGE_KEY = 'pomodoro-todo'
export const SCHEMA_VERSION = 1

export interface PersistedDoc {
  version: 1
  tasks: Task[]
  records: PomodoroRecord[]
  timer: TimerState
}

export type ParseResult =
  | { ok: true; doc: PersistedDoc }
  | { ok: false; reason: 'parse' | 'schema' }

export function emptyDoc(): PersistedDoc {
  return { version: SCHEMA_VERSION, tasks: [], records: [], timer: idleTimer() }
}

export function serializeDoc(doc: PersistedDoc): string {
  return JSON.stringify(doc)
}

type Obj = Record<string, unknown>

function isObj(v: unknown): v is Obj {
  return typeof v === 'object' && v !== null && !Array.isArray(v)
}

const isNum = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v)
const isNumOrNull = (v: unknown): boolean => v === null || isNum(v)

function isTask(v: unknown): v is Task {
  return (
    isObj(v) &&
    typeof v.id === 'string' &&
    typeof v.title === 'string' &&
    typeof v.done === 'boolean' &&
    isNum(v.order) &&
    isNum(v.pomodoroCount) &&
    isNum(v.createdAt)
  )
}

function isRecord(v: unknown): v is PomodoroRecord {
  return isObj(v) && typeof v.taskId === 'string' && isNum(v.completedAt)
}

function isTimer(v: unknown): v is TimerState {
  return (
    isObj(v) &&
    (v.phase === 'idle' || v.phase === 'focus' || v.phase === 'break') &&
    typeof v.paused === 'boolean' &&
    (v.taskId === null || typeof v.taskId === 'string') &&
    isNumOrNull(v.endsAt) &&
    isNumOrNull(v.remainingMs)
  )
}

export function parseDoc(raw: string): ParseResult {
  let data: unknown
  try {
    data = JSON.parse(raw)
  } catch {
    return { ok: false, reason: 'parse' }
  }
  if (
    !isObj(data) ||
    data.version !== SCHEMA_VERSION ||
    !Array.isArray(data.tasks) ||
    !data.tasks.every(isTask) ||
    !Array.isArray(data.records) ||
    !data.records.every(isRecord) ||
    !isTimer(data.timer)
  ) {
    return { ok: false, reason: 'schema' }
  }
  return {
    ok: true,
    doc: { version: 1, tasks: data.tasks, records: data.records, timer: data.timer },
  }
}
