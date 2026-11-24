# STATUS

- 갱신: 2026-11-24
- 단계: **구현 중** (DESIGN 8절 1~6단계 완료, 테스트 114개 통과(실제 claude 확인 3개는 평소 건너뜀). 다음은 7단계)

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

### 구현 (DESIGN 8절)
- 진행 방식(사용자 합의): 1~2단계 후 멈추고 사용자가 코드 스타일을 검토했다. 그 뒤 3~5단계를 이어서 진행했다.
- **1단계 완료**: Gradle 골격.
  - Gradle wrapper 9.8.2, JDK 21 toolchain, Jackson 2.23.0(BOM), JUnit 5.14.4.
  - `Main`은 인자 검사만 한다. Gradle 산출물용 `.gitignore`를 추가했다.
- **2단계 완료**: `claude` 패키지의 `Outcome`, `TokenUsage`, `AgentResult`, `ResultParser`. `ResultParserTest` 20개가 통과한다.
  - 구현 메모: 비용을 모르면 `AgentResult.costUsd`는 null이다(`costKnown()`). 다른 필수 필드만 빠졌으면 비용은 살린다.
  - 구현 메모: 토큰 하위 필드(`input_tokens` 등)가 없으면 0으로 둔다. 분석용이기 때문이다. `usage` 객체 자체가 없으면 `INVALID_RESULT`다.
  - 2단계에서 나온 미결 3건은 결정 0012로 정했다. 형식 오류는 `INVALID_RESULT`로 즉시 HALT, 토큰은 `modelUsage` 합산, `harness.yml`의 모르는 키는 거부.
- **3단계 완료**: `config` 패키지의 `HarnessConfig`, `ConfigLoader`, `ConfigException`. `ConfigLoaderTest` 15개.
  - 선택 키는 `limits.max_turns`뿐이다(역할별 일부만 줘도 된다). 나머지는 모두 필수다.
  - 검증 문제는 모아서 한 번에 알려 준다.
  - 추가 검증: `max_agent_usd <= max_total_usd`, `test_path`에 `{path}`가 있는지, Bash 패턴이 `Bash(...)` 형식인지.
- **4단계 완료**: `state`(`ProjectFiles`, `HaltNotice`, `TextFiles`, `Timestamps`), `cost`(`CostLedger`, `UsageRecord`), `journal`(`JournalWriter`). 테스트 36개.
  - `.cycle_count`가 숫자가 아니면 예외를 던진다. v1처럼 0으로 되돌리면 c1부터 다시 시작해 JOURNAL과 로그가 섞인다.
  - USAGE.csv에 깨진 줄이 있으면 예외를 던진다. 건너뛰면 누적 비용이 작게 복원되어 상한이 늦게 걸린다.
  - 같은 사이클을 다시 돌면 원본 로그는 `c1-planner-2.json`처럼 번호를 붙여 저장한다. 덮어쓰지 않는다.
  - JOURNAL의 금액은 센트 단위로 반올림한다. 정확한 값은 USAGE.csv에 있다.
- **5단계 완료**: `ClaudeRunner`, `AgentRequest`, `Harness`. 테스트용으로 `FakeClaudeRunner`, `HarnessTest` 20개, `ToolPolicyTest` 4개.
  - 순서 변경: `ToolPolicy`(원래 7단계)를 5단계로 당겼다. 요청을 만들려면 필요하고, 설정을 옮겨 담기만 하는 클래스이기 때문이다.
  - `PromptProvider` 인터페이스를 추가했다. 7단계에서 `PromptRenderer`가 구현한다. 지금은 테스트에서 람다로 대신한다.
  - 8·9·10단계 자리는 `Harness`에 `TODO(n단계)`로 표시했다. `Main`은 아직 루프를 부르지 않는다(6·7단계가 필요하다).
  - 설계에 없던 동작 4가지. 사용자가 확인했고 `DESIGN.md` 6절에 반영했다.
    1. 사이클 시작 때 `CURRENT`도 지운다(`DONE`과 같은 방식). 지우지 않으면 planner가 새로 쓰지 않아도 지난 항목으로 generator가 돈다.
    2. 시작할 때 `HALT`가 있으면 아무것도 실행하지 않는다. v1은 planner를 한 번 돌린 뒤에야 멈췄다.
    3. HALT 후 카운터 처리를 구분했다. 에이전트가 쓴 HALT는 카운터를 저장한다(v1과 같음). 하네스가 쓴 HALT(예산, 오류 연속, CURRENT, 형식 오류)는 저장하지 않는다.
    4. 비용을 모르는 실행(TIMEOUT, JSON 없음)은 누적에 더하지 않는다. 실제로는 돈이 들었을 수 있다. 보수적으로 가려면 `max_agent_usd`를 더하는 방법이 있다.
- **6단계 완료**: `ClaudeExecutable`(실행 파일 찾기), `ProcessClaudeRunner`. 테스트 13개와 실제 확인 3개.
  - 프로세스 처리는 가짜 claude로 테스트한다. `FakeClaudeMain`을 `.cmd` 래퍼로 감싸 실행하므로 비용이 들지 않는다. 표준 입력, 인자 전달, 작업 폴더, 타임아웃 때 자식 프로세스 종료를 확인한다.
  - 실제 claude 확인(`RealClaudeCheckTest`, `HARNESS_REAL_CLAUDE=1`일 때만 실행): haiku 4회, 약 $0.014. 결과는 0008의 "확인 결과"에 있다.
    - 표준 입력으로 프롬프트를 받는다.
    - `--disallowedTools Bash`가 허용 패턴보다 우선한다. 그래서 `ToolPolicy`를 고쳤다. Bash 패턴이 없는 역할만 Bash를 금지한다.
    - 허용 목록 밖 쓰기 명령은 거부되고, 읽기 전용 명령(`whoami`)은 통과한다.
  - 넘긴 프롬프트는 `.harness/logs/c{N}-{role}.prompt.md`로 남긴다. 스모크 테스트에서 `{{...}}` 잔존 검사에 쓴다.
  - `runInteractive`(부트스트랩)는 10단계에서 구현한다. 지금은 `UnsupportedOperationException`이다.

## 다음 할 일 (순서대로)
1. **구현**: `DESIGN.md` 8절의 11단계를 따른다. 11단계는 스모크 테스트이고, 0007의 비용 보정도 이 단계에서 한다.
   - 다음: 7단계. `PromptRenderer`(`PromptProvider` 구현)를 만들고, 프롬프트를 복사·수정한다(아래 변경 목록). 그 뒤 `Main`에서 루프를 연결한다.
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

## 10단계에서 검토할 것
- **Bash 허용 목록 훅**: 6단계 확인에서 읽기 전용 명령(`whoami`)이 허용 목록 밖인데도 실행됐다(0008 확인 결과). C2 위험 명령 차단 훅과 같은 PreToolUse 훅이므로 함께 만든다.
  - 동작: 허용 패턴에 없는 Bash 명령은 거부한다.
  - 먼저 확인할 것(실제 claude, haiku 1~2회, 약 $0.005)
    - 자동 허용되는 읽기 전용 명령에도 훅이 호출되는지
    - `--settings`로 역할별 훅 설정을 넘길 수 있는지
  - 주의 1: `;`, `&&`, `|`, `$(...)`, 백틱, `>`가 든 명령은 무조건 거부한다. 앞부분만 비교하면 `echo ok && rm -rf src`가 통과한다. 프롬프트에 "명령은 하나씩 실행한다"를 넣는다.
  - 주의 2: 역할마다 허용 목록이 다르므로 하네스가 역할별 설정 파일을 만들어 넘긴다.
  - 주의 3: Windows 실행 방식. Java 클래스(예: `harness.hook.BashGuard`)로 만들면 JUnit으로 테스트할 수 있지만, 도구 호출마다 JVM이 떠서 0.3~0.5초 느려진다.
  - 급하지 않다. 쓰기 명령은 이미 막힌다. 10단계에서 미룰지 사용자가 정한다.

## 미확인 항목
`IMPROVEMENTS.md` 6절을 본다. 남은 것은 두 가지다.
- 사용량 한도 도달 시 출력 형태: 재현할 수 없어서, 처음 발생할 때 확인한다.
- 비용 보정: 스모크 테스트로 한다(0011). Pro 한도를 다 쓴 상태여야 비교가 된다.

## 아직 정하지 않은 것
- 첫 대상 프로젝트(0004). 하네스는 특정 프로젝트를 가정하지 않고 `harness.yml`로 분리한다.
