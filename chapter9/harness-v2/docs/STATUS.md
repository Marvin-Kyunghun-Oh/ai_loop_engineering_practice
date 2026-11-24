# STATUS

- 갱신: 2026-11-24
- 단계: **구현 전** (설계 확정, 코드 없음)

## 완료
- v1 rss-wiki 실행을 중단하고 기록을 남겼다(0001). 브랜치 `feat/chap9-harness-setup`, 커밋 `8e03550`, `b8ec582`.
- v1 결함과 v2 개선 항목을 정리했다(`IMPROVEMENTS.md`).
- 사용자와 결정 0001~0010을 합의했다. 지금 사용자가 정할 결정은 남아 있지 않다.
- 위 문서와 인수인계 문서(`CLAUDE.md`, 이 파일)를 `feat/chap9-harness-v2` 브랜치에 커밋하고 푸시했다.

- CLI 결과 JSON 필드를 확인했다(haiku로 3회 실행, 약 $0.007).
  - 샘플은 `src/test/resources/claude-result/`에 있다(`success`, `error-max-budget-usd`, `error-max-turns`).
  - 필드 표는 `IMPROVEMENTS.md` A2에 있다.
  - 핵심은 세 가지다. 판정은 종료 코드가 아니라 `subtype`으로 한다. 오류 시 `result`는 `null`이다. 예산 상한은 턴 1회분을 넘긴 뒤 멈춘다.

- 결정 0011을 추가했다. 샘플 프로젝트로 실제 `claude` 스모크 테스트를 한다. 비용 때문에 범위를 줄일 때는 사용자에게 먼저 묻는다는 규칙도 CLAUDE.md에 넣었다.
- v2 설계 초안 `docs/DESIGN.md`를 작성했다. 사용자가 1차 검토를 마쳤고 스모크 테스트(7.1)를 반영했다. 내용은 다음과 같다.
  - 클래스 구조
  - `harness.yml` 스키마
  - 하네스와 프롬프트가 공유하는 파일 형식(4절)
  - 메인 루프, 테스트, 구현 순서
- 사용자가 `DESIGN.md`를 검토하고 확정했다.

## 다음 할 일 (순서대로)
1. **구현**: `DESIGN.md` 8절의 11단계를 따른다. 11단계는 스모크 테스트이고, 0007의 비용 보정도 이 단계에서 한다.
   - 프롬프트 복사·수정은 8절 7단계에서 한다. 아래 "프롬프트 변경 목록"과 `DESIGN.md` 4절의 형식을 따른다.
   - 각 단계가 끝날 때마다 `./gradlew test` 통과를 확인하고 이 파일을 갱신한다.
   - 8절 6단계에서는 짧은 실행 1회로 표준 입력 프롬프트를 확인한다. 사전에 알린다.
   - `DESIGN.md` 9절의 확인 항목은 해당 단계에서 확인한다.
2. **실제 대상 프로젝트 실행**: 대상 프로젝트가 정해지면(0004) 돌린다. 비용 보정은 스모크 테스트에서 끝냈을 것이므로 보정된 상한을 쓴다.

## 프롬프트 변경 목록 (DESIGN 8절 7단계에서 사용)

| 파일 | 변경 | 근거 |
|---|---|---|
| planner.md | `:44`, `:47`의 메모 규칙 → FAIL만 항목화, 나머지는 BACKLOG, 마일스톤 끝에 결함성 최대 `{{limits.backlog_per_milestone}}`개 | 0010 |
| planner.md | 아카이브 참조 시 Grep 규칙, 자체 결정 1~2줄, JOURNAL 최근 30줄만 읽기 | 0005 |
| planner.md | `:46` "1~2개 선정" → 항목 ID를 `docs/CURRENT`에 기록 | D5 |
| planner.md | `:99` JOURNAL 쓰기 삭제 → 마지막 출력은 요약 한 줄 | 0009 |
| generator.md | `:19` `uv run pytest -x`, `:32` `uv add` → 템플릿 변수 | D3 |
| generator.md | `:15` "첫 미완료 항목" → `docs/CURRENT`의 항목 | D5 |
| generator.md | 허용되지 않은 명령이 필요하면 BLOCKED에 그 명령을 적기 | 0008 |
| generator.md | 아카이브 참조 시 Grep 규칙 | 0005 |
| generator.md | `:24` JOURNAL 쓰기 삭제 | 0009 |
| evaluator.md | `:20` 테스트 명령 → 템플릿 변수 | D3 |
| evaluator.md | 변이 검증은 acceptance에 명시된 것만 | A3 |
| evaluator.md | 메모마다 결함성/보강 분류 | 0010 |
| evaluator.md | REVIEW에 "핵심 결정:" 한 줄 | 0005 |
| evaluator.md | 평가 대상 → `docs/CURRENT`의 항목 | D5 |
| evaluator.md | `:46` JOURNAL 쓰기 삭제 | 0009 |
| planner_bootstrap.md | `:26` JOURNAL 쓰기 삭제 | 0009 |

줄 번호는 v1 파일(`chapter9/harness/src/harness/prompts/`) 기준이다.

## 미확인 항목
`IMPROVEMENTS.md` 6절을 본다. 남은 것은 두 가지다.
- 사용량 한도 도달 시 출력 형태: 재현할 수 없어서, 처음 발생할 때 확인한다.
- 비용 보정: 스모크 테스트로 한다(0011). Pro 한도를 다 쓴 상태여야 비교가 된다.

## 아직 정하지 않은 것
- 첫 대상 프로젝트(0004). 하네스는 특정 프로젝트를 가정하지 않고 `harness.yml`로 분리한다.
