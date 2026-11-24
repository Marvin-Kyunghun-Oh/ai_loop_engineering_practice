# TASKS-M4.md

## M4. 화면: 할 일 목록과 타이머 패널

- [x] T21. 저장소 사용 불가 시 변경 저장 동작 고정 (BACKLOG: M3 마감)
  - 내용
    - `repository.available`이 false면 init 이후 변경이 일어나도 `save`를 호출하지 않는다. 이 경우 `saveFailed`는 false로 유지하고 경고는 `storageUnavailable`만으로 알린다(PRD 8절: 메모리 동작 + 상시 배너).
    - available이 true인 경로의 동작은 바꾸지 않는다.
  - acceptance
    - `npx vitest run tests/stores/persistence.spec.ts` 통과. 다음을 추가한다:
      - available false인 저장소(save를 vi.fn으로 감싼 가짜)로 init 후 할 일 추가·타이머 시작 → save 호출 0회, saveFailed false, storageUnavailable true, 메모리 상태(할 일 1개, phase 'focus')는 유지
    - `npx vitest run` 전체 통과
    - `npx vue-tsc --noEmit` 종료 코드 0
  - touch: `src/stores/persistence.ts`, `tests/stores/persistence.spec.ts`

- [x] T22. 타이머 패널 컴포넌트 (PRD 4절, P2, P3)
  - 내용
    - `src/components/TimerPanel.vue`: 전역 `useTasksStore`·`useTimerStore`를 쓴다.
      - idle이면 안내 문구 "할 일을 클릭해 집중을 시작하세요"만 표시.
      - 그 외: 대상 할 일 제목, 단계 문구(집중 중 / 휴식 중 / 일시정지), 남은 시간 `formatMmSs(remainingMs(timer, now))`.
      - 버튼: 진행 중이면 [일시정지], 일시정지면 [재개], 항상 [취소]. 각각 store의 pause/resume/cancel.
    - 표시용 현재 시각 `now`는 컴포넌트 안에서 1초 간격 setInterval로 `Date.now()`를 갱신한다(unmount 시 해제). tick 호출(시간 경과 처리)은 T26 범위다.
  - acceptance
    - `npx vitest run tests/components/TimerPanel.spec.ts` 통과. `vi.useFakeTimers()`·`vi.setSystemTime`과 `setActivePinia(createPinia())`로 최소 다음을 포함한다:
      - idle → 안내 문구 표시, 버튼 없음
      - 할 일 1개에 clickTask 후 → 제목, "집중 중", "25:00"; 61초 진행(advanceTimersByTime) 후 "23:59"
      - [일시정지] 클릭 → "일시정지"와 [재개] 표시; [재개] 클릭 → "집중 중"; [취소] 클릭 → 안내 문구
    - `npx vue-tsc --noEmit` 종료 코드 0
  - touch: `src/components/TimerPanel.vue`, `tests/components/TimerPanel.spec.ts`

- [x] T23. 할 일 입력과 목록 행 (T1, T2, T5, R1, P1, P6, P7)
  - 내용
    - `src/components/TaskInput.vue`: 입력창 + [추가] 버튼. Enter 또는 버튼으로 `add`. 추가되면 입력창을 비운다.
    - `src/components/TaskList.vue`: `orderedTasks`를 행으로 표시. 행: 드래그 핸들 `≡`(동작은 T25), 체크박스(toggleDone), 제목, `🍅 N`. done이면 제목에 취소선 클래스, 타이머 대상 행은 강조 클래스(예: `is-current`).
    - 제목 클릭 → `clickTask`. 결과가 'confirmNeeded'면 `window.confirm("현재 뽀모도로를 취소하고 새로 시작할까요?")`, 확인이면 `confirmSwitch`.
  - acceptance
    - `npx vitest run tests/components/TaskList.spec.ts` 통과. 최소 다음을 포함한다:
      - 입력 "  보고서  " + Enter → 행 1개 "보고서", 입력창 비움; 공백만 입력 → 행 추가 없음
      - 체크박스 클릭 → done 클래스 적용, 행 순서 그대로
      - 제목 클릭 → timer.phase 'focus', 그 행에 강조 클래스
      - 집중 중 다른 행 클릭: confirm false(vi.spyOn) → 대상 그대로; true → 새 대상으로 전환
      - pomodoroCount 3인 할 일 → `🍅 3` 표시
    - `npx vue-tsc --noEmit` 종료 코드 0
  - touch: `src/components/TaskInput.vue`, `src/components/TaskList.vue`, `tests/components/TaskList.spec.ts`

- [x] T24. 제목 인라인 편집과 삭제 (T3, T4)
  - 내용
    - TaskList 행에 ✎, 🗑 버튼 추가.
    - ✎ → 제목 자리에 입력창(현재 제목). Enter → `rename`, 성공 시 편집 종료, 빈 제목이면 편집 유지. Esc → 원래 제목으로 편집 종료.
    - 🗑 → `window.confirm` 확인 시 `remove` 후 timer 스토어 `onTaskRemoved(id)` 호출(대상이면 미집계 취소). 이력(records)은 지우지 않는다.
  - acceptance
    - `npx vitest run tests/components/TaskList.spec.ts` 통과. 다음을 추가한다:
      - ✎ → "새 제목" Enter → 제목 변경; 빈 문자열 Enter → 원래 제목 유지, 입력창 남음; Esc → 원래 제목
      - 🗑 confirm false → 그대로; true → 행 제거
      - 타이머 대상 할 일 삭제 → phase 'idle', records 개수 변화 없음
    - `npx vue-tsc --noEmit` 종료 코드 0
  - touch: `src/components/TaskList.vue`, `tests/components/TaskList.spec.ts`

- [x] T25. 드래그 앤 드롭 순서 변경 (T6)
  - 내용
    - TaskList 행에 HTML5 DnD(`draggable`, dragstart/dragover/drop)를 직접 붙인다. 라이브러리 추가 금지.
    - dragstart에서 원래 인덱스를 기억하고, 다른 행에 drop하면 `reorder(from, to)`.
  - acceptance
    - `npx vitest run tests/components/TaskList.spec.ts` 통과. 다음을 추가한다:
      - 행 A, B, C에서 A dragstart → C drop(trigger) → 표시 순서 B, C, A, 각 order 0·1·2
      - 같은 행에 drop → 순서 변화 없음
    - `npx vue-tsc --noEmit` 종료 코드 0
  - touch: `src/components/TaskList.vue`, `tests/components/TaskList.spec.ts`

- [x] T26. 앱 조립: 화면 배치, 영속화 시작, 시간 경과 처리
  - 내용
    - App.vue: 상단 TimerPanel, 그 아래 TaskInput·TaskList를 배치한다.
    - 앱 시작 시 `createRepository(() => localStorage, systemClock)`로 영속화 스토어를 만들어 `init()`을 호출한다(위치는 main.ts 또는 App의 setup).
    - App이 1초 간격으로 timer 스토어 `tick()`을 호출한다(unmount 시 해제). 반환 이벤트는 M5의 알림음에서 쓴다.
  - acceptance
    - `npx vitest run tests/App.spec.ts` 통과. fake timers로 최소 다음을 포함한다:
      - 마운트 시 안내 문구와 할 일 입력창 표시
      - 할 일 추가 후 제목 클릭, 25분 진행 → 행의 `🍅 1`, 패널 "휴식 중"
    - `npx vitest run` 전체 통과
    - `npx vue-tsc --noEmit` 종료 코드 0
  - touch: `src/App.vue`, `src/main.ts`, `tests/App.spec.ts`
