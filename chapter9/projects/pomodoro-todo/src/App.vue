<script setup lang="ts">
import { onBeforeUnmount } from 'vue'
import { playBeep } from './audio/beep'
import TaskInput from './components/TaskInput.vue'
import TaskList from './components/TaskList.vue'
import TimerPanel from './components/TimerPanel.vue'
import TodaySummary from './components/TodaySummary.vue'
import { systemClock } from './domain/clock'
import { createRepository } from './storage/repository'
import { createPersistenceStore } from './stores/persistence'
import { useTasksStore } from './stores/tasks'
import { useTimerStore } from './stores/timer'

// 영속화: 시작 시 로드·복원, 이후 변경 시 즉시 저장
const usePersistenceStore = createPersistenceStore('persistence', {
  repository: createRepository(() => localStorage, systemClock),
  clock: systemClock,
  tasks: () => useTasksStore(),
  timer: () => useTimerStore(),
})
const persistence = usePersistenceStore()
persistence.init()

// 시간 경과 처리: 1초 간격 tick. 이벤트가 있으면 알림음 1회.
// 마운트 직후의 tick 이벤트는 복원 시 놓친 알림이므로 재생하지 않는다.
const timerStore = useTimerStore()
timerStore.tick()
const tickHandle = setInterval(() => {
  if (timerStore.tick().length > 0) playBeep()
}, 1000)
onBeforeUnmount(() => clearInterval(tickHandle))
</script>

<template>
  <main class="app">
    <h1>뽀모도로 할 일</h1>
    <div v-if="persistence.saveFailed" class="banner" role="alert">
      저장에 실패했습니다. 새로고침하면 변경 사항이 사라질 수 있습니다
    </div>
    <div v-if="persistence.storageUnavailable" class="banner" role="alert">
      브라우저 저장소를 사용할 수 없어 변경 사항이 저장되지 않습니다
    </div>
    <div v-if="persistence.resetNotice" class="banner" role="alert">
      저장된 데이터를 읽지 못해 초기화했습니다
    </div>
    <TimerPanel />
    <TaskInput />
    <TaskList />
    <TodaySummary />
  </main>
</template>

<style>
body {
  margin: 0;
  font-family: system-ui, -apple-system, 'Segoe UI', sans-serif;
  background: #faf6f2;
  color: #2b2b2b;
}
.app {
  max-width: 640px;
  margin: 0 auto;
  padding: 48px 24px;
}
.app .banner {
  margin: 16px 0 0;
  padding: 10px 14px;
  border-radius: 8px;
  background: #fdecea;
  color: #8e2a1f;
  border: 1px solid #f5c6c0;
  font-size: 0.9rem;
}
.app h1 {
  font-size: 1.75rem;
  font-weight: 700;
  color: #c0392b;
  margin: 0;
}
@media (max-width: 480px) {
  .app {
    padding: 24px 12px;
  }
}
</style>
