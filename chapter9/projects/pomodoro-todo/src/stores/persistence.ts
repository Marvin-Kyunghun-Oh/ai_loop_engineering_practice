import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import { systemClock, type Clock } from '../domain/clock'
import { restore } from '../domain/timer'
import type { PomodoroRecord, Task, TimerState } from '../domain/types'
import type { Repository } from '../storage/repository'
import { SCHEMA_VERSION } from '../storage/schema'

export interface PersistenceDeps {
  repository: Repository
  clock: Clock
  tasks: () => { tasks: Task[]; hydrate(list: Task[]): void }
  timer: () => {
    timer: TimerState
    records: PomodoroRecord[]
    hydrate(state: TimerState, list: PomodoroRecord[]): void
  }
}

export function createPersistenceStore(storeId: string, deps: PersistenceDeps) {
  const clock = deps.clock ?? systemClock

  return defineStore(storeId, () => {
    const saveFailed = ref(false)
    const storageUnavailable = ref(false)
    const resetNotice = ref(false)
    let started = false

    function saveNow(): void {
      // 저장소 사용 불가: 메모리로만 동작하고 경고는 storageUnavailable로만 알린다.
      if (!deps.repository.available) return
      const tasksStore = deps.tasks()
      const timerStore = deps.timer()
      const ok = deps.repository.save({
        version: SCHEMA_VERSION,
        tasks: tasksStore.tasks,
        records: timerStore.records,
        timer: timerStore.timer,
      })
      saveFailed.value = !ok
    }

    function init(): void {
      if (started) return
      started = true
      const tasksStore = deps.tasks()
      const timerStore = deps.timer()

      storageUnavailable.value = !deps.repository.available
      const { doc, notice } = deps.repository.load()
      resetNotice.value = notice === 'resetCorrupt'

      const taskList = doc.tasks
      const { state, completed } = restore(doc.timer, clock.now(), (id) =>
        taskList.some((t) => t.id === id),
      )
      const records = [...doc.records, ...completed]
      for (const rec of completed) {
        const task = taskList.find((t) => t.id === rec.taskId)
        if (task) task.pomodoroCount += 1
      }
      tasksStore.hydrate(taskList)
      timerStore.hydrate(state, records)

      if (deps.repository.available) saveNow()

      watch(() => [tasksStore.tasks, timerStore.records, timerStore.timer], saveNow, {
        deep: true,
        flush: 'sync',
      })
    }

    return { saveFailed, storageUnavailable, resetNotice, init }
  })
}
