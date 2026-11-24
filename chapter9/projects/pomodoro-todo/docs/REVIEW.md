판정: 조건부 11/15
핵심 결정: Enter·Space 모두 onTitleClick 재사용
메모:
- [보강] Space/Enter의 preventDefault(스크롤·기본동작 방지)를 검증하는 테스트가 없다
- [보강] 편집 중 입력창 키 동작이 그대로인지 확인하는 회귀 테스트는 기존 편집 테스트에 의존한다

평가 대상: T32 · 사이클 24 · 2026-11-24T18:04:07+09:00

## 직접 확인한 내용
- `npx vitest run tests/components/TaskList.spec.ts`: 17개 통과
- `npx vitest run`: 14개 파일, 101개 통과 (회귀 없음)
- `npx vue-tsc --noEmit`: 오류 없음
- IMPL의 처리 항목(T32)은 CURRENT와 일치. 변경 파일은 TaskList.vue와 TaskList.spec.ts뿐이라 touch 범위 안으로 판단함(touch 목록 자체는 대조하지 않음).
- 변이 검증은 acceptance에 명시돼 있지 않아 하지 않음.
- 화면은 실행하지 않고 diff로 확인함. 변경은 포커스 outline뿐이다.

## 점수
| 축 | 점수 | 근거 |
|---|---|---|
| 사양 충족 | 3 | acceptance 4개 항목과 전체 테스트가 모두 통과. TaskList.vue:89-96에서 tabindex, role, enter/space 핸들러 확인 |
| 모듈 경계 | 3 | TaskList.vue와 해당 spec만 변경. 확인과 P7 로직은 onTitleClick 재사용 |
| 테스트 충실도 | 2 | tabindex, Enter, Space, confirm false/true를 모두 검증(spec 81-119). preventDefault 검증과 편집 중 키 동작 회귀 테스트는 없음 |
| 운영 고려 | 1 | `.title:focus-visible` 추가(TaskList.vue:140). 의존성 변경은 없음. IMPL에 결정은 적혔지만 USAGE 등 사용자 문서에 키보드 조작 안내는 반영되지 않음 |
| 화면 완성도 | 2 | 포커스 outline과 role이 있어 키보드로 발견할 수 있음. 다만 실행해서 확인하지는 않았다 |

기준: 화면이 있는 항목이므로 12점 이상이면 PASS로 보았다. 합계는 3+3+2+1+2=11/15라 PASS 기준(12점)에 1점 못 미쳐 조건부다. 보완할 점은 위 메모의 테스트 보강과 키보드 조작 문서화다.
