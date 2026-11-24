import { describe, expect, it } from 'vitest'
import { createFakeClock } from '../../src/domain/clock'
import { createRepository } from '../../src/storage/repository'
import { emptyDoc, STORAGE_KEY, type PersistedDoc } from '../../src/storage/schema'

function memStorage(opts: { failSet?: () => boolean } = {}) {
  const m = new Map<string, string>()
  const s = {
    getItem: (k: string) => (m.has(k) ? m.get(k)! : null),
    setItem: (k: string, v: string) => {
      if (opts.failSet?.()) throw new DOMException('full', 'QuotaExceededError')
      m.set(k, v)
    },
    removeItem: (k: string) => void m.delete(k),
  } as unknown as Storage
  return { s, m }
}

const doc: PersistedDoc = {
  ...emptyDoc(),
  tasks: [{ id: 'a', title: 'x', done: false, order: 0, pomodoroCount: 0, createdAt: 1 }],
  records: [{ taskId: 'a', completedAt: 5 }],
}

describe('repository', () => {
  it('save 후 load는 같은 doc', () => {
    const { s } = memStorage()
    const repo = createRepository(() => s, createFakeClock(1))
    expect(repo.available).toBe(true)
    expect(repo.save(doc)).toBe(true)
    expect(repo.load()).toEqual({ doc, notice: 'none' })
  })

  it('키가 없으면 emptyDoc', () => {
    const { s } = memStorage()
    const repo = createRepository(() => s, createFakeClock(1))
    expect(repo.load()).toEqual({ doc: emptyDoc(), notice: 'none' })
  })

  it('손상 문서는 백업하고 초기화', () => {
    const { s, m } = memStorage()
    s.setItem(STORAGE_KEY, 'not json')
    const repo = createRepository(() => s, createFakeClock(777))
    expect(repo.load()).toEqual({ doc: emptyDoc(), notice: 'resetCorrupt' })
    expect(m.get('pomodoro-todo-corrupt-777')).toBe('not json')
  })

  it('백업 저장이 실패해도 load는 던지지 않는다', () => {
    let fail = false
    const { s } = memStorage({ failSet: () => fail })
    s.setItem(STORAGE_KEY, '{')
    const repo = createRepository(() => s, createFakeClock(1))
    fail = true
    expect(repo.load().notice).toBe('resetCorrupt')
  })

  it('QuotaExceeded면 save false, 이후 성공하면 true', () => {
    let fail = false
    const { s } = memStorage({ failSet: () => fail })
    const repo = createRepository(() => s, createFakeClock(1))
    fail = true
    expect(repo.save(doc)).toBe(false)
    fail = false
    expect(repo.save(doc)).toBe(true)
  })

  it('getStorage가 던지면 사용 불가', () => {
    const repo = createRepository(() => {
      throw new Error('denied')
    }, createFakeClock(1))
    expect(repo.available).toBe(false)
    expect(repo.load()).toEqual({ doc: emptyDoc(), notice: 'none' })
    expect(repo.save(doc)).toBe(false)
  })

  it('setItem이 항상 던지면 사용 불가', () => {
    const { s } = memStorage({ failSet: () => true })
    const repo = createRepository(() => s, createFakeClock(1))
    expect(repo.available).toBe(false)
    expect(repo.load()).toEqual({ doc: emptyDoc(), notice: 'none' })
    expect(repo.save(doc)).toBe(false)
  })
})
