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

- [x] T27. 드래그 취소 시 시작 인덱스 초기화 (BACKLOG: M4 마감) — PASS 11/12 · 결정: dragend에서 dragFrom을 null로 초기화한다 · 상세: archive/TASKS-M5.md#T27

- [x] T28. 오늘 합계 표시 (R2) — PASS 12/15 · 결정: 오늘 범위는 setDate(+1)로 다음 자정을 구한다 · 상세: archive/TASKS-M5.md#T28

- [x] T29. 알림음: Web Audio 비프와 tick 이벤트 연결 (P4, P5, 6절, 8절) — PASS 10/12 · 결정: 복원 직후 tick은 반환값을 버려 알림음 생략 · 상세: archive/TASKS-M5.md#T29

- [x] T30. 저장 경고 배너와 초기화 안내 (8절) — PASS 13/15 · 결정: 배너 3종은 독립 v-if로 두어 동시 표시 가능 · 상세: archive/TASKS-M5.md#T30

- [x] T31. 좁은 화면 최소 CSS (4절, 1절 비목표의 "깨지지 않는 수준") — PASS 10/12 · 결정: 편집 입력은 flex:1 유지, 제목만 줄바꿈 처리 · 상세: archive/TASKS-M5.md#T31

## M6. 키보드 접근성

- [x] T32. 키보드로 집중 시작 (P1 개선)
  - 내용
    - TaskList의 제목 `span.title`에 `tabindex="0"`과 `role="button"`을 주어 Tab으로 포커스할 수 있게 한다.
    - 제목에서 `keydown.enter`와 `keydown.space`(기본 동작 막기)를 받으면 클릭과 같은 `onTitleClick(task.id)`를 호출한다. P6 확인(confirm)과 P7 규칙도 클릭과 똑같이 적용된다.
    - 포커스가 보이도록 `.title:focus-visible`에 outline을 준다.
    - 편집 중 입력창·체크박스·버튼의 기존 키 동작은 바꾸지 않는다.
  - acceptance
    - `npx vitest run tests/components/TaskList.spec.ts` 통과. 다음을 추가한다:
      - 제목 요소에 `tabindex="0"`이 있다
      - 제목에서 Enter keydown → 집중 시작, 행 강조(`is-current`)
      - 제목에서 Space keydown → 집중 시작
      - 집중 중 다른 행 제목에서 Enter: confirm false면 유지, true면 전환
    - `npx vitest run` 전체 통과
    - `npx vue-tsc --noEmit` 종료 코드 0
  - touch: `src/components/TaskList.vue`, `tests/components/TaskList.spec.ts`
