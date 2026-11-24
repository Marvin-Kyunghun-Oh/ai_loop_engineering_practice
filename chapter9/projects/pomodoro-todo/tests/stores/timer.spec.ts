import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { createTasksStore } from '../../src/stores/tasks'
import { createTimerStore } from '../../src/stores/timer'
import { createFakeClock } from '../../src/domain/clock'
import { FOCUS_MS } from '../../src/domain/types'

let n = 0
function setup() {
  setActivePinia(createPinia())
  const clock = createFakeClock(1000)
  n = 0
  const tasks = createTasksStore('tasks', { clock, createId: () => `id${++n}` })()
  const timer = createTimerStore('timer', { clock, tasks: () => tasks })()
  return { tasks, timer, clock }
}

describe('timer store', () => {
  let ctx: ReturnType<typeof setup>
  beforeEach(() => {
    ctx = setup()
  })

  it('25분 경과 후 tick: records, pomodoroCount, break, 이벤트', () => {
    const { tasks, timer, clock } = ctx
    const a = tasks.add('A')!
    expect(timer.clickTask(a.id)).toBe('started')
    clock.advance(FOCUS_MS)
    expect(timer.tick()).toEqual(['focusCompleted'])
    expect(timer.records).toHaveLength(1)
    expect(timer.records[0].taskId).toBe(a.id)
    expect(tasks.tasks[0].pomodoroCount).toBe(1)
    expect(timer.timer.phase).toBe('break')
  })

  it('집중 중 cancel은 미집계', () => {
    const { tasks, timer, clock } = ctx
    const a = tasks.add('A')!
    timer.clickTask(a.id)
    clock.advance(10 * 60_000)
    timer.cancel()
    clock.advance(FOCUS_MS)
    timer.tick()
    expect(timer.timer.phase).toBe('idle')
    expect(timer.records).toHaveLength(0)
    expect(tasks.tasks[0].pomodoroCount).toBe(0)
  })

  it('대상 할 일 삭제 시 onTaskRemoved: idle, 기존 records 유지', () => {
    const { tasks, timer, clock } = ctx
    const a = tasks.add('A')!
    const b = tasks.add('B')!
    timer.clickTask(a.id)
    clock.advance(FOCUS_MS)
    timer.tick()
    timer.clickTask(b.id) // break 중 클릭 → B 집중
    expect(timer.timer.taskId).toBe(b.id)
    tasks.remove(b.id)
    timer.onTaskRemoved(b.id)
    expect(timer.timer.phase).toBe('idle')
    expect(timer.records).toHaveLength(1)
  })

  it('다른 할 일 onTaskRemoved는 무시', () => {
    const { tasks, timer } = ctx
    const a = tasks.add('A')!
    timer.clickTask(a.id)
    timer.onTaskRemoved('other')
    expect(timer.timer.phase).toBe('focus')
  })

  it('다른 할 일 클릭: confirmNeeded, 상태 불변; confirmSwitch 후 새 대상', () => {
    const { tasks, timer } = ctx
    const a = tasks.add('A')!
    const b = tasks.add('B')!
    timer.clickTask(a.id)
    const before = { ...timer.timer }
    expect(timer.clickTask(b.id)).toBe('confirmNeeded')
    expect(timer.timer).toEqual(before)
    timer.confirmSwitch(b.id)
    expect(timer.timer.phase).toBe('focus')
    expect(timer.timer.taskId).toBe(b.id)
  })

  it('pause/resume은 남은 시간을 보존', () => {
    const { tasks, timer, clock } = ctx
    const a = tasks.add('A')!
    timer.clickTask(a.id)
    clock.advance(10 * 60_000)
    timer.pause()
    clock.advance(60 * 60_000)
    timer.resume()
    clock.advance(15 * 60_000)
    expect(timer.tick()).toEqual(['focusCompleted'])
  })
})
