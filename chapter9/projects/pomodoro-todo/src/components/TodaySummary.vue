<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import { countToday } from '../domain/stats'
import { useTimerStore } from '../stores/timer'

const timerStore = useTimerStore()
const now = ref(Date.now())
const handle = setInterval(() => {
  now.value = Date.now()
}, 1000)
onBeforeUnmount(() => clearInterval(handle))

const count = computed(() => countToday(timerStore.records, now.value))
</script>

<template>
  <p class="today-summary">오늘 집중: 🍅 {{ count }}</p>
</template>

<style scoped>
.today-summary {
  margin: 24px 0 0;
  font-weight: 600;
  color: #7a3b2e;
}
</style>
