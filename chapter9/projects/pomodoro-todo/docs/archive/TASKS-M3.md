# TASKS-M3.md

## M3. 저장소 계층과 실패 정책

- [x] T18. 저장 문서 스키마와 파싱·검증 (순수 함수, PRD 7절)
  - 내용
    - `src/storage/schema.ts`에 다음을 둔다.
      - `STORAGE_KEY = 'pomodoro-todo'`, `SCHEMA_VERSION = 1`
      - `PersistedDoc = { version: 1; tasks: Task[]; records: PomodoroRecord[]; timer: TimerState }`
      - `emptyDoc()`: tasks·records 빈 배열, timer = `idleTimer()`
      - `serializeDoc(doc): string` (JSON.stringify)
      - `parseDoc(raw: string): { ok: true; doc: PersistedDoc } | { ok: false; reason: 'parse' | 'schema' }`
    - 스키마 검증은 직접 작성한다(라이브러리 추가 금지). version이 1이 아니거나, 각 Task/PomodoroRecord/TimerState 필드의 타입이 types.ts와 다르거나(phase는 'idle'|'focus'|'break'만, taskId·endsAt·remainingMs는 null 허용) 배열이 아니면 `schema`.
    - JSON.parse가 던지면 `parse`.
  - acceptance
    - `npx vitest run tests/storage/schema.spec.ts` 통과. 최소 다음을 포함한다:
      - `parseDoc(serializeDoc(doc))`가 원래 doc과 deep equal (할 일 2개, 이력 1건, focus 타이머)
      - `parseDoc(serializeDoc(emptyDoc()))` 성공
      - `'{'`·`'not json'` → reason 'parse'
      - version 2, version 누락, tasks가 객체, Task의 title이 숫자, timer.phase가 'run', records 원소의 completedAt이 문자열 → 각각 reason 'schema'
    - `npx vue-tsc --noEmit` 종료 코드 0
  - touch: `src/storage/schema.ts`, `tests/storage/schema.spec.ts`

- [x] T19. 저장소 어댑터와 실패 정책 (PRD 8절)
  - 내용
    - `src/storage/repository.ts`에 `createRepository(getStorage: () => Storage, clock: Clock)`를 둔다. 반환:
      - `available: boolean`: 생성 시 getStorage 호출, 시험 키 setItem/removeItem이 던지면 false
      - `load(): { doc: PersistedDoc; notice: 'none' | 'resetCorrupt' }`: 키 없음 → emptyDoc, notice 'none'. parseDoc 실패 → 원본 문자열을 `pomodoro-todo-corrupt-<clock.now()>` 키에 보관하고 emptyDoc, notice 'resetCorrupt'. available이 false면 emptyDoc, 'none'.
      - `save(doc): boolean`: setItem 성공 true, 던지면 false. available이 false면 false.
    - 백업 setItem이 실패해도 load는 던지지 않는다.
  - acceptance
    - `npx vitest run tests/storage/repository.spec.ts` 통과. 메모리 Storage 가짜 객체로 최소 다음을 포함한다:
      - save 후 load → 같은 doc, notice 'none'
      - 손상된 문자열 저장 상태에서 load → emptyDoc, 'resetCorrupt', 백업 키(`pomodoro-todo-corrupt-<fake now>`)에 원본 그대로
      - setItem이 QuotaExceeded를 던지는 Storage → save false, 다음 정상 setItem에서는 true
      - getStorage가 던지거나 setItem이 항상 던지는 Storage → available false, load는 emptyDoc
    - `npx vue-tsc --noEmit` 종료 코드 0
  - touch: `src/storage/repository.ts`, `tests/storage/repository.spec.ts`

- [x] T20. 스토어 영속화 연결: 시작 시 로드·복원, 변경 시 즉시 저장 (PRD 6절, 7절)
  - 내용
    - `src/stores/persistence.ts`에 `createPersistenceStore(storeId, deps)`(repository·clock·tasks·timer 스토어 주입)를 둔다. state: `saveFailed`, `storageUnavailable`, `resetNotice`(배너 표시는 M4/M5).
    - `init()`: load → 할 일 스토어에 tasks, 타이머 스토어에 records를 넣고, timer는 `restore(saved, now, taskExists)`로 계산해 넣는다. restore의 completed는 records에 추가하고 해당 할 일의 pomodoroCount를 +1한다. 이어서 한 번 저장한다.
    - init 이후 tasks·records·timer가 바뀔 때마다(`$subscribe` 또는 deep watch, flush 'sync') 전체 문서를 save한다. save false → saveFailed true, 이후 성공 → false.
    - 필요하면 할 일·타이머 스토어에 상태 일괄 대입용 action(예: `hydrate`)을 추가한다.
  - acceptance
    - `npx vitest run tests/stores/persistence.spec.ts` 통과. 최소 다음을 포함한다:
      - 할 일 추가 직후 Storage의 `pomodoro-todo` 값에 그 할 일이 들어 있음
      - 집중 중(종료 예정 T) 저장된 문서를 T+2분에 init → timer.phase 'break', records 1건, 대상 pomodoroCount +1
      - 대상 할 일이 없는 타이머 문서 init → idle
      - save가 실패하는 저장소 → saveFailed true, 이후 성공 → false
      - 손상 문서 init → resetNotice true; 사용 불가 저장소 → storageUnavailable true
    - `npx vitest run` 전체 통과(회귀 없음)
    - `npx vue-tsc --noEmit` 종료 코드 0
  - touch: `src/stores/persistence.ts`, `src/stores/tasks.ts`, `src/stores/timer.ts`, `tests/stores/persistence.spec.ts`
