import { describe, it, expect } from 'vitest'
import { createId } from '../../src/domain/id'

describe('createId', () => {
  it('100개 ID가 모두 고유하고 비어 있지 않다', () => {
    const ids = Array.from({ length: 100 }, () => createId())
    expect(ids.every((id) => id.length > 0)).toBe(true)
    expect(new Set(ids).size).toBe(100)
  })
})
