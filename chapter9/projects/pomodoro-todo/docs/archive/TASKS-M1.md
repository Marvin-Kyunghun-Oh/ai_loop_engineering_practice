# TASKS-M1.md

## M1. 프로젝트 골격과 할 일 도메인

- [x] T10. 프로젝트 골격 구성 (Vite + Vue 3 + TS strict + Pinia + Vitest)
  - 내용
    - `npm create` 없이 설정 파일을 직접 작성한다: `package.json`, `vite.config.ts`, `vitest.config.ts`(또는 vite.config.ts 안의 test 설정), `tsconfig.json`(strict: true, src와 tests 포함), `index.html`, `src/env.d.ts`.
    - 의존성은 `npm install`로 설치한다: vue, pinia / 개발용 vite, @vitejs/plugin-vue, typescript, vue-tsc, vitest, @vue/test-utils, jsdom.
    - `src/main.ts`(createApp + Pinia 등록), `src/App.vue`(제목 "뽀모도로 할 일"만 표시하는 최소 화면).
    - Vitest 환경은 jsdom, 테스트 파일 패턴은 `tests/**/*.spec.ts`.
    - 스모크 테스트 `tests/App.spec.ts`: App을 마운트하면 "뽀모도로 할 일" 문구가 렌더링된다.
  - acceptance
    - `npx vue-tsc --noEmit` 종료 코드 0
    - `npx vitest run tests/App.spec.ts` 통과 (1개 이상 테스트, 실패 0)
    - `package.json`에 위 의존성이 기록되어 있고 `node_modules/`는 커밋 대상이 아니다(.gitignore에 이미 있음)
  - touch: `package.json`, `package-lock.json`, `vite.config.ts`, `vitest.config.ts`, `tsconfig.json`, `index.html`, `src/env.d.ts`, `src/main.ts`, `src/App.vue`, `tests/App.spec.ts`

- [x] T11. 도메인 타입과 주입 가능한 시계
  - 내용
    - `src/domain/types.ts`: PRD 7절 개념 모델 타입
      - `Task { id: string; title: string; done: boolean; order: number; pomodoroCount: number; createdAt: number }`
      - `PomodoroRecord { taskId: string; completedAt: number }`
      - `TimerState { phase: 'idle' | 'focus' | 'break'; paused: boolean; taskId: string | null; endsAt: number | null; remainingMs: number | null }`
      - 상수 `FOCUS_MS = 25 * 60 * 1000`, `BREAK_MS = 5 * 60 * 1000`
    - `src/domain/clock.ts`: `interface Clock { now(): number }`, `systemClock`(Date.now 사용), 테스트용 `createFakeClock(start: number)`(`now()`, `advance(ms)`, `set(ms)` 제공).
    - `src/domain/id.ts`: `createId(): string` (crypto.randomUUID 사용, 없으면 시각+난수 대체).
  - acceptance
    - `npx vitest run tests/domain/clock.spec.ts` 통과: fake clock의 now/advance/set 동작, systemClock.now()가 number를 반환
    - `npx vitest run tests/domain/id.spec.ts` 통과: 100회 생성한 ID가 모두 서로 다르고 빈 문자열이 아님
    - `npx vue-tsc --noEmit` 종료 코드 0
  - touch: `src/domain/types.ts`, `src/domain/clock.ts`, `src/domain/id.ts`, `tests/domain/clock.spec.ts`, `tests/domain/id.spec.ts`

- [x] T12. 할 일 스토어 (메모리, CRUD와 순서 변경)
  - 내용
    - `src/stores/tasks.ts`: Pinia 스토어 `useTasksStore`. 시계와 ID 생성기는 주입 가능하게 한다(기본값 systemClock, createId).
    - state: `tasks: Task[]`. getter `orderedTasks`(order 오름차순).
    - `add(title)`: 앞뒤 공백 제거 후 빈 문자열이면 추가하지 않고 null 반환. 새 항목은 맨 아래(order 최대값 + 1), done=false, pomodoroCount=0, createdAt=시계 now.
    - `rename(id, title)`: 공백 제거 후 빈 문자열이면 거부(false 반환, 제목 유지). 없는 id면 false.
    - `remove(id)`: 해당 할 일 제거. 완료 이력·타이머 연동은 이 항목에서 다루지 않는다(M2 이후).
    - `toggleDone(id)`: done 전환. order는 바뀌지 않는다.
    - `reorder(fromIndex, toIndex)`: orderedTasks 기준 인덱스로 이동 후 order를 0..n-1로 다시 매긴다. 범위 밖 인덱스는 무시.
    - `incrementPomodoro(id)`: pomodoroCount +1 (M2 타이머가 사용).
  - acceptance
    - `npx vitest run tests/stores/tasks.spec.ts` 통과. 최소 다음 사례를 포함한다:
      - add: "  보고서  " → 제목 "보고서"; "   " → 추가 안 됨; 세 번 추가하면 추가 순서대로 맨 아래에 붙음
      - rename: 정상 변경; 빈 제목 거부 시 기존 제목 유지
      - remove: 대상만 제거되고 나머지 순서 유지
      - toggleDone: done 전환 후 orderedTasks 위치 불변
      - reorder: [A,B,C]에서 (0→2) → [B,C,A], (2→0) → [A,B,C]로 복귀; 범위 밖 인덱스는 변화 없음
      - incrementPomodoro: 대상 pomodoroCount만 1 증가
    - `npx vue-tsc --noEmit` 종료 코드 0
  - touch: `src/stores/tasks.ts`, `tests/stores/tasks.spec.ts`
