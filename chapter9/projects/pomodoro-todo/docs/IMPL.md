# IMPL (사이클 24)

## 처리한 항목
T32. 키보드로 집중 시작 (P1 개선)

## 변경 파일
- `src/components/TaskList.vue`: 제목 span에 `tabindex="0"`, `role="button"`, `keydown.enter`/`keydown.space`(prevent) → `onTitleClick(task.id)`. `.title:focus-visible` outline 추가.
- `tests/components/TaskList.spec.ts`: tabindex/role, Enter, Space, 집중 중 다른 행 Enter(confirm false/true) 테스트 4개 추가.

## 검증
- `npx vitest run tests/components/TaskList.spec.ts` → 17개 통과
- `npx vitest run` → 14개 파일, 101개 통과
- `npx vue-tsc --noEmit` → 오류 없음(종료 코드 0)

## 참고
- 결정: Enter와 Space 모두 클릭과 같은 `onTitleClick`을 호출해 P6 확인과 P7 규칙을 그대로 재사용한다.
- 새 의존성 없음. 화면 변경은 포커스 outline뿐이며 실행은 `npm run dev`.
