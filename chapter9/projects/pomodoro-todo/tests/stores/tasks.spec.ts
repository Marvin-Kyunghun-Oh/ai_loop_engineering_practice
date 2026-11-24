import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { createTasksStore } from '../../src/stores/tasks'
import { createFakeClock } from '../../src/domain/clock'

let n = 0
function setup() {
  setActivePinia(createPinia())
  const clock = createFakeClock(1000)
  n = 0
  const store = createTasksStore('tasks', { clock, createId: () => `id${++n}` })()
  return { store, clock }
}
const titles = (s: ReturnType<typeof setup>['store']) => s.orderedTasks.map((t) => t.title)

describe('tasks store', () => {
  let ctx: ReturnType<typeof setup>
  beforeEach(() => {
    ctx = setup()
  })

  it('add: 공백 제거, 빈 제목 거부, 맨 아래 추가', () => {
    const { store, clock } = ctx
    const t = store.add('  보고서  ')
    expect(t?.title).toBe('보고서')
    expect(t).toMatchObject({ done: false, pomodoroCount: 0, createdAt: clock.now() })
    expect(store.add('   ')).toBeNull()
    expect(store.tasks).toHaveLength(1)
    store.add('B')
    store.add('C')
    expect(titles(store)).toEqual(['보고서', 'B', 'C'])
  })

  it('rename: 정상 변경, 빈 제목 거부, 없는 id', () => {
    const { store } = ctx
    const t = store.add('A')!
    expect(store.rename(t.id, ' X ')).toBe(true)
    expect(store.tasks[0].title).toBe('X')
    expect(store.rename(t.id, '  ')).toBe(false)
    expect(store.tasks[0].title).toBe('X')
    expect(store.rename('none', 'Y')).toBe(false)
  })

  it('remove: 대상만 제거, 나머지 순서 유지', () => {
    const { store } = ctx
    store.add('A')
    const b = store.add('B')!
    store.add('C')
    store.remove(b.id)
    expect(titles(store)).toEqual(['A', 'C'])
  })

  it('toggleDone: 위치 불변', () => {
    const { store } = ctx
    store.add('A')
    const b = store.add('B')!
    store.add('C')
    store.toggleDone(b.id)
    expect(store.tasks.find((t) => t.id === b.id)?.done).toBe(true)
    expect(titles(store)).toEqual(['A', 'B', 'C'])
    store.toggleDone(b.id)
    expect(store.tasks.find((t) => t.id === b.id)?.done).toBe(false)
  })

  it('reorder: 이동, 복귀, 범위 밖 무시, order 재할당', () => {
    const { store } = ctx
    store.add('A')
    store.add('B')
    store.add('C')
    store.reorder(0, 2)
    expect(titles(store)).toEqual(['B', 'C', 'A'])
    expect(store.orderedTasks.map((t) => t.order)).toEqual([0, 1, 2])
    store.reorder(2, 0)
    expect(titles(store)).toEqual(['A', 'B', 'C'])
    store.reorder(-1, 1)
    store.reorder(0, 3)
    store.reorder(5, 0)
    expect(titles(store)).toEqual(['A', 'B', 'C'])
  })

  it('incrementPomodoro: 대상만 증가', () => {
    const { store } = ctx
    const a = store.add('A')!
    store.add('B')
    store.incrementPomodoro(a.id)
    expect(store.orderedTasks.map((t) => t.pomodoroCount)).toEqual([1, 0])
  })
})
