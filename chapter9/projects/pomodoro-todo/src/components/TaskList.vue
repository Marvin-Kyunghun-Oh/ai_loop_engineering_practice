<script setup lang="ts">
import { ref } from 'vue'
import { useTasksStore } from '../stores/tasks'
import { useTimerStore } from '../stores/timer'

const tasksStore = useTasksStore()
const timerStore = useTimerStore()

function onTitleClick(id: string): void {
  const result = timerStore.clickTask(id)
  if (result === 'confirmNeeded' && window.confirm('현재 뽀모도로를 취소하고 새로 시작할까요?')) {
    timerStore.confirmSwitch(id)
  }
}

const editingId = ref<string | null>(null)
const draft = ref('')

function startEdit(id: string, title: string): void {
  editingId.value = id
  draft.value = title
}

function commitEdit(id: string): void {
  if (tasksStore.rename(id, draft.value)) editingId.value = null
}

function cancelEdit(): void {
  editingId.value = null
}

function onRemove(id: string): void {
  if (!window.confirm('이 할 일을 삭제할까요?')) return
  tasksStore.remove(id)
  timerStore.onTaskRemoved(id)
}

const dragFrom = ref<number | null>(null)

function onDragStart(index: number, e: DragEvent): void {
  dragFrom.value = index
  if (e.dataTransfer) {
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.setData('text/plain', String(index))
  }
}

function onDragEnd(): void {
  dragFrom.value = null
}

function onDrop(index: number): void {
  const from = dragFrom.value
  dragFrom.value = null
  if (from === null || from === index) return
  tasksStore.reorder(from, index)
}
</script>

<template>
  <ul class="task-list">
    <li
      v-for="(task, index) in tasksStore.orderedTasks"
      :key="task.id"
      class="task-row"
      :class="{ 'is-current': timerStore.timer.taskId === task.id }"
      draggable="true"
      @dragstart="onDragStart(index, $event)"
      @dragend="onDragEnd"
      @dragover.prevent
      @drop.prevent="onDrop(index)"
    >
      <span class="handle" aria-hidden="true">≡</span>
      <input
        type="checkbox"
        :checked="task.done"
        :aria-label="`${task.title} 완료`"
        @change="tasksStore.toggleDone(task.id)"
      />
      <input
        v-if="editingId === task.id"
        v-model="draft"
        class="edit-input"
        aria-label="제목 편집"
        @keydown.enter.prevent="commitEdit(task.id)"
        @keydown.esc.prevent="cancelEdit"
      />
      <span
        v-else
        class="title"
        :class="{ done: task.done }"
        tabindex="0"
        role="button"
        @click="onTitleClick(task.id)"
        @keydown.enter.prevent="onTitleClick(task.id)"
        @keydown.space.prevent="onTitleClick(task.id)"
        >{{ task.title }}</span
      >
      <span class="count">🍅 {{ task.pomodoroCount }}</span>
      <button type="button" class="edit-btn" aria-label="제목 편집" @click="startEdit(task.id, task.title)">✎</button>
      <button type="button" class="delete-btn" aria-label="삭제" @click="onRemove(task.id)">🗑</button>
    </li>
  </ul>
</template>

<style scoped>
.task-list {
  list-style: none;
  margin: 0;
  padding: 0;
  font-family: system-ui, sans-serif;
}
.task-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid #e5e7eb;
}
.task-row.is-current {
  background: #fff7f5;
  border-left: 3px solid #c2410c;
}
.handle {
  color: #9ca3af;
  cursor: grab;
}
.title {
  flex: 1;
  min-width: 0;
  overflow-wrap: anywhere;
  cursor: pointer;
}
.handle,
.edit-btn,
.delete-btn,
.count {
  flex-shrink: 0;
}
.title:focus-visible {
  outline: 2px solid #c2410c;
  outline-offset: 2px;
}
.title.done {
  text-decoration: line-through;
  color: #9ca3af;
}
.edit-input {
  flex: 1;
  padding: 0.25rem 0.5rem;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font: inherit;
}
.edit-btn,
.delete-btn {
  border: none;
  background: transparent;
  cursor: pointer;
  padding: 0.125rem 0.25rem;
}
.count {
  font-size: 0.875rem;
  color: #6b7280;
}
</style>
