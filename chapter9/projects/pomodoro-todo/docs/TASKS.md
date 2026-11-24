# TASKS

## M1. 프로젝트 골격과 할 일 도메인

- [x] T10. 프로젝트 골격 구성 (Vite + Vue 3 + TS strict + Pinia + Vitest) — PASS 12/15 · 결정: vitest 설정을 vite.config.ts 안에 둔다 · 상세: archive/TASKS-M1.md#T10

- [x] T11. 도메인 타입과 주입 가능한 시계 — PASS 10/12 · 결정: createId는 randomUUID 없으면 시각+난수로 대체 · 상세: archive/TASKS-M1.md#T11

- [x] T12. 할 일 스토어 (메모리, CRUD와 순서 변경) — PASS 10/12 · 결정: 시계·ID 주입은 createTasksStore 팩토리로 한다 · 상세: archive/TASKS-M1.md#T12

## M2. 타이머 도메인 로직

- [x] T13. 타이머 기본 전이와 남은 시간 계산 (순수 함수) — PASS 11/12 · 결정: 불변 유지를 위해 no-op 전이는 입력 객체를 그대로 반환 · 상세: archive/TASKS-M2.md#T13

- [x] T14. 시간 경과 처리: 집중 완료 → 휴식 → 대기 (P4, P5) — PASS 11/12 · 결정: advance는 focus 종료 시각 기준으로 break를 이어 처리 · 상세: archive/TASKS-M2.md#T14

- [x] T15. 할 일 클릭 규칙 (P1, P6, P7) — PASS 10/12 · 결정: break 중 클릭은 확인 없이 새 집중 시작 · 상세: archive/TASKS-M2.md#T15

- [x] T16. 복원 계산 (PRD 6절) — PASS 10/12 · 결정: restore는 idle·taskId null도 idle로 돌려주고 advance를 재사용 · 상세: archive/TASKS-M2.md#T16

- [x] T17. 타이머 스토어: 도메인 함수와 할 일 스토어 연결 (P4, R3, T4 연동) — PASS 10/12 · 결정: 할 일 스토어는 deps.tasks 게터로 지연 주입 · 상세: archive/TASKS-M2.md#T17

## M3. 저장소 계층과 실패 정책

- [x] T18. 저장 문서 스키마와 파싱·검증 (순수 함수, PRD 7절) — PASS 10/12 · 결정: 숫자 필드는 유한수만 허용, 최상위 null·배열은 schema · 상세: archive/TASKS-M3.md#T18

- [x] T19. 저장소 어댑터와 실패 정책 (PRD 8절) — PASS 10/12 · 결정: 사용 가능 여부는 시험 키 쓰기로 판별한다 · 상세: archive/TASKS-M3.md#T19

- [x] T20. 스토어 영속화 연결: 시작 시 로드·복원, 변경 시 즉시 저장 (PRD 6절, 7절) — PASS 10/12 · 결정: 변경 감시는 init 안에서 deep watch(sync)로 건다 · 상세: archive/TASKS-M3.md#T20

## M4. 화면: 할 일 목록과 타이머 패널

- [x] T21. 저장소 사용 불가 시 변경 저장 동작 고정 (BACKLOG: M3 마감) — PASS 10/12 · 결정: available false 가드를 saveNow 한 곳에 둔다 · 상세: archive/TASKS-M4.md#T21

- [x] T22. 타이머 패널 컴포넌트 (PRD 4절, P2, P3) — PASS 12/15 · 결정: 표시용 now는 패널 내부 1초 setInterval, tick은 T26 · 상세: archive/TASKS-M4.md#T22

- [x] T23. 할 일 입력과 목록 행 (T1, T2, T5, R1, P1, P6, P7) — 조건부 11/15 · 결정: 입력은 form submit으로 Enter와 버튼을 통합 · 상세: archive/TASKS-M4.md#T23

- [x] T24. 제목 인라인 편집과 삭제 (T3, T4) — PASS 12/15 · 결정: 편집 확정은 rename 성공 여부로 판단한다 · 상세: archive/TASKS-M4.md#T24

- [x] T25. 드래그 앤 드롭 순서 변경 (T6) — PASS 12/15 · 결정: 드래그 출발 인덱스는 컴포넌트 ref(dragFrom)에 둔다 · 상세: archive/TASKS-M4.md#T25

- [x] T26. 앱 조립: 화면 배치, 영속화 시작, 시간 경과 처리 — PASS 12/15 · 결정: 영속화 시작은 main.ts가 아니라 App setup에서 한다 · 상세: archive/TASKS-M4.md#T26

## M5. 기록 표시·알림음·마무리

- [x] T27. 드래그 취소 시 시작 인덱스 초기화 (BACKLOG: M4 마감)
  - 내용
    - TaskList 행에 `dragend` 핸들러를 붙여 `dragFrom`을 null로 초기화한다(행 밖 drop, Esc 취소 포함).
    - `dragFrom`이 null일 때 drop은 아무것도 하지 않는다(기존 동작 유지 확인).
  - acceptance
    - `npx vitest run tests/components/TaskList.spec.ts` 통과. 다음을 추가한다:
      - 행 A, B, C에서 A dragstart → A dragend → (dragstart 없이) C drop → 순서 A, B, C 그대로
    - `npx vue-tsc --noEmit` 종료 코드 0
  - touch: `src/components/TaskList.vue`, `tests/components/TaskList.spec.ts`

- [x] T28. 오늘 합계 표시 (R2)
  - 내용
    - `src/domain/stats.ts`: `countToday(records, now): number` 순수 함수. 브라우저 로컬 시간대의 오늘 자정(`new Date(now)`에 `setHours(0,0,0,0)`) 이상, 다음 자정 미만인 `completedAt`만 센다.
    - `src/components/TodaySummary.vue`: 전역 timer 스토어의 `records`로 "오늘 집중: 🍅 N" 표시. 자정 경계 반영을 위해 표시용 `now`를 1초 간격으로 갱신한다(unmount 시 해제).
    - App.vue에서 TaskList 아래에 배치한다.
  - acceptance
    - `npx vitest run tests/domain/stats.spec.ts` 통과. 최소 다음을 포함한다:
      - 빈 배열 → 0
      - 로컬 시각으로 만든 오늘 00:00:00.000, 오늘 23:59:59.999 → 포함; 어제 23:59:59.999, 내일 00:00:00.000 → 제외
    - `npx vitest run tests/components/TodaySummary.spec.ts` 통과: 오늘 2건·어제 1건 records → "🍅 2"; fake timers로 다음 날 자정을 넘기면 "🍅 0"
    - `npx vitest run` 전체 통과
    - `npx vue-tsc --noEmit` 종료 코드 0
  - touch: `src/domain/stats.ts`, `tests/domain/stats.spec.ts`, `src/components/TodaySummary.vue`, `tests/components/TodaySummary.spec.ts`, `src/App.vue`

- [x] T29. 알림음: Web Audio 비프와 tick 이벤트 연결 (P4, P5, 6절, 8절)
  - 내용
    - `src/audio/beep.ts`: `playBeep(): void`. `AudioContext`(없으면 `webkitAudioContext`)로 짧은 사인파 비프를 낸다. AudioContext가 없거나 생성·재생 중 예외가 나도 던지지 않는다(8절). 음원 파일을 쓰지 않는다.
    - App.vue: 1초 간격 tick의 반환 이벤트가 하나 이상이면 `playBeep()`을 한 번 호출한다. 마운트 직후 즉시 호출하는 tick의 이벤트로는 재생하지 않는다(6절: 복원 시 놓친 알림음 재생 안 함).
  - acceptance
    - `npx vitest run tests/audio/beep.spec.ts` 통과: `AudioContext` 미정의 → 예외 없음; 생성자가 throw하는 stub → 예외 없음; 정상 stub → oscillator `start` 호출 1회
    - `npx vitest run tests/App.spec.ts` 통과. `vi.mock('../src/audio/beep')`로 다음을 추가한다:
      - 할 일 클릭 후 25분 진행 → playBeep 1회; 이어서 5분 진행 → 누적 2회
      - 집중 시작 시각이 26분 전인 저장 문서를 localStorage에 넣고 마운트 → playBeep 0회, 패널 "휴식 중"
    - `npx vitest run` 전체 통과
    - `npx vue-tsc --noEmit` 종료 코드 0
  - touch: `src/audio/beep.ts`, `tests/audio/beep.spec.ts`, `src/App.vue`, `tests/App.spec.ts`

- [x] T30. 저장 경고 배너와 초기화 안내 (8절)
  - 내용
    - App.vue가 영속화 스토어 상태로 TimerPanel 위에 배너를 표시한다(`role="alert"`).
      - `saveFailed`: "저장에 실패했습니다. 새로고침하면 변경 사항이 사라질 수 있습니다"
      - `storageUnavailable`: "브라우저 저장소를 사용할 수 없어 변경 사항이 저장되지 않습니다"
      - `resetNotice`: "저장된 데이터를 읽지 못해 초기화했습니다"
    - 배너는 해당 상태가 true인 동안만 보인다. 닫기 버튼은 두지 않는다.
  - acceptance
    - `npx vitest run tests/App.spec.ts` 통과. 다음을 추가한다:
      - 정상 마운트 → 배너 없음
      - 마운트 후 `pomodoro-todo` 키의 setItem만 throw하도록 spy → 할 일 추가 → 저장 실패 문구 표시; spy 해제 후 할 일 추가 → 문구 사라짐
      - 모든 setItem이 throw하는 상태로 마운트 → 저장소 사용 불가 문구 표시, 저장 실패 문구 없음
      - `pomodoro-todo`에 `"{not json"`을 넣고 마운트 → 초기화 안내 문구 표시
    - `npx vitest run` 전체 통과
    - `npx vue-tsc --noEmit` 종료 코드 0
  - touch: `src/App.vue`, `tests/App.spec.ts`

- [x] T31. 좁은 화면 최소 CSS (4절, 1절 비목표의 "깨지지 않는 수준")
  - 내용
    - App.vue에 `@media (max-width: 480px)` 규칙을 두어 바깥 여백을 줄인다.
    - TaskList 행은 flex로 두고 제목 영역에 `min-width: 0`과 `overflow-wrap: anywhere`를 적용해 긴 제목이 행을 밀어내지 않게 한다. 버튼·🍅 N은 줄어들지 않게(`flex-shrink: 0`) 한다.
    - TimerPanel 버튼 묶음은 `flex-wrap: wrap`으로 둔다.
    - 동작·마크업 구조는 바꾸지 않는다(스타일 블록만 수정).
  - acceptance
    - Grep으로 `src/App.vue`에 `@media (max-width: 480px)`, `src/components/TaskList.vue`에 `overflow-wrap: anywhere`와 `min-width: 0`, `src/components/TimerPanel.vue`에 `flex-wrap: wrap`이 있음을 확인
    - `npx vitest run` 전체 통과(기존 테스트 수정 없이)
    - `npx vue-tsc --noEmit` 종료 코드 0
  - touch: `src/App.vue`, `src/components/TaskList.vue`, `src/components/TimerPanel.vue`
