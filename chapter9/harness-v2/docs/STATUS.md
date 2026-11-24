# STATUS

- 갱신: 2026-11-24
- 단계: **설계 전** (문서 정리 완료, 코드 없음)

## 완료
- v1 rss-wiki 실행을 중단하고 기록을 남겼다(0001). 브랜치 `feat/chap9-harness-setup`, 커밋 `8e03550`, `b8ec582`.
- v1 결함과 v2 개선 항목을 정리했다(`IMPROVEMENTS.md`).
- 사용자와 결정 0001~0010을 합의했다. 지금 사용자가 정할 결정은 남아 있지 않다.
- 위 문서와 인수인계 문서(`CLAUDE.md`, 이 파일)를 `feat/chap9-harness-v2` 브랜치에 커밋하고 푸시했다.

## 다음 할 일 (순서대로)
1. **CLI 결과 JSON 필드 확인**
   - 짧은 `claude -p` 실행 2~3번이면 된다. 사용량이 아주 적게 들지만, 실행 전에 사용자에게 알린다.
     - `claude -p "hi" --output-format json`: 정상 종료 시 필드 구조(비용, 토큰, 오류, 종료 사유)
     - `--max-budget-usd 0.01`: 예산 상한에 걸렸을 때의 종료 사유와 종료 코드
   - 출력은 JUnit 테스트용 샘플(`src/test/resources/claude-result-*.json`)로 보관한다.
   - 결과를 `IMPROVEMENTS.md` 6절과 0007에 반영한다.
2. **v2 설계 문서 `docs/DESIGN.md` 작성**
   - 클래스 구조: 설정 로더, `claude` 실행기 인터페이스와 가짜 구현, 비용 기록·상한, 결정 합의 상태 기계, 문서 아카이브, JOURNAL 기록, 메인 루프
   - `harness.yml` 스키마: models, limits, commands, permissions
   - 프롬프트 템플릿 변수 이름과 치환 방식. 예: `{{commands.test}}`
   - 하네스가 기계적으로 읽는 형식
     - REVIEW.md의 "핵심 결정:" 줄(0005)
     - REVIEW 메모의 분류 표기, 결함성/보강(0010)
     - `docs/CURRENT`(IMPROVEMENTS D5)
     - `USAGE.csv` 열(0007)
     - JOURNAL 줄(0009)
3. **프롬프트 수정**
   - v1 프롬프트를 v2로 복사한 뒤 고친다. 템플릿 변수와 형식이 2번에서 정해진 뒤에 한다.
   - 변경 목록은 아래 "프롬프트 변경 목록"을 따른다.
4. **Gradle 골격과 구현**
   - 순서는 v1 동작 포팅 → 개선 항목(IMPROVEMENTS 4절 우선순위)이다.
   - JUnit 테스트를 함께 작성한다.
5. **첫 실행**
   - 대상 프로젝트가 정해지면 `max_total_usd: 10`으로 돌린다.
   - 크레딧 감소량과 `USAGE.csv` 합계를 비교해 상한을 보정한다(0007).

## 프롬프트 변경 목록 (3번에서 사용)

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
`IMPROVEMENTS.md` 6절을 본다. 대부분 다음 할 일 1번에서 확인된다.

## 아직 정하지 않은 것
- 첫 대상 프로젝트(0004). 하네스는 특정 프로젝트를 가정하지 않고 `harness.yml`로 분리한다.
