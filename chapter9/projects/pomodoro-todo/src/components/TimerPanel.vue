<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import { formatMmSs, remainingMs } from '../domain/timer'
import { useTasksStore } from '../stores/tasks'
import { useTimerStore } from '../stores/timer'

const tasksStore = useTasksStore()
const timerStore = useTimerStore()

const now = ref(Date.now())
const handle = setInterval(() => {
  now.value = Date.now()
}, 1000)
onBeforeUnmount(() => clearInterval(handle))

const isIdle = computed(() => timerStore.timer.phase === 'idle')
const title = computed(
  () => tasksStore.tasks.find((t) => t.id === timerStore.timer.taskId)?.title ?? '',
)
const phaseLabel = computed(() => {
  if (timerStore.timer.paused) return '일시정지'
  return timerStore.timer.phase === 'break' ? '휴식 중' : '집중 중'
})
const timeText = computed(() => formatMmSs(remainingMs(timerStore.timer, now.value)))
</script>

<template>
  <section class="timer-panel" :class="{ idle: isIdle }">
    <p v-if="isIdle" class="hint">할 일을 클릭해 집중을 시작하세요</p>
    <template v-else>
      <p class="task-title">{{ title }}</p>
      <p class="phase" :class="timerStore.timer.phase">{{ phaseLabel }}</p>
      <p class="time">{{ timeText }}</p>
      <div class="actions">
        <button v-if="!timerStore.timer.paused" type="button" @click="timerStore.pause()">
          일시정지
        </button>
        <button v-else type="button" @click="timerStore.resume()">재개</button>
        <button type="button" class="cancel" @click="timerStore.cancel()">취소</button>
      </div>
    </template>
  </section>
</template>

<style scoped>
.timer-panel {
  padding: 1.5rem;
  border-radius: 12px;
  background: #fff7f5;
  border: 1px solid #f3d5cf;
  text-align: center;
  font-family: system-ui, sans-serif;
}
.timer-panel.idle {
  background: #f6f7f9;
  border-color: #e1e4e8;
}
.hint {
  margin: 0;
  color: #6b7280;
}
.task-title {
  margin: 0 0 0.25rem;
  font-size: 1.125rem;
  font-weight: 600;
}
.phase {
  margin: 0;
  color: #c2410c;
  font-size: 0.875rem;
}
.phase.break {
  color: #15803d;
}
.time {
  margin: 0.5rem 0 1rem;
  font-size: 3rem;
  font-variant-numeric: tabular-nums;
  font-weight: 700;
}
.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  justify-content: center;
}
button {
  padding: 0.5rem 1rem;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  background: #fff;
  cursor: pointer;
}
button:hover {
  background: #f3f4f6;
}
button.cancel {
  color: #b91c1c;
}
</style>
