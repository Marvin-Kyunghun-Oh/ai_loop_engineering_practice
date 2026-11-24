# STATUS

- 갱신: 2026-11-24
- 단계: **구현 완료, 실제 대상 프로젝트 대기** (DESIGN 8절 1~11단계 완료. 훅 두 개는 보류 유지. 테스트 175개 통과(실제 claude 확인 3개는 평소 건너뜀), 스모크 테스트 통과)

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
- **7단계 완료**: `PromptRenderer`, `PromptException`, 프롬프트 4개(`src/main/resources/prompts/`), `Main` 루프 연결. `PromptRendererTest` 17개.
  - 아래 "프롬프트 변경 목록" 16건을 모두 반영했다. 테스트가 프롬프트에 `uv`, `run.py`, JOURNAL 쓰기 지시가 남지 않았는지 검사한다.
  - `Main`은 시작할 때 세 역할의 프롬프트를 한 번씩 만들어 본다. 모르는 변수가 있으면 비용을 쓰기 전에 종료 코드 2로 멈춘다. `harness.yml`이 없을 때 종료 코드 2로 멈추는 것은 직접 실행해 확인했다.
  - 프롬프트를 쓰며 정한 형식 세부 (`DESIGN.md` 4.2·4.3·5.6에 반영)
    1. REVIEW 블록 다음에 `평가 대상: T8r · 사이클 35 · {시각}` 줄을 둔다. planner가 BACKLOG에 출처 사이클을 적을 때 쓴다. 메모가 없으면 `메모: 없음`.
    2. BACKLOG에 같은 항목 ID·사이클 줄이 있으면 다시 적지 않는다. 사이클이 중간에 멈추면 planner가 같은 REVIEW를 다시 읽기 때문이다.
    3. 마일스톤 마감: 마지막 섹션이 전부 `[x]`이고 REVIEW가 FAIL이 아닐 때. BACKLOG 항목에는 `(BACKLOG: M{n} 마감)`을 붙인다. 이것으로 마지막 마일스톤에서 두 번 고르는 것을 막는다.
    4. TASKS.md에는 진행 중인 마일스톤까지만 섹션을 만든다. 그래서 아카이브 조건("다음 섹션에 항목이 있다")과 마감 처리 시점이 맞물린다.
    5. `{{cycle.now}}`는 사이클 시작 시각이 아니라 프롬프트를 만든 시각이다.
    6. 에이전트가 쓰는 HALT도 4.7의 네 줄 형식을 따르게 했다. generator·evaluator에는 "명령은 하나씩 실행한다"를 넣었다(10단계 훅 메모의 주의 1).
    7. 평가자는 변이를 acceptance에 명시된 것만 한다. 지금 권한(테스트 명령만, `docs/**`만 편집)으로는 변이 검증을 할 수 없으므로, 못 하면 "변이 검증 불가"로 적게 했다.
- **8단계 완료**: `decision` 패키지의 `DecisionResolver`(v1 `resolve_decisions` 포팅). `DecisionResolverTest` 10개, `HarnessTest` 2개. 사이클 끝(evaluator 뒤)에서 호출한다.
  - v1과 다른 점 두 가지. 사용자 확인이 필요하면 되돌린다.
    1. 선택 파일의 라벨이 비어 있으면(`선택:`만 있음) 미기록으로 본다. v1은 빈 라벨끼리 "합의"로 봤다.
    2. 한 주제에서 HALT를 쓰면 나머지 주제는 판정하지 않는다. v1은 계속 봤다.
  - 합의 불발 HALT는 4.7의 네 줄 형식이고, `상세`에 planner·evaluator의 선택 전문을 담는다. 에이전트가 쓴 HALT와 같이 카운터를 저장한다(v1과 같음).
- **9단계 완료**: `review`(`ReviewParser`, `ReviewBlock`, `ReviewRecord`, `ReviewStore`), `archive`(`TaskArchiver`). 새 테스트 27개(`ReviewParserTest` 7, `ReviewStoreTest` 5, `TaskArchiverTest` 11, `HarnessTest` 4).
  - 연결: evaluator가 성공하면 REVIEW.md 블록을 읽어 `.harness/reviews.csv`에 저장하고 JOURNAL 줄 끝에 판정을 붙인다. 사이클 시작 때 `TaskArchiver`로 아카이브한다(DONE·CURRENT 삭제 직후, planner 실행 전).
  - 구현하며 정한 동작 (`DESIGN.md` 4.4에 반영). 사용자 확인이 필요하면 되돌린다.
    1. **지난 REVIEW 방어**: REVIEW의 `평가 대상:` 줄이 이번 항목 ID·사이클과 다르면(또는 줄이 없으면) 기록하지 않고 콘솔에 경고만 한다. HALT하지 않는다. evaluator가 REVIEW를 새로 쓰지 않았을 때 지난 판정을 이번 것으로 착각하지 않게 하기 위해서다. 대신 평가 대상 줄을 빼먹으면 그 항목은 요약 줄에 `-`로 남는다. 스모크 테스트에서 evaluator가 이 줄을 잘 쓰는지 본다.
    2. **reviews.csv**: `task_id,cycle,verdict,key_decision`. 같은 항목을 다시 평가하면 줄이 늘고 마지막 줄이 이긴다. 쉼표·큰따옴표는 큰따옴표로 감싼다. 깨진 줄은 USAGE.csv처럼 예외를 던진다.
    3. **요약 줄 판별**: 항목 줄 하나뿐이고 `상세: archive/`가 든 항목을 이미 옮긴 것으로 본다. 그래서 반복 호출해도 결과가 같다. 이미 옮긴 섹션에 새 완료 항목이 생기면 그 항목만 옮긴다.
    4. 항목 ID가 없는 항목(`- [x] 설정 로더`)이 있거나, `## M{n}.` 형식이 아닌 `##` 섹션은 옮기지 않는다.
    5. archive 파일은 `docs/archive/TASKS-M{n}.md`. 새 파일은 `# TASKS-M{n}.md` 제목과 `## M{n}. 제목` 아래에 항목 상세를 쓰고, 이미 있으면 뒤에 덧붙인다. archive를 먼저 쓰고 TASKS.md를 고친다. 그 사이에 멈추면 같은 항목이 archive에 두 번 들어갈 수 있다(손실은 없다).
    6. CRLF/LF와 끝 줄바꿈 유무는 입력을 따른다.
  - REVIEW 메모를 BACKLOG에 옮기는 일은 planner의 몫이라 하네스는 읽지 않는다.

- **11단계 완료**: 스모크 테스트를 실제 claude(haiku)로 실행했다(2026-11-24). 2분 22초, 약 $0.046(실행 6회, 에이전트당 $0.006~0.009).
  - 배관 검사 10개 모두 통과. 사이클 1에서 T1 FAIL(5/9), 사이클 2에서 PASS(9/12).
  - evaluator가 `평가 대상:` 줄을 잘 써서 판정이 `reviews.csv`에 저장됐다.
  - 허용 목록 밖 명령(`python3 -c ...`)이 거부됐다. generator는 우회하지 않고 BLOCKED로 보고했고, planner가 확인 방법을 unittest로 바꿨다.
  - 훅(0013, 0014)은 보류를 유지하기로 사용자가 정했다.
  - 0007 비용 보정은 하지 못했다. 하네스 합계 $0.0464를 Pro 한도 사용량과 비교해야 하는데, 한도를 다 쓴 상태가 필요하다.

- **문서 최신화 완료**: `README.md`를 새로 썼다(1년 뒤 읽는 순서, 사용법, 폴더 설명, 메서드 이름이 든 실행 흐름). `CLAUDE.md`에 README 순서, 명령어, 유료 실행 승인 규칙, 훅 보류를 반영했다. `DESIGN.md`의 없는 `CycleRunner`는 `Harness.runCycle()`로 고쳤다.

## 다음 할 일 (순서대로)
1. **Bootstrap 실제 확인**: PRD 없이 처음 실행할 때 세션이 뜨고 역할 지시(`--append-system-prompt-file`)가 적용되는지 본다. 안 되면 `--append-system-prompt <본문>`으로 바꾼다.
2. **실제 대상 프로젝트 실행**: 대상 프로젝트가 정해지면(0004) 돌린다.
3. **0007 비용 보정**: Pro 한도를 다 쓴 상태에서 하네스 합계와 비교한다.
4. 사용자 확인이 남은 동작: 8단계의 v1과 다른 점 2가지, 9단계 구현 동작, 비용을 모르는 실행을 누적에 더하지 않는 처리(5단계 4번).
5. 훅(0013, 0014)은 보류. 실제 프로젝트에서 위험 명령이나 허용 목록 우회가 문제가 되면 다시 판단한다.

## 프롬프트 변경 목록 (7단계에서 반영 완료, 기록용)

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

## 10단계 구현 메모
- **Bootstrap 완료**(`Bootstrap`, `ProcessClaudeRunner.runInteractive`, `PromptRenderer.bootstrapPrompt`). 테스트 5개 추가.
  - `Harness.run()`이 PRD가 없을 때 호출한다. 끝나도 PRD가 없으면 종료 코드 1.
  - 명령줄: `claude --model {planner 모델} --append-system-prompt-file {.harness/logs/bootstrap.prompt.md} --allowedTools ... --disallowedTools Bash`. 입출력은 콘솔을 그대로 쓴다(`inheritIO`). 시간·예산 상한은 없다.
  - **실제 claude로는 아직 확인하지 않았다.** `--append-system-prompt-file` 옵션이 `claude --help` 본문에는 `--append-system-prompt[-file]`로만 나온다. 사람이 대화하는 세션이라 자동으로 확인할 수 없으니, 처음 PRD 없이 실행할 때 세션이 뜨고 역할 지시가 적용되는지 본다. 안 되면 v1처럼 `--append-system-prompt <본문>`으로 바꾼다.
  - 부트스트랩은 JOURNAL에 줄을 남기지 않는다(결과 JSON이 없어 0009의 형식을 채울 수 없다). 비용도 USAGE.csv에 잡히지 않는다(DESIGN 4.5).

## 11단계 준비 (완료, 실행도 끝남)
- **실행**: `$env:HARNESS_SMOKE = "1"; ./gradlew smokeTest`. 환경 변수가 없으면 유료 테스트(`SmokeTest`)는 건너뛰고, 무료 검사(`SmokeChecksTest` 8개)만 돈다. `test`·`check`에는 연결하지 않았다.
- **샘플 프로젝트**: `src/smokeTest/resources/sample-project/`. PRD는 `reverse()` 함수 하나(Python, 표준 라이브러리, `python3 -m unittest`). 세 역할 haiku, `max_iterations: 2`, `max_total_usd: 1`, `max_agent_usd: 0.5`. 테스트 명령은 수 초 안에 끝난다.
  - 언어는 Python으로 정했다(DESIGN 7.1의 "구체적인 구성은 구현 단계에서"). Gradle 프로젝트는 매 호출마다 데몬을 띄워 느리고 래퍼 복사가 필요하다. 에이전트가 만든 코드의 품질은 확인 대상이 아니다.
  - 허용 Bash: `python3 -m unittest`, `python3 -m compileall`.
- **동작**: 샘플을 `build/smoke-run/`에 복사해 `Main.run()`으로 돌린다. 끝나면 `build/smoke-run/`에 `docs/`, `.harness/logs/`, `console.log`, `REPORT.md`가 남는다. 이전 실행 결과는 지우고 시작한다.
- **검사 10개**(`SmokeChecks`): 정상 종료, 3역할 실행, `CURRENT` 형식, TASKS 형식, REVIEW 블록과 reviews.csv, USAGE.csv, JOURNAL 형식, 원본 로그, 프롬프트 `{{` 잔존, 허용 명령 거부 여부. 검사는 하나가 실패해도 모두 돌려 한 번에 보고한다.
- **한계**: 허용 목록 밖 명령이 실제로 막히는지는 에이전트가 그런 명령을 시도해야 알 수 있다. 시도하지 않았으면 기록이 없다고 리포트에 적는다.
- `Main.run(Path, PrintStream)`을 패키지 공개로 빼서 스모크 테스트가 실제와 같은 조립을 쓴다.

## 보류한 훅 (0013, 0014): 스모크 테스트 뒤에 다시 판단
- **Bash 허용 목록 훅**(0013으로 11단계 뒤로 미룸): 6단계 확인에서 읽기 전용 명령(`whoami`)이 허용 목록 밖인데도 실행됐다(0008 확인 결과). C2 위험 명령 차단 훅과 같은 PreToolUse 훅이므로 함께 만든다.
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
