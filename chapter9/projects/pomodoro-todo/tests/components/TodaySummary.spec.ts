import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import TodaySummary from '../../src/components/TodaySummary.vue'
import { useTimerStore } from '../../src/stores/timer'

describe('TodaySummary', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date(2026, 5, 10, 12, 0, 0))
    setActivePinia(createPinia())
  })
  afterEach(() => {
    vi.useRealTimers()
  })

  it('오늘 기록만 센다', () => {
    useTimerStore().records = [
      { taskId: 'a', completedAt: new Date(2026, 5, 10, 9, 0).getTime() },
      { taskId: 'a', completedAt: new Date(2026, 5, 10, 10, 0).getTime() },
      { taskId: 'a', completedAt: new Date(2026, 5, 9, 23, 0).getTime() },
    ]
    const wrapper = mount(TodaySummary)
    expect(wrapper.text()).toContain('🍅 2')
  })

  it('자정을 넘기면 0으로 바뀐다', async () => {
    useTimerStore().records = [
      { taskId: 'a', completedAt: new Date(2026, 5, 10, 9, 0).getTime() },
    ]
    const wrapper = mount(TodaySummary)
    expect(wrapper.text()).toContain('🍅 1')
    vi.setSystemTime(new Date(2026, 5, 11, 0, 0, 0))
    vi.advanceTimersByTime(1000)
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('🍅 0')
  })
})
