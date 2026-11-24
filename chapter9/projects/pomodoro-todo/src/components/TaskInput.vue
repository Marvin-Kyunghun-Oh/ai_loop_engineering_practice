<script setup lang="ts">
import { ref } from 'vue'
import { useTasksStore } from '../stores/tasks'

const tasksStore = useTasksStore()
const title = ref('')

function submit(): void {
  if (tasksStore.add(title.value)) title.value = ''
}
</script>

<template>
  <form class="task-input" @submit.prevent="submit">
    <input v-model="title" type="text" placeholder="할 일을 입력하세요" aria-label="할 일 입력" />
    <button type="submit">추가</button>
  </form>
</template>

<style scoped>
.task-input {
  display: flex;
  gap: 0.5rem;
  font-family: system-ui, sans-serif;
}
input {
  flex: 1;
  padding: 0.5rem 0.75rem;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 1rem;
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
</style>
