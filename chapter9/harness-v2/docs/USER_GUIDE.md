# 사용자 가이드

하네스를 **쓰는 사람**을 위한 문서다. 하네스 코드를 읽고 고치는 사람은 [README](../README.md)의 "1년 뒤 읽는 순서"를 따른다.

예제는 `chapter9/projects/pomodoro-todo`(Vue 3 + TypeScript 할 일 앱)를 아무것도 없는 상태에서 만든다고 가정한다. 실제 파일은 [`projects/pomodoro-todo/`](../../projects/pomodoro-todo/)에 있다.

목차
1. [아무것도 없는 상태에서 시작하기](#1-아무것도-없는-상태에서-시작하기)
2. [`harness.yml` 설정값](#2-harnessyml-설정값)
3. [루프가 멈췄을 때 (HALT)](#3-루프가-멈췄을-때-halt)
4. [완료 여부는 어떻게 아나](#4-완료-여부는-어떻게-아나)
5. [완료 후 개선이 필요할 때](#5-완료-후-개선이-필요할-때)

---

## 1. 아무것도 없는 상태에서 시작하기

### 1.1 준비물
| 항목 | 확인 |
|---|---|
| JDK 21 | `java -version` |
| `claude` CLI(로그인된 상태) | `claude --version` |
| 대상 프로젝트가 쓰는 도구 | 예제는 Node(`node -v`, `npm -v`) |

- **대상 프로젝트의 도구는 하네스가 설치해 주지 않는다.** OS에 Node가 없으면 generator가 명령을 못 돌려 막힌다(3.2). 시작 전에 직접 확인한다.
- 하네스는 한 번만 빌드해 둔다. 하네스 코드를 바꿨다면 다시 빌드한다.

```
cd chapter9/harness-v2
./gradlew installDist
```

### 1.2 프로젝트 폴더 만들기
하네스는 **프로젝트 폴더 하나**를 인자로 받는다. 폴더 안에서 에이전트가 일하고, `docs/`와 `.harness/`에 기록을 남긴다. 폴더는 비어 있어도 된다. `docs/`는 하네스가 만든다.

Windows (PowerShell)
```
cd chapter9\projects
mkdir pomodoro-todo
cd pomodoro-todo
```
macOS / Linux
```
cd chapter9/projects
mkdir pomodoro-todo
cd pomodoro-todo
```

### 1.3 `harness.yml` 두기
프로젝트 폴더 **바로 아래**(`pomodoro-todo/harness.yml`)에 둔다. 처음에는 샘플을 복사해 고친다.

- 복사할 원본: [`projects/pomodoro-todo/harness.yml`](../../projects/pomodoro-todo/harness.yml) (Node 프로젝트), [`src/smokeTest/resources/sample-project/harness.yml`](../src/smokeTest/resources/sample-project/harness.yml) (Python 샘플)
- **첫 실행용으로 한도를 작게 둔다.** 아래는 pomodoro-todo 설정에서 한도만 줄인 첫 실행용 값이다(실제 첫 실행은 `max_iterations: 3`이었다).

```yaml
claude:
  path: claude

models:
  planner: opus
  generator: sonnet
  evaluator: sonnet

limits:
  max_iterations: 3        # 첫 실행은 3사이클만. 동작을 보고 늘린다
  max_total_usd: 5         # 누적 비용 상한
  max_agent_usd: 1         # 에이전트 1회 상한
  max_turns: null
  agent_timeout_min: 30
  backlog_per_milestone: 2
  max_consecutive_errors: 2

commands:
  test: "npx vitest run"
  test_path: "npx vitest run {path}"
  build: "npx vue-tsc --noEmit"
  add_dependency: "npm install <패키지>로 설치하고 package.json에 반영한다"

permissions:
  generator_bash:
    - "Bash(npx vitest:*)"
    - "Bash(npx vue-tsc:*)"
    - "Bash(npm install:*)"
    - "Bash(npm run build:*)"
    - "Bash(git status:*)"
    - "Bash(git diff:*)"
  evaluator_bash:
    - "Bash(npx vitest:*)"
    - "Bash(npx vue-tsc:*)"
```
각 값의 뜻은 [2절](#2-harnessyml-설정값)이다. **Node가 아닌 프로젝트라면 `commands`와 `permissions`를 그 프로젝트의 명령으로 바꾼다.**

### 1.4 `.gitignore` 두기
프로젝트 폴더 바로 아래에 만든다. 하네스의 원본 로그(`.harness/`)와 의존성 폴더가 저장소에 들어가지 않게 한다.
```
.harness/
node_modules/
dist/
```

### 1.5 PRD 준비하기 (`docs/PRD.md`)
PRD가 요구사항의 유일한 기준이다. 두 방법이 있다.

**A. 직접 쓴다 (확인된 방법)**
- `pomodoro-todo/docs/PRD.md`를 만들고 요구사항을 쓴다. 하네스가 폴더를 만들지만, 첫 실행 전에 `docs/`를 직접 만들어 파일을 둬도 된다.
- 좋은 PRD의 조건(예제 PRD가 따른 방식)
  - 요구마다 ID를 붙인다(T1~T6 할 일, P1~P7 타이머, R1~R3 기록).
  - "무엇을 하면 어떻게 된다"를 확인할 수 있게 쓴다. 예: "🗑 클릭 시 확인 후 삭제".
  - 비목표(하지 않을 것)와 실패 정책(저장 실패 시 어떻게 보일지)을 쓴다.
  - 정하지 못한 것은 "미해결 의사결정"에 후보를 적는다. planner와 evaluator가 합의해 PRD에 반영한다.

**B. 비워 두고 대화로 만든다 (Bootstrap, 사용자가 직접 확인함)**
- `docs/PRD.md`가 없으면 하네스가 대화형 planner를 띄우고, 대화로 PRD를 만든다. 끝났는데도 PRD가 없으면 하네스가 종료한다.
- **터미널에서 직접 실행해야 한다.** `./gradlew run`과 Claude Code의 `!`로는 입력이 비어 실패한다(1.6).
- 사용자가 PRD 없이 시작해 대화로 PRD를 만들어 확인했다(결과가 pomodoro-todo의 PRD). 다만 `--append-system-prompt-file`로 넘긴 역할 지시가 적용됐는지를 세션 로그로 검증한 것은 아니다. 대화가 이상하면(역할을 따르지 않는 등) 알려 준다.

### 1.6 실행하기
하네스 폴더에서 실행 파일로 돌린다. 하네스가 비용을 쓰므로 한도(1.3)가 맞는지 먼저 본다.

Windows (PowerShell)
```
cd chapter9\harness-v2
build\install\harness-v2\bin\harness-v2.bat ..\projects\pomodoro-todo
```
macOS / Linux (코드를 읽어 문제없다고 판단했을 뿐 실제로 돌려 보지는 않았다)
```
cd chapter9/harness-v2
build/install/harness-v2/bin/harness-v2 ../projects/pomodoro-todo
```

- **`./gradlew run`은 쓰지 않는다.** 터미널 입력을 연결하지 않아 Bootstrap이 실패한다. Claude Code의 `!`도 마찬가지일 가능성이 높다. DONE·HALT 같은 정상 종료 코드가 `BUILD FAILED`로 보이기도 한다.
- 종료 코드: `0` = DONE 또는 최대 반복 도달, `1` = HALT, `2` = 시작 전 오류(인자, `harness.yml`, `claude` 실행 파일).
- `2`로 끝나면 비용은 들지 않았다. 메시지의 키 이름을 보고 `harness.yml`을 고친다.

### 1.7 첫 실행 뒤 확인
`pomodoro-todo/docs/`에 이런 파일이 생긴다.

| 파일 | 내용 |
|---|---|
| `JOURNAL.md` | 에이전트 실행 한 줄씩(사이클, 역할, 요약, 비용, 판정) |
| `USAGE.csv` | 실행마다 비용·토큰 |
| `TASKS.md`, `PLAN.md` | planner의 작업 목록과 계획 |
| `REVIEW.md`, `IMPL.md` | evaluator의 채점, generator의 구현 메모 |
| `BACKLOG.md` | REVIEW 메모 보관 |
| `.cycle_count` | 끝난 사이클 번호 |

- 먼저 `JOURNAL.md`를 읽는다. 사이클마다 planner → generator → evaluator 세 줄이 있고 전부 `success`면 정상이다.
- 비용은 `USAGE.csv`의 `cost_usd` 합계다. 예제는 사이클당 약 $0.6~0.7이었다(첫 실행 3사이클 $2.32).
- 이상이 없으면 `max_iterations`와 `max_total_usd`를 올려 이어서 돌린다. **`docs/`를 지우지 않는다.** 하네스는 `USAGE.csv`와 `.cycle_count`로 이어서 한다.

---

## 2. `harness.yml` 설정값

Spring의 `application.yml`처럼 프로젝트마다 하나 둔다. 시작할 때 모두 검증하고, **빠진 키·모르는 키·범위를 벗어난 값이 있으면 비용을 쓰기 전에 종료 코드 2로 멈춘다.** 오타가 조용히 무시되지 않는다.

### 2.1 `claude`
| 키 | 값 | 설명 |
|---|---|---|
| `path` | `claude` | CLI 실행 파일. Windows에서 `claude`라고 쓰면 `claude.cmd`를 찾는다. 경로(`/`나 `\` 포함)를 쓰면 그대로 쓴다 |

### 2.2 `models`
| 키 | 기본 권장 | 설명 |
|---|---|---|
| `planner` | `opus` | 계획과 종료 판정. 가장 중요한 역할이라 큰 모델을 쓴다 |
| `generator` | `sonnet` | 구현 |
| `evaluator` | `sonnet` | 테스트 실행과 채점. 비용 절감용으로 내렸다. 보안·데이터 무결성이 중요하거나 놓친 결함이 반복되면 `opus`로 올린다 |

### 2.3 `limits` (비용·반복 한도)
| 키 | 예제 값 | 설명 |
|---|---|---|
| `max_iterations` | 3~8 | **한 번 실행**에서 돌 사이클 수. 다시 실행하면 새로 센다 |
| `max_total_usd` | 5~20 | **누적** 비용 상한. `USAGE.csv`에서 복원하므로 실행을 넘어 누적된다 |
| `max_agent_usd` | 1 | 에이전트 **1회** 상한. `--max-budget-usd`로 전달된다 |
| `max_turns` | `null` | 선택. 에이전트 1회의 턴 수 상한. 역할별로 `{ planner: 15, generator: 40, evaluator: 20 }`처럼도 쓴다 |
| `agent_timeout_min` | 30 | 에이전트 1회 제한 시간(분). 넘으면 오류로 처리 |
| `backlog_per_milestone` | 2 | 마일스톤을 마감할 때 BACKLOG의 `[결함]`을 최대 몇 개까지 작업으로 올릴지. `0`이면 올리지 않는다 |
| `max_consecutive_errors` | 2 | 실행 오류(`ERROR`, `TIMEOUT`)가 연속 N회면 HALT |

**비용 상한이 어떻게 막는가 (서킷 브레이커처럼 사전 차단)**
- 에이전트를 실행하기 **전에** `누적 + max_agent_usd ≤ max_total_usd`인지 본다. 넘으면 실행하지 않고 HALT("예산 소진")다.
- 그래서 `max_total_usd`는 `max_agent_usd`보다 충분히 커야 한다(`max_agent_usd > max_total_usd`면 시작을 거부한다). 예: 누적 $7.09에 `max_agent_usd` 1이고 `max_total_usd`가 8이면 다음 실행은 막힌다.
- 상한은 에이전트 1회분만큼 **넘칠 수 있다**(턴 사이에서만 끊기므로). `max_total_usd`에 여유를 둔다.
- 값을 정하는 감: `max_total_usd` ≈ 예상 사이클 수 × 약 $0.7 + 여유. pomodoro-todo(25사이클)는 약 $16.5가 들었고 한도는 20이었다.
- 금액은 CLI가 보고한 API 환산값이라 Pro 크레딧 차감액과는 다를 수 있다. 근거는 [0007](decisions/0007-cost-limit.md).
- `max_agent_usd`는 한 번에 쓰는 비용의 천장이다. 예제에서 가장 비싼 한 번은 약 $0.62(planner)였다.

### 2.4 `commands`
프롬프트의 `{{commands.*}}`로 들어가, 에이전트가 "무엇으로 테스트하고 빌드하는지"를 알게 한다.

| 키 | 예제 | 설명 |
|---|---|---|
| `test` | `npx vitest run` | 전체 테스트 |
| `test_path` | `npx vitest run {path}` | 경로 지정 테스트. **`{path}`가 반드시 들어가야 한다** |
| `build` | `npx vue-tsc --noEmit` | 타입 검사·빌드. evaluator가 직접 돌린다 |
| `add_dependency` | `npm install <패키지>로 …` | 에이전트에게 주는 의존성 추가 방법 문장 |

### 2.5 `permissions` (역할별 Bash 허용 목록)
- 에이전트의 Bash는 **목록에 있는 명령만** 실행된다. 화이트리스트다. 형식은 `Bash(명령:*)`이고 이 형식이 아니면 시작을 거부한다. 목록은 비어 있어도 되지만 키는 있어야 한다(`[]`).
- 에이전트가 목록 밖 명령을 쓰려 하면 거부된다. generator는 우회하지 않고 `BLOCKED`로 기록하고, 3회 쌓이면 HALT가 난다(3.2).
- **`commands.build`의 명령은 `evaluator_bash`에도 넣는다.** 안 넣으면 evaluator가 빌드를 직접 못 돌리고 generator 보고를 믿게 된다. 예제는 이 때문에 `Bash(npx vue-tsc:*)`를 evaluator 목록에 추가했다.
- evaluator에는 테스트·빌드 명령만 준다. 쓰기 명령은 줄수록 위험하다.
- **어느 도구든 OS에 설치되어 있어야 한다.** 허용 목록은 "실행해도 되는 명령"이지 설치가 아니다.

### 2.6 한도를 바꾸는 시점
| 상황 | 바꿀 값 |
|---|---|
| 예산 HALT가 났다 | `max_total_usd` ↑ |
| 같은 항목에서 예산·턴 한도로 2회 연속 중단됐다 | `max_agent_usd` ↑ 또는 `max_turns` ↑ |
| 시간 초과가 반복된다 | `agent_timeout_min` ↑ |
| 평가가 허술해서 결함을 놓친다 | `models.evaluator`를 `opus`로 |
| 명령이 거부된다 | `permissions.*_bash`에 추가 |

---

## 3. 루프가 멈췄을 때 (HALT)

### 3.1 멈춘 것을 아는 법
- 종료 코드가 `1`이고, 프로젝트의 **`docs/HALT`** 파일이 생긴다. 콘솔에는 "에이전트가 HALT를 남겼다" 또는 "하네스가 HALT했다. docs/HALT를 확인한다."가 나온다.
- `docs/HALT`는 네 줄이다. **마지막 줄이 재개 방법이다.**
```
사유: 예산 소진
상세: 누적 $34.10 + 에이전트 1회 상한 $5.00 > 상한 $38.00
사이클: 15 / 역할: generator (실행 전)
재개: 이 파일을 지우고 harness.yml의 limits.max_total_usd를 올린다
```

### 3.2 사유별 대처
| 사유(예) | 의미 | 해야 할 일 |
|---|---|---|
| 예산 소진 | 누적 + 1회 상한이 `max_total_usd`를 넘음 | `max_total_usd` ↑ |
| BLOCKED 3회 | 같은 항목이 3번 막힘(허용 안 된 명령이 필요하거나 환경이 없음) | HALT의 상세를 읽는다. 허용 명령이 없으면 `permissions`에 추가하고, 도구가 OS에 없으면 설치한다. 항목 자체가 모호하면 PRD를 고친다 |
| 연속 오류 | 실행 오류가 `max_consecutive_errors`회 | `.harness/logs/c{N}-{역할}.json`에서 오류 내용을 본다. 일시적(네트워크, 사용량 한도)이면 그대로 재개한다 |
| 한도 중복 도달 | 같은 항목에서 예산·턴 한도로 2회 연속 중단 | `max_agent_usd` 또는 `max_turns` ↑. 항목이 너무 크면 PRD를 나눠 쓴다 |
| 결과 형식 이상(`INVALID_RESULT`) | `claude` 출력이 예상과 다름 | `claude` CLI 버전을 확인하고 `.harness/logs/`의 원본을 본다. 이 경우는 즉시 HALT다 |
| 합의 불발 | planner와 evaluator의 결정이 3회 일치하지 않음 | HALT의 상세에 양쪽 선택이 있다. 사람이 정해 PRD에 쓴다 |
| `CURRENT` 누락·형식 오류 | planner가 이번 항목을 못 정함 | `.harness/logs/c{N}-planner.json`을 본다 |

### 3.3 재개하는 법 (항상 같은 절차)
1. `docs/HALT`를 읽고 원인을 해결한다(3.2).
2. **`docs/HALT`를 지운다.** HALT가 있으면 하네스는 아무것도 실행하지 않고 종료 코드 1로 끝난다.
3. 같은 명령으로 다시 실행한다.
```
build\install\harness-v2\bin\harness-v2.bat ..\projects\pomodoro-todo     # Windows
build/install/harness-v2/bin/harness-v2 ../projects/pomodoro-todo           # macOS / Linux
```

- **`USAGE.csv`, `.cycle_count`, `docs/` 안의 다른 파일은 지우지 않는다.** 이것들로 이어서 한다.
- 하네스가 쓴 HALT(예산, 오류 연속, `CURRENT` 누락)는 사이클 카운터를 저장하지 않으므로 **같은 번호의 사이클을 다시 한다.** 이미 성공한 역할은 건너뛴다. 예를 들어 generator까지 끝났고 예산 HALT가 났다면, 재개할 때 planner·generator를 건너뛰고 evaluator부터 한다([0016](decisions/0016-resume-interrupted-cycle.md)).
- 에이전트가 쓴 HALT(BLOCKED 3회, 합의 불발)는 카운터를 저장하므로 다음 번호의 사이클부터 한다.
- `max_iterations`는 매번 새로 센다. HALT 전에 몇 사이클을 돌았는지와 무관하다.
- 재개하기 전에 해결하지 않고 HALT만 지우면 같은 이유로 다시 멈춘다. 이때도 비용은 나간다.

---

## 4. 완료 여부는 어떻게 아나

### 4.1 `DONE`과 "최대 반복 도달"은 다르다
둘 다 종료 코드가 `0`이라 **코드로는 구분되지 않는다.**

| | DONE (완료) | 최대 반복 도달 (미완) |
|---|---|---|
| 콘솔 마지막 줄 | `planner가 DONE을 남겼다. 종료.` | `최대 반복 횟수(N)에 도달했다. 종료.` |
| `docs/DONE` 파일 | 있다 | 없다 |
| JOURNAL 마지막 줄 | `planner: DONE 생성 (…)` | 마지막 evaluator 줄 |

- 가장 확실한 확인은 **`docs/DONE`이 있는지**다. 없으면 완료가 아니다. 한도를 올려 이어서 돌린다(3.3과 같은 방식, HALT는 없으니 그냥 다시 실행).
- 하네스는 사이클을 시작할 때 `DONE`을 지우고 planner가 다시 판정하게 한다. 그래서 `DONE`은 "마지막 사이클에서 planner가 PRD와 코드의 간극이 없다고 봤다"는 뜻이다.

### 4.2 DONE을 믿기 전에 직접 확인할 것
`DONE`은 planner의 판단이다. **다음을 직접 확인한다.**

1. **작업이 모두 끝났는가**: `docs/TASKS.md`에 `- [ ]`가 없다. 끝난 마일스톤은 `docs/archive/`로 옮겨져 있다.
2. **마지막 평가가 통과인가**: `.harness/reviews.csv` 마지막 줄이 `PASS`나 `조건부`다. `FAIL`이 마지막이면 DONE이 나오지 않아야 한다.
3. **미처리 결함이 없는가**: `docs/BACKLOG.md`에서 `→`가 없는 `[결함]` 줄을 찾는다. 있으면 마일스톤 마감 때 올려지지 않은 것이다.
4. **테스트와 타입 검사를 직접 돌린다.** (프로젝트 폴더에서)
   ```
   npx vitest run
   npx vue-tsc --noEmit
   ```
5. **화면은 사람이 본다.** evaluator는 브라우저를 못 띄우므로 화면 점수는 **코드를 읽고 한 추정**이다. 예제는 사람이 직접 확인해서 키보드 문제를 찾았다.
   - 개발 서버는 **앱 폴더에서** 실행한다. 하네스 폴더에서 `npm run dev`를 치면 안 된다.
   ```
   cd chapter9/projects/pomodoro-todo
   npm run dev
   ```
   - PRD의 요구를 하나씩 따라 해 본다(할 일 추가·편집·삭제·드래그, 집중 시작·일시정지, 새로고침 후 복원 등).

### 4.3 비용·이력 확인
- 총 비용: `docs/USAGE.csv`의 `cost_usd` 합계. 한도 안이면 정상이다.
- 사이클 수: `docs/.cycle_count`.
- 결함 승격이 동작했는지: BACKLOG에서 `→ T21`처럼 항목 ID가 붙은 줄.

---

## 5. 완료 후 개선이 필요할 때

`DONE`이 나온 뒤에도 요구는 바뀐다. **PRD를 고치고 같은 명령으로 다시 실행하면 된다.** 하네스는 사이클을 시작할 때 `DONE`을 지우고 planner가 PRD 전체를 다시 읽어 간극을 찾는다.

### 5.1 절차
1. `docs/PRD.md`에 새 요구를 쓴다.
2. `harness.yml`의 `max_iterations`를 작게(2~3) 둔다. 보통 개선 하나는 "새 작업 1개 → 구현 → 평가 → DONE 재판정"이라 2사이클이면 된다.
3. 예산을 확인한다. `max_total_usd - 누적`이 사이클 수 × $1 정도 남아 있어야 한다.
4. 실행한다(1.6과 같은 명령). `docs/DONE`을 직접 지울 필요는 없다.
5. 결과를 4절과 같이 확인한다.

### 5.2 PRD에 쓰는 법 (예제)
pomodoro-todo는 처음에 "제목은 클릭하면 집중이 시작된다"까지만 요구했고, 키보드로는 시작할 수 없었다(PRD에 요구가 없었으므로 하네스는 이를 `[보강]`으로만 남겼다). PRD의 P1 행 끝에 한 줄을 덧붙였다.

```
| P1 | 집중 시작 | 할 일 행(제목 영역)을 클릭하면 … (자체 결정: 합의), <br>(개선) 키보드만으로도 집중을 시작할 수 있어야 한다(Tab으로 할 일 제목에 포커스, Enter 또는 Space로 시작). |
```
- 결과: planner가 M6(키보드 접근성)와 T32를 새로 만들었고, generator가 `tabindex`와 Enter/Space 핸들러를 넣었으며, evaluator가 조건부(11/15)로 통과시켰다. 이어서 planner가 PRD 전체를 다시 대조해 `DONE`을 다시 만들었다. 2사이클, 약 $1이었다.
- 요령
  - **확인할 수 있게 쓴다.** "접근성을 개선한다"가 아니라 "Tab으로 포커스, Enter 또는 Space로 시작"처럼 동작을 쓴다.
  - 기존 요구를 고칠 때는 바뀐 부분을 표시한다(예: `(개선)`). 나중에 PRD를 읽을 때 구분된다.
  - 요구를 **삭제하지 않는다.** 이미 만든 기능과 PRD가 어긋나면 planner가 간극으로 본다.
  - 큰 개선은 한 줄로 끝내지 않고 요구를 나눠 쓴다. 하나의 사이클은 작업 1개를 처리한다.

### 5.3 BACKLOG에 있는 것은 자동으로 처리되지 않는다
- evaluator의 `[보강]` 메모(테스트 보강, 접근성 등)는 BACKLOG에 쌓이기만 하고 **작업으로 올라가지 않는다.** 마일스톤 마감 때 올라가는 것은 `[결함]`뿐이고 최대 `backlog_per_milestone`개다.
- 그러니 `[보강]` 중 정말 필요한 것은 사람이 PRD의 요구로 옮겨 쓴다.
- BACKLOG를 정기적으로 읽는 것이 좋다. 예제의 `[보강]` 중 "키보드 접근성", "저장 경고 배너 없음"은 실제로 의미 있는 항목이었다(후자는 계획에 이미 있어 처리됐다).

### 5.4 하지 말 것
- `docs/TASKS.md`, `.cycle_count`, `USAGE.csv`를 손으로 고치지 않는다. 하네스가 기계적으로 읽는다.
- `docs/` 폴더를 지우고 다시 시작하지 않는다. 이전 합의와 이력이 사라지고 같은 비용을 다시 쓴다.
- 평가가 못 보는 것(화면)은 개선 후에도 사람이 본다. 하네스가 `DONE`을 만들어도 화면은 보증하지 않는다.

### 5.5 다른 방식으로 고치고 싶을 때
- **하네스의 동작 자체**(프롬프트, 기준)가 문제라면 PRD가 아니라 하네스를 고친다. 결정은 [`decisions/`](decisions/README.md)에 기록한다. 예제 실행에서 이렇게 고친 것이 [0015](decisions/0015-journal-summary-last-line.md)와 [0016](decisions/0016-resume-interrupted-cycle.md)이다.
- 결과가 의도와 다르면 [STATUS](STATUS.md)의 "pomodoro-todo 첫 실행 점검과 수정"처럼, 로그를 읽고 원인을 찾은 뒤 고친다.
