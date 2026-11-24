import { describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { createFakeClock } from '../../src/domain/clock'
import { FOCUS_MS } from '../../src/domain/types'
import { createRepository } from '../../src/storage/repository'
import { SCHEMA_VERSION, STORAGE_KEY, emptyDoc, serializeDoc } from '../../src/storage/schema'
import { createPersistenceStore } from '../../src/stores/persistence'
import { createTasksStore } from '../../src/stores/tasks'
import { createTimerStore } from '../../src/stores/timer'

class MemStorage implements Storage {
  data = new Map<string, string>()
  failSet = false
  get length() {
    return this.data.size
  }
  clear() {
    this.data.clear()
  }
  getItem(k: string) {
    return this.data.get(k) ?? null
  }
  key(i: number) {
    return [...this.data.keys()][i] ?? null
  }
  removeItem(k: string) {
    this.data.delete(k)
  }
  setItem(k: string, v: string) {
    if (this.failSet) throw new Error('QuotaExceeded')
    this.data.set(k, v)
  }
}

function setup(storage: MemStorage, getStorage?: () => Storage, startAt = 1000) {
  setActivePinia(createPinia())
  const clock = createFakeClock(startAt)
  let n = 0
  const tasks = createTasksStore('tasks', { clock, createId: () => `id${++n}` })()
  const timer = createTimerStore('timer', { clock, tasks: () => tasks })()
  const repository = createRepository(getStorage ?? (() => storage), clock)
  const persistence = createPersistenceStore('persistence', {
    repository,
    clock,
    tasks: () => tasks,
    timer: () => timer,
  })()
  return { tasks, timer, persistence, clock }
}

describe('persistence store', () => {
  it('할 일 추가 직후 저장된다', () => {
    const storage = new MemStorage()
    const { tasks, persistence } = setup(storage)
    persistence.init()
    tasks.add('A')
    const doc = JSON.parse(storage.getItem(STORAGE_KEY)!)
    expect(doc.tasks.map((t: { title: string }) => t.title)).toEqual(['A'])
  })

  it('집중 중 저장 문서를 T+2분에 init하면 break, 기록 1건, count +1', () => {
    const storage = new MemStorage()
    const T = 1_000_000 + FOCUS_MS
    storage.setItem(
      STORAGE_KEY,
      serializeDoc({
        version: SCHEMA_VERSION,
        tasks: [{ id: 'a', title: 'A', done: false, order: 0, pomodoroCount: 0, createdAt: 0 }],
        records: [],
        timer: { phase: 'focus', paused: false, taskId: 'a', endsAt: T, remainingMs: null },
      }),
    )
    const { tasks, timer, persistence } = setup(storage, undefined, T + 2 * 60_000)
    persistence.init()
    expect(timer.timer.phase).toBe('break')
    expect(timer.records).toHaveLength(1)
    expect(tasks.tasks[0].pomodoroCount).toBe(1)
  })

  it('대상 할 일이 없는 타이머는 idle', () => {
    const storage = new MemStorage()
    storage.setItem(
      STORAGE_KEY,
      serializeDoc({
        version: SCHEMA_VERSION,
        tasks: [],
        records: [],
        timer: { phase: 'focus', paused: false, taskId: 'gone', endsAt: 5000, remainingMs: null },
      }),
    )
    const { timer, persistence } = setup(storage)
    persistence.init()
    expect(timer.timer.phase).toBe('idle')
  })

  it('저장 실패 시 saveFailed true, 이후 성공하면 false', () => {
    const storage = new MemStorage()
    const { tasks, persistence } = setup(storage)
    persistence.init()
    storage.failSet = true
    tasks.add('A')
    expect(persistence.saveFailed).toBe(true)
    storage.failSet = false
    tasks.add('B')
    expect(persistence.saveFailed).toBe(false)
  })

  it('손상 문서는 resetNotice, 사용 불가 저장소는 storageUnavailable', () => {
    const bad = new MemStorage()
    bad.setItem(STORAGE_KEY, '{broken')
    const a = setup(bad)
    a.persistence.init()
    expect(a.persistence.resetNotice).toBe(true)

    const b = setup(
      new MemStorage(),
      () => {
        throw new Error('denied')
      },
    )
    b.persistence.init()
    expect(b.persistence.storageUnavailable).toBe(true)
  })

  it('사용 불가 저장소는 변경해도 save를 호출하지 않고 메모리 상태를 유지한다', () => {
    setActivePinia(createPinia())
    const clock = createFakeClock(1000)
    let n = 0
    const tasks = createTasksStore('tasks', { clock, createId: () => `id${++n}` })()
    const timer = createTimerStore('timer', { clock, tasks: () => tasks })()
    const save = vi.fn(() => false)
    const repository = {
      available: false,
      load: () => ({ doc: emptyDoc(), notice: 'none' as const }),
      save,
    }
    const persistence = createPersistenceStore('persistence', {
      repository,
      clock,
      tasks: () => tasks,
      timer: () => timer,
    })()
    persistence.init()
    tasks.add('A')
    timer.clickTask(tasks.tasks[0].id)
    expect(save).not.toHaveBeenCalled()
    expect(persistence.saveFailed).toBe(false)
    expect(persistence.storageUnavailable).toBe(true)
    expect(tasks.tasks).toHaveLength(1)
    expect(timer.timer.phase).toBe('focus')
  })
})
