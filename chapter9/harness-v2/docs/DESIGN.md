# harness-v2 설계

`IMPROVEMENTS.md`의 개선 항목과 `decisions/` 0001~0010을 Java 코드 구조로 옮긴 설계다.
v1(`chapter9/harness/src/harness/run.py`)의 동작은 유지하고, 결함을 고친다.
설계 세부는 제안한 기본값이다. 사용자 검토 후 바뀔 수 있다.

## 1. 한눈에 보기

```
Main ─▶ ConfigLoader ─▶ HarnessConfig (harness.yml)
  │
  └▶ Harness (메인 루프)
       ├─ Bootstrap            PRD가 없으면 대화형 planner 실행
       ├─ TaskArchiver         끝난 마일스톤의 작업 지시를 archive로 이동 (0005)
       ├─ CycleRunner          planner → generator → evaluator
       │    ├─ PromptRenderer  프롬프트의 {{변수}} 치환 (D3)
       │    ├─ ToolPolicy      역할별 허용·금지 도구 (0008)
       │    ├─ CostLedger      실행 전 예산 검사, USAGE.csv 기록 (0007)
       │    ├─ ClaudeRunner    claude -p 실행 → AgentResult (인터페이스)
       │    └─ JournalWriter   JOURNAL 한 줄 기록 (0009)
       ├─ DecisionResolver     블라인드 결정 합의 (v1 resolve_decisions 포팅)
       └─ ProjectFiles         docs/ 아래 파일 경로와 DONE/HALT/CURRENT 읽기·쓰기
```

설계의 핵심은 두 가지다.
- **`ClaudeRunner`를 인터페이스로 둔다.** 실제 구현은 `ProcessClaudeRunner`(`ProcessBuilder`)다. 테스트에서는 `FakeClaudeRunner`가 미리 정한 `AgentResult`를 돌려준다. 그래서 크레딧을 쓰지 않고 루프 전체를 JUnit으로 검증할 수 있다(D4).
- **판단은 에이전트, 순서·기록·상한은 하네스가 맡는다.**
  - 에이전트가 하는 일: 계획, 구현, 채점
  - 하네스가 하는 일: 실행 순서, 비용 기록, JOURNAL, 아카이브, 예산 차단, 실패 처리

## 2. 디렉터리 구조

### 하네스 프로젝트 (`chapter9/harness-v2`)
```
harness-v2/
├── CLAUDE.md
├── build.gradle            # application 플러그인, Jackson, JUnit 5
├── settings.gradle
├── docs/                   # 이 문서들
├── src/main/java/harness/
│   ├── Main.java
│   ├── Harness.java
│   ├── CycleRunner.java
│   ├── Bootstrap.java
│   ├── config/   HarnessConfig.java, ConfigLoader.java
│   ├── claude/   ClaudeRunner.java, ProcessClaudeRunner.java,
│   │             AgentRequest.java, AgentResult.java, Outcome.java, ResultParser.java
│   ├── cost/     CostLedger.java, UsageRecord.java
│   ├── journal/  JournalWriter.java
│   ├── prompt/   PromptRenderer.java
│   ├── policy/   ToolPolicy.java, Role.java
│   ├── state/    ProjectFiles.java
│   ├── decision/ DecisionResolver.java
│   └── archive/  TaskArchiver.java
├── src/main/resources/prompts/
│   └── planner.md, generator.md, evaluator.md, planner_bootstrap.md
├── src/test/
│   ├── java/harness/...    # 7절 단위 테스트
│   └── resources/claude-result/   # 실제 CLI 출력 샘플 (확인함)
└── src/smokeTest/
    ├── java/harness/...    # 7.1 스모크 테스트
    └── resources/sample-project/  # 작은 PRD와 harness.yml
```

### 대상 프로젝트 (하네스가 일하는 곳)
```
<project>/
├── harness.yml             # 프로젝트별 설정 (3절)
├── docs/
│   ├── PRD.md  PLAN.md  TASKS.md  IMPL.md  REVIEW.md  JOURNAL.md
│   ├── BACKLOG.md          # REVIEW 메모 보관 (0010)
│   ├── CURRENT             # 이번 사이클 항목 ID (4.1)
│   ├── USAGE.csv           # 비용·토큰 기록 (0007)
│   ├── .cycle_count  DONE  HALT
│   ├── decisions/          # planner·evaluator 블라인드 합의 (v1과 동일)
│   └── archive/            # TASKS-M{n}.md, DECISIONS-retired.md (0005)
└── .harness/logs/          # 에이전트 원본 결과 JSON (D2)
```
- 원본 로그를 `docs/` 밖(`.harness/logs/`)에 두는 이유가 있다. 에이전트가 `docs/`를 Glob으로 훑을 때 큰 JSON이 읽히지 않게 하기 위해서다.
- `.harness/`는 대상 프로젝트의 `.gitignore`에 넣기를 권장한다.

### 실행 방법
```
cd chapter9/harness-v2
./gradlew run --args="../projects/<project>"
```
`gradlew installDist` 후 `build/install/harness-v2/bin/harness-v2 <project>`로도 실행할 수 있다.

## 3. `harness.yml`

```yaml
claude:
  path: claude            # Windows는 자동으로 claude.cmd를 찾는다 (5.3)

models:
  planner: opus
  generator: sonnet
  # 테스트 실행·채점 역할. 비용 절감을 위해 sonnet으로 내렸다.
  # 꼼꼼한 검수가 필요하다면 opus로 변경하는 것을 추천한다.
  # (예: 보안·데이터 무결성이 중요한 프로젝트, sonnet 평가에서 놓친 결함이 반복될 때)
  evaluator: sonnet

limits:
  max_iterations: 50            # 한 번 실행에서 돌 사이클 수 (v1 MAX_ITERATIONS)
  max_total_usd: 38             # 누적 비용 상한 (0007)
  max_agent_usd: 5              # 에이전트 1회 → --max-budget-usd
  max_turns: null               # 선택. 예: { planner: 15, generator: 40, evaluator: 20 }
  agent_timeout_min: 30         # B2
  backlog_per_milestone: 2      # 0010
  max_consecutive_errors: 2     # B1. 실행 오류가 연속 N회면 HALT

commands:                       # 프롬프트의 {{commands.*}}로 치환 (D3)
  test: "./gradlew test"
  test_path: "./gradlew test --tests {path}"   # acceptance에 경로가 있을 때
  build: "./gradlew build"
  add_dependency: "build.gradle의 dependencies 블록에 추가한다"

permissions:                    # 0008. 역할별 Bash 허용 패턴
  generator_bash:
    - "Bash(./gradlew build:*)"
    - "Bash(./gradlew test:*)"
    - "Bash(git status:*)"
    - "Bash(git diff:*)"
  evaluator_bash:
    - "Bash(./gradlew test:*)"
```

- `ConfigLoader`가 `jackson-dataformat-yaml`로 읽어 `HarnessConfig` record로 만든다.
- 읽는 시점에 검증한다. 빠진 필수 키, 음수, 모르는 키는 키 이름을 담은 예외로 시작을 거부한다. v1 rss-wiki의 `config.py` 방식과 같다.
- 파일이 없으면 시작을 거부한다. 기본값으로 조용히 도는 것보다 명시적인 편이 안전하다.

## 4. 하네스가 기계적으로 읽고 쓰는 형식

에이전트(프롬프트)와 Java 코드가 같은 형식을 써야 하는 것들이다. 프롬프트 수정(STATUS 2번) 때 이 절을 그대로 따른다.

### 4.1 `docs/CURRENT` (D5)
planner가 이번 사이클 항목 ID 한 줄을 쓴다. 하네스·generator·evaluator가 읽는다.
```
T9a
```
- planner 실행 후 `CURRENT`가 없거나 비어 있으면, `DONE`이나 `HALT`가 없는 한 실행 오류로 본다. generator로 넘어가지 않는다.
- ID 형식은 `T` 뒤에 숫자, 그 뒤에 소문자가 붙을 수 있다(`^T\d+[a-z]*$`).

### 4.2 REVIEW.md의 기계 판독 줄 (0005, 0010)
evaluator가 REVIEW.md 맨 위에 다음 블록을 쓴다. 사람이 읽는 평가 표는 그 아래에 둔다.
```
판정: PASS 11/12
핵심 결정: 버리기 깊이는 태그별로 센다
메모:
- [결함] html_to_text가 짝 없는 끝 태그에서 깊이를 음수로 만들 수 있다
- [보강] 블록 태그 목록을 테스트 리터럴로 고정
```
- 블록은 파일의 **첫 줄**부터 시작한다. 앞에 제목이나 빈 줄을 두지 않는다.
- `판정:` 값은 `PASS`, `조건부`, `FAIL` 중 하나이고 그 뒤에 점수(`합계/만점`)가 온다.
- `핵심 결정:`은 없으면 `-`로 쓴다.
- 메모의 분류는 두 가지다. 메모가 없으면 `메모: 없음` 한 줄로 쓴다.
  - `[결함]`: 동작 오류, 경계 누락, 회귀 위험
  - `[보강]`: 테스트·문서·구조 개선
- 블록 다음 빈 줄 뒤에 `평가 대상: T8r · 사이클 35 · {시각}` 줄을 둔다. planner가 BACKLOG에 출처 항목 ID와 사이클을 적을 때 이 줄을 쓴다(7단계에서 정함).
- 하네스가 쓰는 곳
  - `핵심 결정:` → 아카이브 때 TASKS 요약 줄(4.4)
  - `판정:` → JOURNAL 줄 끝에 덧붙임

### 4.3 `docs/BACKLOG.md` (0010)
planner가 PASS·조건부 REVIEW의 메모를 옮겨 적는다.
```
- [결함] [T8r] html_to_text 짝 없는 끝 태그 깊이 (c35)
- [보강] [T8r] 블록 태그 목록 리터럴 고정 (c35)
```
- 출처 항목 ID와 사이클 번호를 함께 적는다. 같은 항목 ID·사이클의 줄이 이미 있으면 다시 적지 않는다. 사이클이 중간에 멈추면 planner가 같은 REVIEW를 다시 읽기 때문이다.
- 처리한 줄은 지우지 않는다. 줄 끝에 `→ T12`처럼 생성된 항목 ID를 붙인다.
- **마감 처리 (7단계에서 정함)**: TASKS.md의 마지막 마일스톤 섹션이 전부 `- [x]`이고 직전 REVIEW가 FAIL이 아니면 마감이다.
  - planner는 `→`가 없는 `[결함]` 줄을 최대 `backlog_per_milestone`개 골라 항목으로 만든다. 제목 끝에 `(BACKLOG: M{n} 마감)`을 붙인다.
  - 다음 마일스톤이 있으면 새 섹션 맨 앞에 넣는다. 마지막 마일스톤이면 그 섹션 끝에 넣는다.
  - 마지막 마일스톤에서 마감 처리를 두 번 하지 않도록, 그 섹션에 `(BACKLOG: M{n} 마감)` 항목이 이미 있으면 다시 고르지 않는다.
  - TASKS.md에는 진행 중인 마일스톤까지만 섹션을 만든다. 다음 섹션은 마감 때 만든다. 그래서 4.4의 아카이브 조건("그 뒤 섹션에 항목이 있다")이 "마감 처리를 마쳤다"와 같은 뜻이 된다.

### 4.4 TASKS.md와 아카이브 (0005)
- 마일스톤은 `## M{n}. 제목` 제목으로 구분한다(v1과 동일).
- **아카이브 조건**: 다음 두 가지를 모두 만족하는 마일스톤 섹션을 사이클 시작 시 아카이브한다.
  - 섹션 안의 항목이 전부 `- [x]`다.
  - **그 뒤 마일스톤 섹션에 항목이 1개 이상 있다.**

  두 번째 조건이 있는 이유가 있다. v1에서 M2는 항목이 전부 체크된 상태에서 planner가 T9a를 더 추가한 적이 있다. 일이 다음 마일스톤으로 넘어간 게 확실할 때만 옮겨야 한다. 마지막 마일스톤은 아카이브하지 않는다.
- **동작**
  1. 항목의 상세 줄(`- [x] T..` 아래 들여쓴 줄 전체)을 `docs/archive/TASKS-M{n}.md`로 옮긴다.
  2. TASKS.md에는 요약 한 줄만 남긴다.
     ```
     - [x] T8s. 버리기 깊이 태그별 분리 — PASS 11/12 · 결정: 깊이 태그별 · 상세: archive/TASKS-M2.md#T8s
     ```
     `판정`과 `결정`은 그 항목을 평가한 REVIEW의 4.2 블록에서 가져온다. 하네스는 항목 ID별 판정·핵심 결정을 `.harness/reviews.csv`에 매 사이클 저장해 두었다가 쓴다.
  - 저장 시점은 evaluator가 성공한 직후다. REVIEW의 `평가 대상:`이 이번 항목 ID·사이클과 같을 때만 저장한다(지난 REVIEW 방어). 다르면 경고만 하고 요약 줄에는 `-`가 남는다.
  - 이미 요약 줄이 된 항목(한 줄짜리, `상세: archive/` 포함)은 다시 옮기지 않는다. `## M{n}.` 형식이 아닌 섹션과 항목 ID가 없는 항목이 든 섹션은 옮기지 않는다.
- planner가 BACKLOG에서 고른 항목은 **다음 마일스톤 섹션의 맨 앞**에 넣는다(프롬프트 규칙). 이미 아카이브한 섹션은 다시 열지 않는다.

### 4.5 `docs/USAGE.csv` (0007)
```
timestamp,cycle,role,model,subtype,cost_usd,input,cache_creation,cache_read,output,turns,duration_ms
2026-11-24T12:26:46+09:00,12,generator,sonnet,success,1.20,88000,120000,3100000,41000,23,184000
```
- 하네스가 시작할 때 이 파일의 `cost_usd` 합으로 누적 비용을 복원한다.
- **부트스트랩 비용은 집계에서 빠진다.** 부트스트랩은 대화형이라 결과 JSON이 없다. 그래서 이 대화의 비용은 `USAGE.csv`와 누적 상한($38)에 잡히지 않는다.
  - 사람이 직접 대화하는 동안이라 폭주 위험은 없다. 입력을 기다리는 동안에는 토큰이 쓰이지 않는다.
  - 다만 총 사용량 집계에서는 빠진다.
  - 세션 비용을 가져올 방법이 있는지 구현 시 확인한다(9절). 없으면 이대로 둔다.
- 참고: 부트스트랩은 블로킹 호출이다. PRD가 없으면 사용자가 대화를 마칠 때까지 하네스가 기다리고, 그래도 PRD가 없으면 종료한다. 사이클이 PRD를 기다리며 도는 일은 없다(v1 `run.py:76-81`과 같음).

### 4.6 JOURNAL 줄 (0009)
```
- 2026-11-24T12:26:46+09:00 [c12] generator: T7b 완료 (258 passed) · $1.20 · success
- 2026-11-24T12:29:10+09:00 [c12] evaluator: T7b PASS 12/12 · $0.80 · success · PASS 12/12
- 2026-11-24T12:40:02+09:00 [c13] generator: Reached maximum budget ($5) · $5.31 · error_max_budget_usd
```
- 요약은 결과 JSON의 `result` 첫 줄에서 가져온다. `result`가 `null`이면(오류) `errors[0]`을 쓴다.
- 200자를 넘으면 자른다.

### 4.7 `docs/HALT`
```
사유: 예산 소진
상세: 누적 $34.10 + 에이전트 1회 상한 $5.00 > 상한 $38.00
사이클: 15 / 역할: generator (실행 전)
재개: 이 파일을 지우고 harness.yml의 limits.max_total_usd를 올린다
```
- 모든 HALT는 `사유`, `상세`, `사이클`, `재개` 네 줄을 쓴다. v1은 사유만 적었다.

## 5. 주요 클래스

### 5.1 `ClaudeRunner`와 결과 모델
```java
public interface ClaudeRunner {
    AgentResult run(AgentRequest request);          // 대화형이 아닌 실행 (-p)
    void runInteractive(AgentRequest request);      // 부트스트랩 전용
}

public record AgentRequest(
    Role role, String prompt, String model,
    List<String> allowedTools, List<String> disallowedTools,
    boolean acceptEdits, BigDecimal maxBudgetUsd, Integer maxTurns,
    Duration timeout, Path workDir, Path rawLogFile) {}

public record AgentResult(
    Outcome outcome, String subtype, BigDecimal costUsd, TokenUsage usage,
    int numTurns, long durationMs, String summary, List<String> errors) {}

public enum Outcome { SUCCESS, BUDGET_LIMIT, TURN_LIMIT, INVALID_RESULT, ERROR, TIMEOUT }
```
- `ResultParser`는 결과 JSON을 `AgentResult`로 바꾼다. 판정 규칙(B1)은 다음과 같다.

  | 조건 | Outcome |
  |---|---|
  | `subtype == "success"` 이고 `is_error == false` | `SUCCESS` |
  | `subtype == "error_max_budget_usd"` | `BUDGET_LIMIT` |
  | `subtype == "error_max_turns"` | `TURN_LIMIT` |
  | JSON 객체이지만 필수 필드가 없거나 `type != "result"` | `INVALID_RESULT` (즉시 HALT, 0012) |
  | 그 밖의 `error_*`, `api_error_status != null`, JSON이 없거나 파싱 실패 | `ERROR` |
  | 프로세스가 타임아웃으로 종료됨 | `TIMEOUT` (Runner가 직접 만듦) |

- 필수 필드는 `type`, `subtype`, `is_error`, `total_cost_usd`, `usage`다. 하나라도 없으면 `INVALID_RESULT`로 처리한다. 비용을 0으로 처리하지 않는다(0007의 "필드 누락 처리", 0012).
- 토큰은 `modelUsage`의 모델별 값을 합산한다. 없으면 `usage`를 쓴다(0012).
- 종료 코드는 판정에 쓰지 않는다. 상한 도달과 오류가 모두 `1`이기 때문이다(확인함).

### 5.2 `ProcessClaudeRunner`
- `ProcessBuilder`로 `claude -p --output-format json --model ... --allowedTools ... --disallowedTools ... --max-budget-usd ... [--max-turns ...] [--permission-mode acceptEdits]`를 실행한다.
- **프롬프트는 명령줄 인자가 아니라 표준 입력으로 넘긴다.** Windows에서 `claude.cmd`는 `cmd.exe`를 거치는데, `cmd.exe`의 명령줄 길이 한도는 약 8,000자다. 템플릿을 치환한 프롬프트가 이 한도를 넘을 수 있다. `claude -p`가 표준 입력에서 프롬프트를 읽는지는 구현 첫 단계에서 확인한다. 안 되면 인자 방식으로 두고 길이를 검사한다.
- 6단계 확인: 표준 입력으로 받는다(9,300자 프롬프트로 확인). 넘긴 프롬프트는 `.harness/logs/c{N}-{role}.prompt.md`에 남는다. 스모크 테스트에서 치환되지 않은 `{{...}}`를 이 파일로 검사한다.
- 표준 출력은 전부 `rawLogFile`(`.harness/logs/c{N}-{role}.json`)에 저장한 뒤 파싱한다(D2). 표준 에러는 콘솔로 흘린다.
- 결과 JSON이 없거나 깨졌을 때만 요약에 종료 코드를 덧붙인다. 원인을 찾는 단서로 쓴다.
- **타임아웃**: `process.waitFor(timeout)`가 시간을 넘기면 `process.descendants()`까지 모두 `destroyForcibly()`하고 `TIMEOUT`을 반환한다(B2).

### 5.3 실행 파일 찾기 (Windows)
- `claude.path`가 `claude`이고 OS가 Windows이면, `PATH`에서 `claude.cmd`, `claude.exe`, `claude` 순으로 찾는다.
  - 셸과 같은 순서로 찾는다. PATH 앞쪽 폴더가 우선이고, 같은 폴더 안에서는 위 확장자 순서를 따른다.
  - 참고: 이 PC의 claude는 네이티브 설치판 `claude.exe`다. `.cmd` 경로는 테스트의 가짜 실행기로 확인한다. 괄호·별표·공백이 든 인자가 cmd.exe를 거쳐도 그대로 전달된다.
- v1은 이 문제로 실패한 적이 있다(커밋 `0c8e5d8`). 그래서 찾는 로직을 별도 메서드로 두고 테스트한다.

### 5.4 `CostLedger`
```java
boolean canAfford(BigDecimal maxAgentUsd);   // 누적 + maxAgent <= maxTotal
void record(int cycle, Role role, String model, AgentResult r);  // USAGE.csv 추가 + 누적 갱신
BigDecimal total();
```
- 금액은 `BigDecimal`로 다룬다. double 누적 오차를 피하기 위해서다.

### 5.5 `ToolPolicy` (0008)

| 역할 | allowedTools | 비고 |
|---|---|---|
| planner | `Read Glob Grep Edit(docs/**) Write(docs/**)` | v1과 동일 |
| generator | `Read Write Edit Glob Grep` + `permissions.generator_bash` | `acceptEdits` |
| evaluator | `Read Glob Grep Edit(docs/**) Write(docs/**)` + `permissions.evaluator_bash` | |

- 금지 목록은 Bash 허용 패턴이 없는 역할(planner, 그리고 `evaluator_bash: []`일 때 evaluator)에만 `Bash`를 넣는다. 패턴이 있는 역할은 허용 목록만 넘긴다.
  - 6단계 확인 결과(0008): `--disallowedTools Bash`가 허용 패턴보다 우선해 허용 명령까지 막는다.
  - 허용 목록만 주면 목록 밖 쓰기 명령은 거부되고 `permission_denials`에 남는다. 다만 읽기 전용 명령은 통과한다. 그래서 Bash가 아예 없어야 하는 역할은 금지 목록으로 Bash 자체를 뺀다.
- 변이 검증용 임시 복사본 쓰기 허용(0008)은 첫 구현 범위에서 뺀다. 프롬프트에서 "변이 검증은 acceptance에 명시된 것만"으로 줄였기 때문이다(A3). 필요해지면 추가한다.

### 5.6 `PromptRenderer` (D3)
- `{{a.b}}` 형태의 변수를 `HarnessConfig`와 실행 맥락 값으로 치환한다.
- **모르는 변수가 있으면 예외**를 던진다. 치환되지 않은 `{{...}}`가 에이전트에게 그대로 가는 일을 막는다.
- 변수 목록

  | 변수 | 값 |
  |---|---|
  | `{{commands.test}}`, `{{commands.test_path}}`, `{{commands.build}}`, `{{commands.add_dependency}}` | `harness.yml` |
  | `{{limits.backlog_per_milestone}}` | `harness.yml` |
  | `{{cycle.number}}` | 현재 사이클 번호 |
  | `{{cycle.now}}` | 프롬프트를 만든 시각(에이전트 실행 직전, ISO 8601). 에이전트가 문서에 날짜를 적을 때 쓴다 |

- 7단계 구현
  - 모르는 변수는 모아서 한 번에 알려 준다. 닫히지 않은 `{{`도 예외다. 중괄호 하나(`{path}`, `{주제}`)는 변수가 아니다.
  - `Main`이 시작할 때 세 역할의 프롬프트를 한 번씩 만들어 본다(`checkTemplates`). 비용을 쓰기 전에 템플릿 오류를 찾기 위해서다.
  - `{{cycle.now}}`는 원래 "사이클 시작 시각"이었다. `PromptProvider`가 역할마다 따로 불리므로 실행 직전 시각으로 바꿨다. 에이전트가 문서에 적는 날짜로는 이쪽이 더 정확하다.
  - `planner_bootstrap.md`에는 변수가 없다. 10단계에서 `Bootstrap`이 같은 방식으로 읽는다.

### 5.7 `DecisionResolver`
- v1 `resolve_decisions`(`run.py:118-149`)를 그대로 옮긴다.
  - `{주제}.planner.md`와 `{주제}.evaluator.md`의 첫 줄 `선택: {라벨}`을 비교한다.
  - 같으면 `합의: {라벨} (시도 N회)`를 추가한다.
  - 다르면 `합의 불발` 재시도를 표시한다.
  - 3회 불발이면 HALT한다.
  - 판정 후 선택 파일 두 개를 지운다.
- 동작을 바꾸지 않고 테스트만 추가한다.

### 5.8 `TaskArchiver`
- 4.4의 규칙만 구현한다. 입력은 TASKS.md 문자열과 `reviews.csv`, 출력은 새 TASKS.md 문자열과 아카이브에 추가할 문자열이다. 파일 입출력은 호출하는 쪽이 한다.
- 순수 함수에 가깝게 만들어 테스트하기 쉽게 한다.

## 6. 메인 루프

```
main(projectDir):
  config = ConfigLoader.load(projectDir/harness.yml)
  files  = ProjectFiles(projectDir)
  ledger = CostLedger.load(files.usageCsv(), config.limits())
  if not files.prd().exists(): Bootstrap.run()        # 대화형, 끝나도 PRD 없으면 종료
  start = files.readCycleCount()

  for i in 1..max_iterations:
    cycle = start + i
    files.deleteDone()                                  # v1과 동일: 매 사이클 종료 재판정
    TaskArchiver.archiveClosedMilestones(files)         # 0005

    r = runAgent(PLANNER)                               # 실패·HALT면 return
    if files.done(): save(cycle); return 0
    if files.halt(): save(cycle); return 1
    if files.current() is empty: halt("planner가 CURRENT를 쓰지 않음")

    r = runAgent(GENERATOR)
    r = runAgent(EVALUATOR)
    files.saveReviewVerdict(currentId)                  # 4.2 → .harness/reviews.csv

    DecisionResolver.resolve(files)
    if files.halt(): save(cycle); return 1
    save(cycle)                                         # 정상 완료한 사이클만 카운트 (B1)

runAgent(role):
  if not ledger.canAfford(max_agent_usd): halt("예산 소진"); stop
  prompt = PromptRenderer.render(role)
  result = runner.run(request(role, prompt))
  ledger.record(cycle, role, model, result)             # 오류여도 비용은 기록
  journal.append(cycle, role, result)
  switch result.outcome:
    SUCCESS                     → 계속
    BUDGET_LIMIT, TURN_LIMIT    → 이 사이클 중단, 다음 사이클로. 같은 CURRENT 항목에서 2회 연속이면 HALT
    INVALID_RESULT              → 즉시 HALT(원본 로그 경로 포함) (0012)
    ERROR, TIMEOUT              → 이 사이클 중단. 연속 max_consecutive_errors회면 HALT(원본 로그 경로 포함)
```

- 상한 도달과 오류로 이 사이클을 중단한 경우 `.cycle_count`를 올리지 않는다.
- 다음 사이클은 같은 번호로 다시 시작한다. 그래서 JOURNAL에 같은 `[c12]`가 두 번 나올 수 있다. 이건 의도한 동작이다.
- 구현하며 정한 동작 (5단계, 사용자 확인 2026-11-24)
  1. 사이클 시작 때 `DONE`과 함께 `CURRENT`도 지운다. 지우지 않으면 planner가 새로 쓰지 않아도 지난 항목으로 generator가 돈다.
  2. 시작할 때 `HALT`가 있으면 아무것도 실행하지 않는다. v1은 planner를 한 번 돌린 뒤에야 멈췄다.
  3. HALT 후 카운터 처리
     - 에이전트가 쓴 HALT는 카운터를 저장한다(v1과 같음).
     - 하네스가 쓴 HALT(예산, 오류 연속, CURRENT, 결과 형식 오류)는 저장하지 않는다.
  4. 비용을 모르는 실행(TIMEOUT, 결과 JSON 없음)은 누적에 더하지 않는다. 오류가 연속되면 `max_consecutive_errors`회 만에 HALT하므로 놓치는 금액은 작다.
  5. `CURRENT`의 값이 4.1 형식이 아니면 HALT한다.
  6. 상한 도달 반복을 판단하는 키는 `CURRENT` 항목 ID다. planner처럼 항목이 정해지기 전이면 역할 이름을 쓴다.

## 7. 테스트 (JUnit 5)

| 대상 | 확인할 것 |
|---|---|
| `ResultParser` | 샘플 3개(`success`, `error-max-budget-usd`, `error-max-turns`) → Outcome·비용·토큰. 필수 필드 누락 → `ERROR`. 깨진 JSON → `ERROR` |
| `ConfigLoader` | 정상 / 필수 키 누락 / 음수 / 모르는 키 / 파일 없음 |
| `CostLedger` | 빈 CSV, 기존 CSV에서 누적 복원, `canAfford` 경계(같으면 허용, 1센트 넘으면 거부) |
| `PromptRenderer` | 치환 / 모르는 변수 → 예외 / 중첩 키 |
| `ToolPolicy` | 역할별 목록이 `harness.yml`과 일치 |
| `DecisionResolver` | 합의 / 불발 1·2회 / 3회 → HALT / 한쪽만 기록 → 대기 / 형식 오류 → 미기록 취급 |
| `TaskArchiver` | 조건 미충족(다음 섹션 비어 있음) → 그대로 / 충족 → 요약 줄·아카이브 내용 / 판정 정보 없음 → `-` |
| `JournalWriter` | `result` 있음 / `null` → `errors[0]` / 200자 자르기 |
| `Harness` (FakeClaudeRunner) | 정상 사이클 3역할 순서, `DONE`/`HALT` 종료, 예산 사전 차단, 상한 도달 시 카운터 유지, 오류 연속 → HALT, `CURRENT` 누락 → HALT |
| 실행 파일 찾기 | Windows에서 `claude.cmd` 우선 (OS·PATH 주입) |

- 단위 테스트는 실제 `claude`를 부르지 않는다. 비용 없이 빌드할 때마다 돈다.
- 실제 연동은 7.1의 스모크 테스트로 따로 확인한다.

### 7.1 스모크 테스트 (실제 `claude`, 수동 실행, [0011](decisions/0011-smoke-test.md))
단위 테스트는 "에이전트가 형식을 지켰다"고 가정한다. 그래서 가장 불확실한 부분은 실제로 돌려야만 확인된다. 그 부분은 프롬프트와 하네스 사이의 배관이다.

- **실행**: `./gradlew smokeTest`. `test`나 `check`에 연결하지 않는다. 사람이 필요할 때만 실행하며, 실행하면 비용이 든다.
- **샘플 프로젝트**: `src/smokeTest/resources/sample-project/`
  - `docs/PRD.md`: 할 일 1~2개짜리 아주 작은 PRD. 예: "문자열을 뒤집는 `StringUtils.reverse`와 그 테스트". PRD가 있으므로 부트스트랩은 건너뛴다.
  - `harness.yml`: 세 역할 모두 haiku, `max_total_usd: 1`, `max_agent_usd: 0.5`, `max_iterations: 2`
  - 빌드·테스트 명령은 수 초 안에 끝나는 최소 구성으로 한다. 구체적인 구성은 구현 단계에서 정한다.
- **흐름**
  1. 샘플 프로젝트를 임시 폴더로 복사한다. 원본은 항상 깨끗하게 남는다.
  2. `ProcessClaudeRunner`로 하네스를 실행한다.
  3. 결과 파일의 형식을 검사한다.
  4. 리포트를 출력한다.
- **검사하는 것 (배관)**
  - planner가 `docs/CURRENT`를 4.1 형식으로 썼다
  - evaluator가 REVIEW.md 맨 위에 4.2 블록(`판정:`, `핵심 결정:`, `메모:`)을 썼다
  - `USAGE.csv`·JOURNAL·`.harness/logs/`가 4.5·4.6 형식으로 생겼다
  - 프롬프트에 치환되지 않은 `{{...}}`가 남지 않았다(원본 로그로 확인)
  - generator의 허용 명령은 통과하고, 허용 목록 밖 명령은 막혔다(`permission_denials` 필드)
  - 루프가 `DONE`, 상한, 또는 `max_iterations`로 정상 종료했다
- **검사하지 않는 것**: 에이전트가 만든 코드의 품질. 이번 확인의 대상이 아니다.
- **비용**: 1회 $0.5~1 정도로 추정한다. 첫 실행에서 실제 값을 확인한다.
- **한계**: haiku는 상위 모델보다 프롬프트를 덜 정확하게 따를 수 있다. 실패하면 하네스 문제인지 모델 문제인지 원본 로그로 가린다. haiku로 통과하면 상위 모델에서도 통과할 가능성이 높다.
- **부수 효과**: 0007의 첫 실행 보정(크레딧 감소량과 `USAGE.csv` 비교)을 이 테스트로 할 수 있다. 대상 프로젝트(0004)를 정하지 않아도 된다.
- **Gradle**: 별도 source set `smokeTest`와 같은 이름의 태스크로 둔다.

## 8. 구현 순서

1. Gradle 골격: `build.gradle`(application, Jackson, jackson-dataformat-yaml, JUnit 5), `Main` 빈 껍데기
2. `ResultParser`와 `AgentResult`: 샘플 JSON 테스트부터 작성
3. `ConfigLoader`와 `HarnessConfig`
4. `ProjectFiles`, `CostLedger`, `JournalWriter`
5. `ClaudeRunner` 인터페이스, `FakeClaudeRunner`, `Harness` 루프. 여기까지가 **v1 동작 포팅 + A2·B1·D2**다
6. `ProcessClaudeRunner`와 실행 파일 찾기. 표준 입력으로 프롬프트를 넘기는 방식을 여기서 확인한다(짧은 실행 1회, 사전 알림)
7. `PromptRenderer`, `ToolPolicy`, 프롬프트 복사·수정(STATUS 2번)
8. `DecisionResolver`
9. `TaskArchiver`, `reviews.csv`
10. `Bootstrap`. 위험 명령 차단 훅(C2)은 보류한다(0014, 스모크 테스트 뒤에 다시 판단)
11. 스모크 테스트(7.1): 샘플 프로젝트와 `smokeTest` 태스크를 만든다. 실행 전에 사용자에게 알리고, 결과로 비용 보정(0007)을 한다

각 단계가 끝날 때마다 `./gradlew test`가 통과해야 한다. STATUS.md도 그때마다 갱신한다.

## 9. 구현 시 확인할 것
- [x] `claude -p`가 표준 입력으로 프롬프트를 받는지 (5.2): 받는다
- [x] `--disallowedTools Bash`와 `--allowedTools "Bash(./gradlew test:*)"`의 우선순위 (5.5): 금지가 이긴다
- [x] 허용 패턴 문법 `Bash(명령:*)` (0008): 동작한다. 단, 읽기 전용 명령은 목록과 무관하게 통과한다
- 위험 명령 차단 훅 (C2): 보류(0014). 만든다면 하네스가 `--settings`로 넘기고, 사람의 규칙은 프로젝트 `.claude/settings.json`에 사람이 둔다
- 대화형 부트스트랩 세션의 비용을 사후에 가져올 방법이 있는지 (4.5)
- 스모크 테스트 샘플 프로젝트의 빌드·테스트 명령 구성 (7.1)
