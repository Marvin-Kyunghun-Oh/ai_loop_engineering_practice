# IMPL

## 처리 항목
- T31. 좁은 화면 최소 CSS (사이클 22)

## 변경 파일
- `src/App.vue`: `@media (max-width: 480px)`에서 `.app` 패딩을 `24px 12px`로 축소
- `src/components/TaskList.vue`: `.title`에 `min-width: 0`, `overflow-wrap: anywhere` 추가. `.handle`, `.edit-btn`, `.delete-btn`, `.count`에 `flex-shrink: 0` 추가
- `src/components/TimerPanel.vue`: `.actions`에 `flex-wrap: wrap` 추가

스타일 블록만 수정했고 마크업과 동작은 그대로다.

## 검증
- 확인: `src/App.vue`에 `@media (max-width: 480px)`, `src/components/TaskList.vue`에 `overflow-wrap: anywhere`와 `min-width: 0`, `src/components/TimerPanel.vue`에 `flex-wrap: wrap`이 있다. 위 Edit 결과로 확인했고 Grep으로 다시 실행하지는 않았다.
- `npx vitest run` → 14개 파일, 테스트 97개 통과 (기존 테스트 수정 없음)
- `npx vue-tsc --noEmit` → 종료 코드 0, 출력 없음

## 참고
- 결정: 편집 입력(`.edit-input`)은 `flex: 1`을 유지하고 별도로 건드리지 않았다.
- 새 의존성 없음.
