import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import TaskInput from '../../src/components/TaskInput.vue'
import TaskList from '../../src/components/TaskList.vue'
import { useTasksStore } from '../../src/stores/tasks'
import { useTimerStore } from '../../src/stores/timer'

describe('TaskInput + TaskList', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('앞뒤 공백을 제거해 추가하고 입력창을 비운다', async () => {
    const input = mount(TaskInput)
    const list = mount(TaskList)
    const field = input.find('input')
    await field.setValue('  보고서  ')
    await field.trigger('keydown.enter')
    await input.find('form').trigger('submit')
    expect(list.findAll('.task-row')).toHaveLength(1)
    expect(list.find('.title').text()).toBe('보고서')
    expect((field.element as HTMLInputElement).value).toBe('')
  })

  it('Enter(폼 제출)로 추가된다', async () => {
    const input = mount(TaskInput)
    const list = mount(TaskList)
    await input.find('input').setValue('a')
    await input.find('form').trigger('submit')
    expect(list.findAll('.task-row')).toHaveLength(1)
  })

  it('공백만 입력하면 추가되지 않는다', async () => {
    const input = mount(TaskInput)
    const list = mount(TaskList)
    await input.find('input').setValue('   ')
    await input.find('form').trigger('submit')
    expect(list.findAll('.task-row')).toHaveLength(0)
  })

  it('체크박스는 done 클래스를 적용하고 순서를 유지한다', async () => {
    const tasks = useTasksStore()
    tasks.add('첫째')
    tasks.add('둘째')
    const list = mount(TaskList)
    await list.findAll('input[type="checkbox"]')[0].setValue(true)
    expect(list.findAll('.title')[0].classes()).toContain('done')
    expect(list.findAll('.title').map((t) => t.text())).toEqual(['첫째', '둘째'])
  })

  it('제목 클릭으로 집중을 시작하고 행이 강조된다', async () => {
    const task = useTasksStore().add('일')!
    const list = mount(TaskList)
    await list.find('.title').trigger('click')
    expect(useTimerStore().timer.phase).toBe('focus')
    expect(list.find('.task-row').classes()).toContain('is-current')
    expect(useTimerStore().timer.taskId).toBe(task.id)
  })

  it('집중 중 다른 행 클릭: confirm false면 유지, true면 전환', async () => {
    const tasks = useTasksStore()
    const a = tasks.add('A')!
    const b = tasks.add('B')!
    const list = mount(TaskList)
    await list.findAll('.title')[0].trigger('click')

    const spy = vi.spyOn(window, 'confirm').mockReturnValue(false)
    await list.findAll('.title')[1].trigger('click')
    expect(spy).toHaveBeenCalled()
    expect(useTimerStore().timer.taskId).toBe(a.id)

    spy.mockReturnValue(true)
    await list.findAll('.title')[1].trigger('click')
    expect(useTimerStore().timer.taskId).toBe(b.id)
  })

  it('✎ 편집: Enter로 변경, 빈 제목은 편집 유지, Esc는 취소', async () => {
    useTasksStore().add('원래')
    const list = mount(TaskList)
    await list.find('.edit-btn').trigger('click')
    let field = list.find('input.edit-input')
    await field.setValue('새 제목')
    await field.trigger('keydown', { key: 'Enter' })
    expect(list.find('.title').text()).toBe('새 제목')
    expect(list.find('input.edit-input').exists()).toBe(false)

    await list.find('.edit-btn').trigger('click')
    field = list.find('input.edit-input')
    await field.setValue('')
    await field.trigger('keydown', { key: 'Enter' })
    expect(useTasksStore().orderedTasks[0].title).toBe('새 제목')
    expect(list.find('input.edit-input').exists()).toBe(true)

    await field.setValue('버릴 값')
    await field.trigger('keydown', { key: 'Escape' })
    expect(list.find('input.edit-input').exists()).toBe(false)
    expect(list.find('.title').text()).toBe('새 제목')
  })

  it('🗑 삭제: confirm false면 유지, true면 제거', async () => {
    useTasksStore().add('x')
    const list = mount(TaskList)
    const spy = vi.spyOn(window, 'confirm').mockReturnValue(false)
    await list.find('.delete-btn').trigger('click')
    expect(list.findAll('.task-row')).toHaveLength(1)
    spy.mockReturnValue(true)
    await list.find('.delete-btn').trigger('click')
    expect(list.findAll('.task-row')).toHaveLength(0)
  })

  it('타이머 대상 할 일을 삭제하면 idle, records는 유지', async () => {
    useTasksStore().add('x')
    const list = mount(TaskList)
    await list.find('.title').trigger('click')
    expect(useTimerStore().timer.phase).toBe('focus')
    const before = useTimerStore().records.length
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    await list.find('.delete-btn').trigger('click')
    expect(useTimerStore().timer.phase).toBe('idle')
    expect(useTimerStore().records.length).toBe(before)
  })

  it('드래그 앤 드롭으로 순서를 바꾼다', async () => {
    const tasks = useTasksStore()
    tasks.add('A')
    tasks.add('B')
    tasks.add('C')
    const list = mount(TaskList)
    const rows = list.findAll('.task-row')
    await rows[0].trigger('dragstart')
    await rows[2].trigger('drop')
    expect(list.findAll('.title').map((t) => t.text())).toEqual(['B', 'C', 'A'])
    expect(tasks.orderedTasks.map((t) => t.order)).toEqual([0, 1, 2])
  })

  it('같은 행에 drop하면 순서가 변하지 않는다', async () => {
    const tasks = useTasksStore()
    tasks.add('A')
    tasks.add('B')
    const list = mount(TaskList)
    const rows = list.findAll('.task-row')
    await rows[0].trigger('dragstart')
    await rows[0].trigger('drop')
    expect(list.findAll('.title').map((t) => t.text())).toEqual(['A', 'B'])
  })

  it('dragend 후에는 dragstart 없는 drop이 순서를 바꾸지 않는다', async () => {
    const tasks = useTasksStore()
    tasks.add('A')
    tasks.add('B')
    tasks.add('C')
    const list = mount(TaskList)
    const rows = list.findAll('.task-row')
    await rows[0].trigger('dragstart')
    await rows[0].trigger('dragend')
    await rows[2].trigger('drop')
    expect(list.findAll('.title').map((t) => t.text())).toEqual(['A', 'B', 'C'])
  })

  it('pomodoroCount를 🍅 N으로 표시한다', () => {
    const tasks = useTasksStore()
    const t = tasks.add('x')!
    for (let i = 0; i < 3; i++) tasks.incrementPomodoro(t.id)
    const list = mount(TaskList)
    expect(list.text()).toContain('🍅 3')
  })
})
