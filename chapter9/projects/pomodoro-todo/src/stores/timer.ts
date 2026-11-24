import { defineStore } from 'pinia'
import { ref } from 'vue'
import { systemClock, type Clock } from '../domain/clock'
import {
  advance,
  cancel as cancelTimer,
  clickTask as clickTaskDomain,
  confirmSwitch as confirmSwitchDomain,
  idleTimer,
  pause as pauseTimer,
  resume as resumeTimer,
  type TimerEvent,
} from '../domain/timer'
import type { PomodoroRecord, TimerState } from '../domain/types'
import { useTasksStore } from './tasks'

export interface TimerDeps {
  clock: Clock
  /** 할 일 스토어(필요한 부분만). 기본값은 전역 할 일 스토어. */
  tasks: () => { incrementPomodoro(id: string): void }
}

export function createTimerStore(storeId = 'timer', deps: Partial<TimerDeps> = {}) {
  const clock = deps.clock ?? systemClock
  const getTasks = deps.tasks ?? (() => useTasksStore())

  return defineStore(storeId, () => {
    const timer = ref<TimerState>(idleTimer())
    const records = ref<PomodoroRecord[]>([])

    function clickTask(taskId: string): 'started' | 'noop' | 'confirmNeeded' {
      const result = clickTaskDomain(timer.value, taskId, clock.now())
      if (result.kind === 'started') timer.value = result.state
      return result.kind
    }

    function confirmSwitch(taskId: string): void {
      timer.value = confirmSwitchDomain(taskId, clock.now())
    }

    function pause(): void {
      timer.value = pauseTimer(timer.value, clock.now())
    }

    function resume(): void {
      timer.value = resumeTimer(timer.value, clock.now())
    }

    function cancel(): void {
      timer.value = cancelTimer(timer.value)
    }

    function tick(): TimerEvent[] {
      const { state, completed, events } = advance(timer.value, clock.now())
      timer.value = state
      for (const rec of completed) {
        records.value.push(rec)
        getTasks().incrementPomodoro(rec.taskId)
      }
      return events
    }

    function onTaskRemoved(id: string): void {
      if (timer.value.taskId === id) cancel()
    }

    function hydrate(state: TimerState, list: PomodoroRecord[]): void {
      timer.value = state
      records.value = list
    }

    return {
      timer,
      records,
      clickTask,
      confirmSwitch,
      pause,
      resume,
      cancel,
      tick,
      onTaskRemoved,
      hydrate,
    }
  })
}

export const useTimerStore = createTimerStore()
