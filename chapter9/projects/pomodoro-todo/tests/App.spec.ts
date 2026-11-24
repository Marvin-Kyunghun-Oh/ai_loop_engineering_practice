import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import App from '../src/App.vue'
import { playBeep } from '../src/audio/beep'

vi.mock('../src/audio/beep', () => ({ playBeep: vi.fn() }))

function mountApp() {
  const pinia = createPinia()
  setActivePinia(pinia)
  return mount(App, { global: { plugins: [pinia] } })
}

describe('App', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-01-01T00:00:00Z'))
    localStorage.clear()
  })
  afterEach(() => {
    vi.useRealTimers()
  })

  it('제목, 안내 문구, 할 일 입력창을 렌더링한다', () => {
    const wrapper = mountApp()
    expect(wrapper.text()).toContain('뽀모도로 할 일')
    expect(wrapper.text()).toContain('할 일을 클릭해 집중을 시작하세요')
    expect(wrapper.find('input[aria-label="할 일 입력"]').exists()).toBe(true)
    wrapper.unmount()
  })

  it('집중 25분이 지나면 🍅 1이 표시되고 패널은 휴식 중이 된다', async () => {
    const wrapper = mountApp()
    const input = wrapper.find('input[aria-label="할 일 입력"]')
    await input.setValue('보고서')
    await wrapper.find('form').trigger('submit')

    await wrapper.find('.task-row .title').trigger('click')
    vi.advanceTimersByTime(25 * 60 * 1000 + 1000)
    await wrapper.vm.$nextTick()

    expect(wrapper.find('.task-row').text()).toContain('🍅 1')
    expect(wrapper.text()).toContain('휴식 중')
    wrapper.unmount()
  })

  it('집중·휴식이 끝날 때마다 알림음을 한 번씩 낸다', async () => {
    vi.mocked(playBeep).mockClear()
    const wrapper = mountApp()
    await wrapper.find('input[aria-label="할 일 입력"]').setValue('보고서')
    await wrapper.find('form').trigger('submit')
    await wrapper.find('.task-row .title').trigger('click')

    vi.advanceTimersByTime(25 * 60 * 1000 + 1000)
    expect(playBeep).toHaveBeenCalledTimes(1)
    vi.advanceTimersByTime(5 * 60 * 1000)
    expect(playBeep).toHaveBeenCalledTimes(2)
    wrapper.unmount()
  })

  it('복원 시 놓친 알림음은 재생하지 않는다', () => {
    vi.mocked(playBeep).mockClear()
    const now = Date.now()
    const doc = {
      version: 1,
      tasks: [
        { id: 't1', title: '보고서', done: false, order: 0, pomodoroCount: 0, createdAt: now - 3_600_000 },
      ],
      records: [],
      timer: {
        phase: 'focus',
        paused: false,
        taskId: 't1',
        endsAt: now - 26 * 60 * 1000 + 25 * 60 * 1000,
        remainingMs: null,
      },
    }
    localStorage.setItem('pomodoro-todo', JSON.stringify(doc))
    const wrapper = mountApp()
    expect(playBeep).toHaveBeenCalledTimes(0)
    expect(wrapper.text()).toContain('휴식 중')
    wrapper.unmount()
  })

  describe('저장 경고 배너', () => {
    const SAVE_FAILED = '저장에 실패했습니다'
    const UNAVAILABLE = '브라우저 저장소를 사용할 수 없어'
    const RESET = '저장된 데이터를 읽지 못해 초기화했습니다'

    afterEach(() => {
      vi.restoreAllMocks()
    })

    async function addTask(wrapper: ReturnType<typeof mountApp>, title: string) {
      await wrapper.find('input[aria-label="할 일 입력"]').setValue(title)
      await wrapper.find('form').trigger('submit')
    }

    it('정상 마운트 시 배너가 없다', () => {
      const wrapper = mountApp()
      expect(wrapper.find('[role="alert"]').exists()).toBe(false)
      wrapper.unmount()
    })

    it('저장 실패 시 문구가 나타나고 저장이 성공하면 사라진다', async () => {
      const wrapper = mountApp()
      const original = Storage.prototype.setItem
      const spy = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(function (
        this: Storage,
        key: string,
        value: string,
      ) {
        if (key === 'pomodoro-todo') throw new Error('quota')
        original.call(this, key, value)
      })
      await addTask(wrapper, 'A')
      expect(wrapper.text()).toContain(SAVE_FAILED)

      spy.mockRestore()
      await addTask(wrapper, 'B')
      expect(wrapper.text()).not.toContain(SAVE_FAILED)
      wrapper.unmount()
    })

    it('저장소 사용 불가 시 해당 문구만 표시한다', async () => {
      vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
        throw new Error('denied')
      })
      const wrapper = mountApp()
      await addTask(wrapper, 'A')
      expect(wrapper.text()).toContain(UNAVAILABLE)
      expect(wrapper.text()).not.toContain(SAVE_FAILED)
      wrapper.unmount()
    })

    it('손상된 저장 문서면 초기화 안내를 표시한다', () => {
      localStorage.setItem('pomodoro-todo', '{not json')
      const wrapper = mountApp()
      expect(wrapper.text()).toContain(RESET)
      wrapper.unmount()
    })
  })
})
