import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { systemClock, type Clock } from '../domain/clock'
import { createId } from '../domain/id'
import type { Task } from '../domain/types'

export interface TasksDeps {
  clock: Clock
  createId: () => string
}

export function createTasksStore(storeId = 'tasks', deps: Partial<TasksDeps> = {}) {
  const clock = deps.clock ?? systemClock
  const genId = deps.createId ?? createId

  return defineStore(storeId, () => {
    const tasks = ref<Task[]>([])

    const orderedTasks = computed(() => [...tasks.value].sort((a, b) => a.order - b.order))

    function find(id: string): Task | undefined {
      return tasks.value.find((t) => t.id === id)
    }

    function add(title: string): Task | null {
      const trimmed = title.trim()
      if (trimmed === '') return null
      const maxOrder = tasks.value.reduce((m, t) => Math.max(m, t.order), -1)
      const task: Task = {
        id: genId(),
        title: trimmed,
        done: false,
        order: maxOrder + 1,
        pomodoroCount: 0,
        createdAt: clock.now(),
      }
      tasks.value.push(task)
      return task
    }

    function rename(id: string, title: string): boolean {
      const task = find(id)
      const trimmed = title.trim()
      if (!task || trimmed === '') return false
      task.title = trimmed
      return true
    }

    function remove(id: string): void {
      tasks.value = tasks.value.filter((t) => t.id !== id)
    }

    function toggleDone(id: string): void {
      const task = find(id)
      if (task) task.done = !task.done
    }

    function reorder(fromIndex: number, toIndex: number): void {
      const list = orderedTasks.value
      const n = list.length
      if (!Number.isInteger(fromIndex) || !Number.isInteger(toIndex)) return
      if (fromIndex < 0 || fromIndex >= n || toIndex < 0 || toIndex >= n) return
      const [moved] = list.splice(fromIndex, 1)
      list.splice(toIndex, 0, moved)
      list.forEach((t, i) => {
        t.order = i
      })
    }

    function incrementPomodoro(id: string): void {
      const task = find(id)
      if (task) task.pomodoroCount += 1
    }

    function hydrate(list: Task[]): void {
      tasks.value = list
    }

    return {
      tasks,
      orderedTasks,
      add,
      rename,
      remove,
      toggleDone,
      reorder,
      incrementPomodoro,
      hydrate,
    }
  })
}

export const useTasksStore = createTasksStore()
