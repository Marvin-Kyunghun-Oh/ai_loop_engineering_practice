import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import TimerPanel from '../../src/components/TimerPanel.vue'
import { useTasksStore } from '../../src/stores/tasks'
import { useTimerStore } from '../../src/stores/timer'

const HINT = '할 일을 클릭해 집중을 시작하세요'

describe('TimerPanel', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-01-01T00:00:00Z'))
    setActivePinia(createPinia())
  })
  afterEach(() => {
    vi.useRealTimers()
  })

  it('idle이면 안내 문구만 보이고 버튼은 없다', () => {
    const wrapper = mount(TimerPanel)
    expect(wrapper.text()).toContain(HINT)
    expect(wrapper.findAll('button')).toHaveLength(0)
  })

  it('집중 시작 후 제목·단계·남은 시간을 표시하고 시간이 흐른다', async () => {
    const task = useTasksStore().add('보고서 쓰기')!
    useTimerStore().clickTask(task.id)
    const wrapper = mount(TimerPanel)
    expect(wrapper.text()).toContain('보고서 쓰기')
    expect(wrapper.text()).toContain('집중 중')
    expect(wrapper.text()).toContain('25:00')

    vi.advanceTimersByTime(61_000)
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('23:59')
  })

  it('일시정지·재개·취소 버튼이 동작한다', async () => {
    const task = useTasksStore().add('할 일')!
    useTimerStore().clickTask(task.id)
    const wrapper = mount(TimerPanel)

    await wrapper.findAll('button').find((b) => b.text() === '일시정지')!.trigger('click')
    expect(wrapper.text()).toContain('일시정지')
    const resumeBtn = wrapper.findAll('button').find((b) => b.text() === '재개')
    expect(resumeBtn).toBeTruthy()

    await resumeBtn!.trigger('click')
    expect(wrapper.text()).toContain('집중 중')

    await wrapper.findAll('button').find((b) => b.text() === '취소')!.trigger('click')
    expect(wrapper.text()).toContain(HINT)
  })
})
