# harness-v2

planner → generator → evaluator, 세 에이전트(`claude -p`)를 순서대로 돌려 PRD를 코드로 만들어 가는 **Java 하네스**다.
v1(`chapter9/harness`, Python)을 Java 개발자가 읽고 고칠 수 있게 다시 쓴 것이다(근거: [0002](docs/decisions/0002-rewrite-harness-in-java.md)).

- **판단은 에이전트, 순서·기록·상한은 하네스**가 맡는다. 에이전트는 계획·구현·채점을 하고, 하네스는 실행 순서, 비용 기록, JOURNAL, 아카이브, 예산 차단, 실패 처리를 한다.
- 이 폴더는 **하네스 자체**다. 하네스가 일하는 대상은 별도의 프로젝트 폴더(`harness.yml`이 있는 곳)다.

## 1년 뒤 읽는 순서

| 순서 | 문서 | 얻는 것 |
|---|---|---|
| 1 | 이 README | 쓰는 법, 폴더 구조, 실행 흐름 |
| 2 | [`docs/STATUS.md`](docs/STATUS.md) | 어디까지 했고, 무엇이 미확인·보류인지 |
| 3 | [`docs/decisions/README.md`](docs/decisions/README.md) | 사람이 내린 결정 목록(0001~). 이유는 각 파일에 있다 |
| 4 | [`docs/DESIGN.md`](docs/DESIGN.md) | 1절(구조도) → 4절(파일 형식) → 6절(메인 루프) 순으로 읽는다. 3절은 `harness.yml` 스키마 |
| 5 | [`docs/IMPROVEMENTS.md`](docs/IMPROVEMENTS.md) | v1의 결함과 v2 개선 항목(A1~D5), 미확인 항목(6절) |
| 6 | 코드 | `Main` → `Harness` → 필요한 패키지. 아래 "실행 흐름" 참고 |

`CLAUDE.md`는 Claude Code 작업 규칙이다. 사람이 읽을 필요는 없지만 협업 규칙(비용, 결정 방식)이 적혀 있다.

## 빠른 시작

**준비물**: JDK 21, `claude` CLI(로그인된 상태). Windows에서는 `claude.cmd`를 자동으로 찾는다.

```
cd chapter9/harness-v2

./gradlew test                                   # 단위 테스트 (무료, 가짜 claude 사용)
./gradlew run --args="../projects/<project>"     # 대상 프로젝트에서 루프 실행 (유료)
```

`./gradlew installDist` 후 `build/install/harness-v2/bin/harness-v2 <project>`로도 실행할 수 있다.

**종료 코드**: `0` = DONE 또는 최대 반복 도달, `1` = HALT, `2` = 시작 전 오류(인자, `harness.yml`, 프롬프트 템플릿, `claude` 실행 파일).

### 새 프로젝트에 적용하기
1. 프로젝트 폴더를 만들고 `harness.yml`을 둔다. 예제는 [`src/smokeTest/resources/sample-project/harness.yml`](src/smokeTest/resources/sample-project/harness.yml)이고, 키 설명은 DESIGN 3절에 있다.
   - 테스트·빌드·의존성 추가 명령(`commands.*`)과 역할별 Bash 허용 패턴(`permissions.*`)이 프로젝트마다 다른 부분이다.
   - 필수 키가 빠졌거나 모르는 키가 있으면 시작을 거부한다(종료 코드 2).
2. `docs/PRD.md`를 직접 쓴다. **없으면 대화형 planner(`Bootstrap`)가 뜨고**, 대화로 PRD를 만든다. 그래도 PRD가 없으면 종료한다.
3. 위 `run` 명령으로 실행한다. 처음에는 `limits.max_iterations`와 `max_total_usd`를 작게 시작한다.

### 멈췄을 때
- `docs/HALT`가 있으면 하네스는 아무것도 실행하지 않고 종료한다. 파일에 이유·상세·재개 방법이 네 줄로 적혀 있다.
- 원인을 해결하고 **`docs/HALT`를 지운 뒤** 다시 실행한다. `.cycle_count`와 `USAGE.csv`가 남아 있어 이어서 돈다.
- 예산 소진이면 `harness.yml`의 `limits.max_total_usd`를 올려야 재개된다(누적 비용은 `USAGE.csv`에서 복원).
- `docs/DONE`은 planner가 "PRD와 코드의 간극이 없다"고 판단했다는 뜻이다. 매 사이클 지우고 다시 판정한다.

### 비용
- 상한 두 개: `max_total_usd`(누적), `max_agent_usd`(에이전트 1회, `--max-budget-usd`). 근거는 [0007](docs/decisions/0007-cost-limit.md).
- 상한은 **에이전트 1회분만큼 넘칠 수 있다**(턴 사이에서만 끊기므로). 그래서 `max_total_usd`에 여유를 둔다.
- 금액은 CLI가 보고한 API 환산값이다. Pro 크레딧 차감액과는 다를 수 있다(보정은 아직 못 했다).
- 참고 실측: 스모크 샘플(haiku, 6회 실행) 약 $0.046.

## 폴더 설명

### 하네스 (이 폴더)
```
harness-v2/
├── README.md, CLAUDE.md
├── build.gradle, settings.gradle      # application 플러그인, Jackson, JUnit 5. smokeTest 소스셋 포함
├── docs/                              # STATUS, DESIGN, IMPROVEMENTS, decisions/
└── src/
    ├── main/java/harness/
    │   ├── Main.java                  # 진입점. 설정·프롬프트 검증 후 Harness 조립
    │   ├── Harness.java               # 메인 루프(사이클, 에이전트 1회 실행, HALT 처리)
    │   ├── Bootstrap.java             # PRD가 없을 때 대화형 planner 실행
    │   ├── config/                    # harness.yml 읽기·검증 (ConfigLoader, HarnessConfig)
    │   ├── claude/                    # claude -p 실행(ProcessClaudeRunner)과 결과 JSON 해석(ResultParser)
    │   ├── cost/                      # 누적 비용 상한 검사, USAGE.csv (CostLedger)
    │   ├── journal/                   # JOURNAL.md 한 줄 기록 (JournalWriter)
    │   ├── prompt/                    # 프롬프트의 {{변수}} 치환 (PromptRenderer)
    │   ├── policy/                    # 역할(Role)별 허용·금지 도구 (ToolPolicy)
    │   ├── state/                     # docs/ 아래 파일 경로, DONE·HALT·CURRENT 읽기·쓰기 (ProjectFiles)
    │   ├── review/                    # REVIEW.md 판정 읽기, reviews.csv 저장
    │   ├── decision/                  # planner·evaluator 블라인드 합의 (DecisionResolver)
    │   └── archive/                   # 끝난 마일스톤의 작업 지시를 archive로 이동 (TaskArchiver)
    ├── main/resources/prompts/        # planner, generator, evaluator, planner_bootstrap 프롬프트
    ├── test/                          # 단위 테스트. FakeClaudeRunner로 루프 전체를 무료로 검증
    └── smokeTest/                     # 실제 claude로 돌리는 스모크 테스트와 샘플 프로젝트 (유료, 수동)
```

### 대상 프로젝트 (하네스가 일하는 곳)
```
<project>/
├── harness.yml                  # 프로젝트별 설정
├── docs/
│   ├── PRD.md                   # 요구사항 (사람 또는 Bootstrap)
│   ├── PLAN.md, TASKS.md        # planner가 쓰는 계획과 작업 목록
│   ├── CURRENT                  # 이번 사이클의 항목 ID (planner가 쓰고 generator·evaluator가 읽는다)
│   ├── IMPL.md, REVIEW.md       # generator의 구현 메모, evaluator의 채점
│   ├── BACKLOG.md               # REVIEW 메모 보관
│   ├── JOURNAL.md               # 하네스가 한 줄씩 기록하는 실행 이력
│   ├── USAGE.csv                # 실행마다 비용·토큰
│   ├── .cycle_count, DONE, HALT # 사이클 카운터, 종료·정지 표시
│   ├── decisions/               # planner·evaluator 합의 기록
│   └── archive/                 # 끝난 마일스톤의 TASKS-M{n}.md
└── .harness/
    ├── logs/                    # 에이전트 원본 결과 JSON(c{N}-{role}.json)과 넘긴 프롬프트
    └── reviews.csv              # 항목별 판정(PASS/FAIL 점수)
```
- 에이전트가 `docs/`를 훑을 때 큰 JSON을 읽지 않도록 원본 로그는 `.harness/`에 둔다. `.harness/`는 대상 프로젝트의 `.gitignore`에 넣기를 권장한다.
- 형식 규칙(하네스와 프롬프트가 같이 따라야 하는 줄 형식)은 DESIGN 4절에 있다.

## 실행 흐름

실행 → 사이클 반복 → 종료까지의 큰 흐름이다. 이름을 따라 코드를 열면 된다.

1. **시작** — `Main.main` → `Main.run`
   - `ConfigLoader.load`로 `harness.yml`을 검증한다.
   - `PromptRenderer.checkTemplates`로 프롬프트 템플릿 오류를 비용을 쓰기 전에 잡는다.
   - `ClaudeExecutable.resolve`로 claude 실행 파일을 찾고, `Harness`를 조립해 `run()`을 부른다. 실패하면 종료 코드 2.
2. **준비** — `Harness.run`
   - `docs/HALT`가 있으면 아무것도 실행하지 않고 종료한다.
   - `Bootstrap.run`: PRD가 없으면 대화형 planner를 띄운다.
   - `CostLedger.load`로 `USAGE.csv`에서 누적 비용을, `ProjectFiles.readCycleCount`로 이전 사이클 번호를 복원한다.
3. **사이클 반복** — `Harness.runCycle` (`max_iterations`번까지)
   1. `DONE`·`CURRENT`를 지운다. 매 사이클 planner가 다시 판정하게 하기 위해서다.
   2. `archiveClosedMilestones` → `TaskArchiver`: 끝난 마일스톤의 작업 지시를 `docs/archive/`로 옮긴다.
   3. planner 실행. `DONE`이면 종료, `HALT`면 정지, `CURRENT`가 없거나 형식이 틀리면 하네스가 HALT한다.
   4. generator 실행(`CURRENT`의 항목만 구현), evaluator 실행(채점).
   5. evaluator 성공 시 `recordReview`: REVIEW.md 맨 위 블록을 `ReviewParser`로 읽어 `ReviewStore`(reviews.csv)에 저장하고, 판정을 JOURNAL 줄에 붙인다.
   6. `DecisionResolver.resolve`: planner와 evaluator가 따로 낸 결정이 일치하는지 본다. 3회 불발이면 HALT.
4. **에이전트 1회** — `Harness.runAgent`
   - `CostLedger.canAfford`: 누적 + 1회 상한이 총 상한을 넘으면 실행하지 않고 HALT("예산 소진").
   - `PromptRenderer.promptFor`로 프롬프트를, `ToolPolicy`로 역할별 도구를 정해 `AgentRequest`를 만든다.
   - `ClaudeRunner.run`: 실제로는 `ProcessClaudeRunner`가 `claude -p`를 띄우고, `ResultParser`가 결과 JSON을 `AgentResult`(`Outcome` 포함)로 바꾼다. 원본은 `.harness/logs/`에 저장한다.
   - `CostLedger.record`(USAGE.csv)와 `JournalWriter.append`(JOURNAL)는 **오류여도** 남긴다.
   - `decideNext`가 `Outcome`별로 다음을 정한다.

     | Outcome | 처리 |
     |---|---|
     | `SUCCESS` | 계속 |
     | `BUDGET_LIMIT`, `TURN_LIMIT` | 사이클 중단(같은 번호로 재시도). 같은 항목에서 2회 연속이면 HALT |
     | `ERROR`, `TIMEOUT` | 사이클 중단. `max_consecutive_errors`회 연속이면 HALT |
     | `INVALID_RESULT` | 즉시 HALT (결과 JSON 형식이 예상과 다름) |
5. **종료** — 정상 완료한 사이클만 `.cycle_count`에 저장한다(`DONE`·에이전트가 쓴 HALT도 저장, 하네스가 쓴 HALT와 중단된 사이클은 저장하지 않음). 상세는 DESIGN 6절.

## 테스트

| 명령 | 비용 | 내용 |
|---|---|---|
| `./gradlew test` | 무료 | 단위 테스트. 가짜 `claude`(`FakeClaudeRunner`, `FakeClaudeMain`)로 루프까지 검증 |
| `$env:HARNESS_SMOKE = "1"; ./gradlew smokeTest` | 유료 (약 $0.05) | 샘플 프로젝트(`reverse()` 함수 하나)를 haiku로 실제 실행하고 배관 10개를 검사. 결과는 `build/smoke-run/REPORT.md`. 환경 변수가 없으면 무료 검사만 돈다 |
| `$env:HARNESS_REAL_CLAUDE = "1"; ./gradlew test --tests harness.claude.RealClaudeCheckTest` | 유료 (약 $0.014) | 표준 입력, 도구 금지 우선순위 등 실제 CLI 동작 확인. 리포트는 `build/real-claude-check/` |

- 스모크 테스트는 `test`·`check`에 연결하지 않았다. 의도하지 않은 비용을 막기 위해서다([0011](docs/decisions/0011-smoke-test.md)).

## 알려진 한계와 보류
최신 상태는 [`docs/STATUS.md`](docs/STATUS.md)가 기준이다. 이 README 작성 시점(2026-11-24)에는 다음이 남아 있다.
- **Bootstrap 실제 확인 전**: `--append-system-prompt-file`이 대화형 세션에서 적용되는지 확인하지 못했다. 안 되면 `--append-system-prompt <본문>`으로 바꾼다.
- **비용 보정 전**(0007): 하네스 합계와 Pro 한도 사용량의 비교는 한도를 다 쓴 상태에서만 가능하다.
- **훅 보류**(0013, 0014): Bash 허용 목록 훅과 위험 명령 차단 훅. 쓰기 명령은 이미 거부되고, 읽기 전용 명령(`whoami` 등)은 허용 목록 밖이어도 실행된다.
- 사용량 한도에 도달했을 때의 출력 형태는 재현하지 못해 미확인이다.
- 실제 대상 프로젝트로 돌려 본 적이 없다(샘플만).
