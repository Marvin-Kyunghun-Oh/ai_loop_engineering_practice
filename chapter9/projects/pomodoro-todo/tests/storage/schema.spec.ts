import { describe, expect, it } from 'vitest'
import { emptyDoc, parseDoc, serializeDoc, type PersistedDoc } from '../../src/storage/schema'
import { idleTimer } from '../../src/domain/timer'

function sampleDoc(): PersistedDoc {
  return {
    version: 1,
    tasks: [
      { id: 'a', title: '글쓰기', done: false, order: 0, pomodoroCount: 1, createdAt: 100 },
      { id: 'b', title: '운동', done: true, order: 1, pomodoroCount: 0, createdAt: 200 },
    ],
    records: [{ taskId: 'a', completedAt: 5000 }],
    timer: { phase: 'focus', paused: false, taskId: 'a', endsAt: 9000, remainingMs: null },
  }
}

function parseObj(obj: unknown) {
  return parseDoc(JSON.stringify(obj))
}

describe('schema', () => {
  it('왕복 직렬화 후 같은 문서', () => {
    const doc = sampleDoc()
    const r = parseDoc(serializeDoc(doc))
    expect(r).toEqual({ ok: true, doc })
  })

  it('빈 문서 왕복', () => {
    const r = parseDoc(serializeDoc(emptyDoc()))
    expect(r.ok).toBe(true)
    expect(emptyDoc().timer).toEqual(idleTimer())
  })

  it('JSON이 아니면 parse', () => {
    expect(parseDoc('{')).toEqual({ ok: false, reason: 'parse' })
    expect(parseDoc('not json')).toEqual({ ok: false, reason: 'parse' })
  })

  it('스키마 위반은 schema', () => {
    const s = (o: unknown) => expect(parseObj(o)).toEqual({ ok: false, reason: 'schema' })
    s({ ...sampleDoc(), version: 2 })
    const { version: _v, ...noVersion } = sampleDoc()
    s(noVersion)
    s({ ...sampleDoc(), tasks: {} })
    s({ ...sampleDoc(), tasks: [{ ...sampleDoc().tasks[0], title: 1 }] })
    s({ ...sampleDoc(), timer: { ...sampleDoc().timer, phase: 'run' } })
    s({ ...sampleDoc(), records: [{ taskId: 'a', completedAt: '1' }] })
    s(null)
    s([])
  })
})
