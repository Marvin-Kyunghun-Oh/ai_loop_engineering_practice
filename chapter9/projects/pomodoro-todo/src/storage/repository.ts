import type { Clock } from '../domain/clock'
import { emptyDoc, parseDoc, serializeDoc, STORAGE_KEY, type PersistedDoc } from './schema'

export type LoadNotice = 'none' | 'resetCorrupt'

export interface Repository {
  available: boolean
  load(): { doc: PersistedDoc; notice: LoadNotice }
  save(doc: PersistedDoc): boolean
}

const PROBE_KEY = 'pomodoro-todo-probe'

export function createRepository(getStorage: () => Storage, clock: Clock): Repository {
  let storage: Storage | null = null
  try {
    const s = getStorage()
    s.setItem(PROBE_KEY, '1')
    s.removeItem(PROBE_KEY)
    storage = s
  } catch {
    storage = null
  }
  const available = storage !== null

  return {
    available,
    load() {
      if (!storage) return { doc: emptyDoc(), notice: 'none' }
      let raw: string | null
      try {
        raw = storage.getItem(STORAGE_KEY)
      } catch {
        return { doc: emptyDoc(), notice: 'none' }
      }
      if (raw === null) return { doc: emptyDoc(), notice: 'none' }
      const result = parseDoc(raw)
      if (result.ok) return { doc: result.doc, notice: 'none' }
      try {
        storage.setItem(`${STORAGE_KEY}-corrupt-${clock.now()}`, raw)
      } catch {
        // 백업 실패는 무시한다
      }
      return { doc: emptyDoc(), notice: 'resetCorrupt' }
    },
    save(doc) {
      if (!storage) return false
      try {
        storage.setItem(STORAGE_KEY, serializeDoc(doc))
        return true
      } catch {
        return false
      }
    },
  }
}
