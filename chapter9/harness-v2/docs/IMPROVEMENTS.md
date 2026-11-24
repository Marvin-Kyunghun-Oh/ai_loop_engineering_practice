# harness-v2 개선 사항

v1 하네스(`chapter9/harness`)를 Java로 다시 만들면서 함께 고칠 결함과 개선 사항을 정리한다.
근거는 v1 코드(`chapter9/harness/src/harness/run.py`, `prompts/*.md`)와 rss-wiki 실행 기록(`chapter9/projects/rss-wiki/docs/`)이다.

v2의 목표는 **Java 개발자가 읽고 고칠 수 있는 하네스**다. 기능을 늘리기보다 v1의 동작을 이해하기 쉬운 Java 코드로 옮기고, 아래 결함을 고친다.

## 1. 배경: v1 실행 결과

| 항목 | 값 |
|---|---|
| 대상 | `chapter9/projects/rss-wiki` (M1~M6 중 M1 완료, M2 진행 중) |
| 사이클 | 38회 (약 17시간) |
| TASKS | 22/24 완료. 이 중 **11개가 보강 항목**(`T1a`, `T1b`, `T2a`, `T2b`, `T3r`, `T3s`, `T4r`, `T6r`, `T6s`, `T8r`, `T8s`) |
| 테스트 | 406 passed |
| 문서 크기 | TASKS.md 85KB, PLAN.md 42KB, JOURNAL.md 20KB |
| 중단 사유 | Pro 플랜 5시간 한도 도달, 남은 크레딧으로 완주 불가 판단 |

잘 작동한 것(v2에서 유지): 역할별 권한 분리, 파일 기반 상태(`DONE`/`HALT`/`.cycle_count`), 블라인드 결정 합의, 매 사이클 종료 재판정, "사용자에게 묻지 않기" 정책, 평가자가 직접 테스트를 실행하는 구조.

문제는 대부분 **비용 통제와 관측**에 있었다.

## 2. 개선 항목

표기: 심각도 **H**(결함이 크거나 효과가 큼) / **M** / **L**

### A. 비용 통제

#### A1. PASS 메모가 보강 항목을 낳는 규칙 — H
- **근거**: `planner.md:44` "조건부 PASS의 메모는 다음 항목의 acceptance나 touch에 반영", `planner.md:47` "직전 REVIEW의 메모를 해소하는 항목이 있으면 먼저 선정". 평가자는 PASS여도 메모를 남기므로 planner가 매번 후속 항목을 만들었다. 결과적으로 22개 중 11개가 보강 항목이었다.
  - 구멍은 `planner.md:47`이 PASS와 조건부 PASS를 구분하지 않는다는 점이다. 예: T8r은 PASS(11/12)였지만 그 메모가 T8s가 됐다.
- **v2 결정 ([0010](decisions/0010-backlog-for-review-memos.md))**
  - FAIL만 즉시 후속 항목으로 만든다.
  - PASS·조건부 PASS 메모는 `docs/BACKLOG.md`에 한 줄로 적고 현재 마일스톤 범위에서 제외한다.
  - 마일스톤 마감 시 planner가 BACKLOG에서 결함성 항목(동작 오류, 경계 누락, 회귀 위험)만 골라 **최대 2개**를 항목화한다. 상한은 `limits.backlog_per_milestone`으로 바꿀 수 있다.
  - 나머지는 BACKLOG에 남긴다(삭제하지 않음).
- **Java 메모**: 대부분 프롬프트 변경이다. 하네스는 BACKLOG 파일 존재를 보장하고, 마일스톤 마감 사이클에 상한 값을 프롬프트에 넣어 준다.

#### A2. 비용 기록과 금액 상한이 없음 — H
- **근거**: `run.py:91-105`의 `run_agent`는 `claude -p`를 실행하고 종료 코드만 로그로 남긴다. `run.py:36`의 `MAX_ITERATIONS`(기본 50)는 한 번 실행하는 사이클 횟수 제한일 뿐, 누적 한도나 금액 한도가 아니다. 진행 중에 남은 예산을 계산할 수 없었다.
- **기준: CLI가 보고한 비용의 누적**
  - 각 `claude -p` 실행의 결과 JSON에 들어 있는 비용 값(`total_cost_usd`, 실제 출력으로 확인함)을 하네스가 더해 상한을 판단한다.
  - 이 값은 대화형 세션의 `/statusline`이 보여주는 cost와 같은 출처(세션별 환산 비용)다. statusline은 하네스의 하위 세션을 볼 수 없어서, 같은 값을 하네스가 직접 모은다.
  - 단가표를 하네스에 두고 토큰×단가로 계산하는 방식은 쓰지 않는다. 단가를 직접 관리해야 하고, 요금이 바뀌면 틀리기 때문이다.
- **설정**
  ```yaml
  # harness.yml
  limits:
    max_total_usd: 38     # 목표 $40 - 여유분 $2 (누적 상한)
    max_agent_usd: 5      # 에이전트 1회 상한 → --max-budget-usd
  ```
- **운영 흐름** (planner·generator·evaluator 실행마다)
  1. **실행 전 검사**: `누적 + max_agent_usd > max_total_usd`이면 실행하지 않고 `HALT`에 "예산 소진"을 적고 멈춘다.
  2. **실행**: `claude -p ... --output-format json --max-budget-usd 5`로 실행한다.
  3. **기록**: 결과 JSON의 비용과 토큰을 `docs/USAGE.csv`에 적고 누적 비용에 더한다.
  4. **판정**: 오류이거나 예산 상한에 걸려 끊겼으면 그 사이클을 중단한다(B1).

  ```
  사이클 12 evaluator 종료 · $1.80 · 누적 $27.40 / $38
  사이클 15 generator 실행 안 함: 누적 $34.10 + 최대 $5 > $38 → HALT
  ```
  - 결과적으로 $40을 넘지 않는다. 실제로는 대략 $33~38에서 멈추고, 남는 금액은 안전 여유다.
  - **재개**: `HALT`를 지우고 `max_total_usd`를 올리면 이어서 돈다. 누적 비용은 `USAGE.csv`에서 다시 읽는다.
- **상한을 넘을 수 있는 경로와 대책**

  | 수준 | 비용을 아는 시점 | 넘칠 수 있는 크기 | 대책 |
  |---|---|---|---|
  | 하네스(누적 상한) | 에이전트 프로세스 종료 후 | 에이전트 1회분 (수 달러) | 1회 상한을 이용해 **실행 전에** 차단 |
  | CLI(`--max-budget-usd`) | 턴과 턴 사이 (**확인함**) | 마지막 턴 1회분 (수십 센트) | 여유분 $2로 흡수 |

  - 2026-11-24 확인: 상한 $0.001로 실행하자 2턴째에 멈췄고, 실제 비용은 $0.00196(상한의 약 2배)이었다. 상한을 넘긴 뒤에야 멈추며, 넘치는 크기는 턴 1회분이다.
  - 따라서 실행 전 검사에서 쓰는 `max_agent_usd`는 "정확한 최대치"가 아니라 "턴 1회분이 더 붙을 수 있는 값"이다. 여유분 $2가 이 차이를 흡수한다. opus의 큰 컨텍스트 턴 1회는 대략 수십 센트~$1 수준으로 추정한다.

- **한계: 표시 금액 ≠ 실제 크레딧 차감액**
  - 표시 금액은 API 요금으로 환산한 값이다. Pro 5시간 한도 안에서 쓴 사용량(크레딧이 빠지지 않음)도 세므로, 보통은 실제보다 **많게** 센다. 일찍 멈추는 쪽이라 안전하다.
  - 결과 JSON의 `modelUsage.{모델}.costBasis`가 `"list"`로 나온다. 정가(API 요금표) 기준 환산이라는 뜻으로 보인다.
  - 한도 초과 후 크레딧이 같은 단가로 차감되는지는 확인하지 못했다.
  - **보정 절차**(0011 이후 스모크 테스트로 수행, Pro 한도를 다 쓴 상태에서): 첫 실행은 `max_total_usd: 10`으로 돌린다. 끝나면 계정의 크레딧 감소량과 `USAGE.csv` 합계를 비교한다. 비슷하면 $38로 올리고, 차이가 크면 그 비율만큼 조정한다.
- **토큰 기록 (분석용)**
  - 상한 판단에는 쓰지 않지만, 어디에 많이 쓰였는지 보려고 토큰을 종류별로 기록한다.
  - 하네스는 매 턴 같은 문서를 다시 읽으므로 캐시 읽기 토큰이 압도적으로 많다. 이 토큰은 일반 입력보다 훨씬 싸므로(API 기준 약 1/10) 합계만 보면 오해한다. 반드시 종류별로 본다.
  ```
  cycle,agent,model,input,cache_creation,cache_read,output,turns,duration_sec,cost_usd,stop_reason
  ```
- **결과 JSON 필드 (2026-11-24 실제 출력으로 확인)**
  - 샘플: `src/test/resources/claude-result/`의 `success.json`, `error-max-budget-usd.json`, `error-max-turns.json`
  - `session_id`, `uuid`, `credential_expires_at`는 `<redacted>`로 가렸다.

  | 용도 | 필드 | 값의 예 |
  |---|---|---|
  | 비용 | `total_cost_usd` | `0.00271608` |
  | 토큰 | `modelUsage.{모델}.inputTokens`, `cacheCreationInputTokens`, `cacheReadInputTokens`, `outputTokens`의 합 (없으면 `usage.*_tokens`). 예산 상한에 걸리면 `usage`는 0으로 나온다 (0012) | `2`, `12718`, `15028`, `44` |
  | 모델별 | `modelUsage.{모델}.costUSD`, `costBasis` | `"claude-haiku-5-5"`, `"list"` |
  | 오류 여부 | `is_error` | `false` / `true` |
  | 종료 사유 | `subtype` | `success`, `error_max_budget_usd`, `error_max_turns` |
  | 종료 사유(보조) | `terminal_reason` | `completed`, `budget_exhausted`, `max_turns` |
  | 오류 메시지 | `errors` (배열, 오류일 때만) | `["Reached maximum budget ($0.001)"]` |
  | API 오류 | `api_error_status` | `null` |
  | 요약 | `result` | 성공 시 문자열, **오류 시 `null`** |
  | 기타 | `num_turns`, `duration_ms`, `stop_reason` | `1`, `1126`, `end_turn` |

  - **종료 코드로는 구분할 수 없다.** 예산 상한과 턴 상한 모두 종료 코드가 `1`이다. 판정은 `subtype`으로 한다.
  - **오류 시 `result`가 `null`이다.** JOURNAL 요약(0009)은 `result`가 없으면 `errors[0]`을 대신 쓴다.
  - 필드가 많고 버전마다 늘 수 있으므로, Jackson은 필요한 필드만 매핑하고 나머지는 무시한다(`@JsonIgnoreProperties(ignoreUnknown = true)`).
- **Java 메모**: 결과 JSON은 Jackson으로 파싱한다(5절). 표준 출력이 JSON이 되므로 에이전트의 요약 출력은 결과 JSON의 `result` 필드에서 꺼내 콘솔에 출력한다. 필수 필드(비용, 오류, 종료 사유)가 없으면 0으로 넘어가지 말고 예외로 `HALT`한다. 필드명이 틀려 상한이 영원히 발동하지 않는 사고를 막기 위해서다.

#### A3. 에이전트 1회 실행의 상한이 없음 — H
- **근거**: v1은 에이전트 1회 실행의 길이나 비용을 제한하지 않는다. 평가자 프롬프트(`evaluator.md`)에는 변이 검증 지시가 없는데, JOURNAL을 보면 평가자가 스스로 변이를 7~16종씩 돌렸다. (프롬프트 근거는 없고 JOURNAL 기록에서 추정한 것이다)
- **v2 제안**
  - 1차 수단은 **금액 상한**이다. A2의 `max_agent_usd`를 `--max-budget-usd`로 넘긴다. 관리하려는 대상이 돈이므로, 턴 수보다 직접적이다.
  - `--max-turns`는 **기본 미설정 선택 옵션**으로 둔다. 같은 도구 호출을 반복하며 헛도는 경우를 대비한 보조 장치다(지원 확인, `claude --help` 출력에는 나오지 않음).
    ```yaml
    # harness.yml
    limits:
      max_turns: null   # 예: { planner: 15, generator: 40, evaluator: 20 }
    ```
  - 상한(금액·턴)에 걸려 끝난 실행은 결과 JSON의 종료 사유로 구분해 B1의 오류와 다르게 기록한다. 그 사이클은 재시도하지 않고 다음 사이클로 넘어가며, 같은 항목에서 연속되면 `BLOCKED`로 취급한다.
  - 평가자 프롬프트에 "변이 검증은 acceptance에 명시된 것만 수행한다"를 넣는다.

#### A4. 문서가 계속 커짐 — H
- **근거**: TASKS.md는 완료 항목의 `내용`·`acceptance`를 그대로 남겨 85KB가 됐다. PLAN.md는 "자체 결정"이 누적돼 42KB, JOURNAL은 무한히 누적된다. 매 사이클 모든 에이전트가 이 문서를 읽고, v1 기본 설정에서는 그중 둘이 opus다.
- **위험: 맥락 손실**
  - 일이 TASK 단위로 딱 끊기지 않는다. v1에서도 T9a는 "T6 REVIEW 선택 메모"를 근거로 했고, T7b의 규칙은 T7의 결정 위에 쌓였다. 이전 내용을 무작정 치우면 에이전트가 이런 맥락을 잃는다.
  - 반대로 문서를 다 두는 것도 맥락을 잃는다. 85KB를 매번 읽으면 중요한 결정이 세부 사항에 묻히고, 모델은 긴 입력의 중간을 놓치기 쉽다.
  - 따라서 이 항목은 "보존 대 손실"의 선택이 아니라, **무엇을 매번 읽히고 무엇을 필요할 때만 찾게 할지**의 선택이다.
- **맥락의 종류별 처리**

  | 종류 | 예 | 처리 |
  |---|---|---|
  | 완료 항목의 작업 지시 | T1의 필드 목록, acceptance | **아카이브**. 지금은 코드와 테스트가 그 내용의 원본이다 |
  | 결정과 그 이유 | "깨진 link는 원문 유지", "버리기 깊이는 태그별" | **옮기지 않는다**. 코드만으로는 이유를 알 수 없는 핵심 맥락이다 |
  | 진행 흐름 | JOURNAL | 파일은 두고 최근 30줄만 읽는다 |

- **v2 제안**
  1. **하네스(Java 코드)가 옮긴다.** 대상은 완료 항목(`- [x]`)의 `내용`·`acceptance` 상세뿐이다. 규칙이 기계적이라 결과가 항상 같고, 비용이 들지 않고, JUnit으로 검증할 수 있다.
  2. **옮기는 시점은 마일스톤 완료 때다.** 진행 중인 마일스톤의 항목은 서로 참조할 가능성이 높으므로 그대로 둔다. 대상 파일은 `docs/archive/TASKS-M{n}.md`.
  3. **TASKS.md에 단서를 남긴다.** 완료 항목은 한 줄 요약으로 바꾸고, 핵심 결정과 상세 위치를 적는다.
     ```
     - [x] T8s. 버리기 깊이 태그별 분리 — PASS 11/12 · 결정: 깊이 태그별 · 상세: archive/TASKS-M2.md#T8s
     ```
     "결정" 칸은 evaluator가 REVIEW에 적은 핵심 결정 한 줄에서 가져온다. 에이전트가 요약을 쓰지 않는다.
  4. **결정(PLAN.md "자체 결정")은 아카이브하지 않는다.** 대신 짧게 유지한다. 한 결정은 1~2줄로 쓴다. 다른 결정으로 대체된 결정만 "폐기"로 표시하고 `docs/archive/DECISIONS-retired.md`로 옮긴다.
  5. **찾아보는 규칙을 프롬프트에 넣는다.** "현재 항목이 이전 항목 ID나 REVIEW 메모를 참조하면 `docs/archive/`에서 Grep으로 찾아 읽는다." 정보는 지워지지 않으므로, 위험은 "찾아봐야 한다는 사실을 모르는 것"이다. 3번의 단서와 이 규칙이 그 위험을 막는다.
- **검증 방법**: 아카이브 이후 REVIEW나 FAIL에 "이전 결정과 충돌", "기존 동작 회귀" 같은 지적이 나오는지 지켜본다. 나오면 아카이브 범위를 줄인다.

#### A5. 모델 기본값 — M
- **근거**: `run.py:37-38`에서 planner와 evaluator의 기본값이 opus다. 한 사이클 3회 호출 중 2회가 가장 비싼 모델이다.
- **v2 결정 (2026-11-24)**: 판단 역할인 planner만 opus로 두고, 나머지는 sonnet으로 내린다. 모델은 `harness.yml`에서 역할별로 바꿀 수 있다.

  | 역할 | v1 | v2 기본값 | 메모 |
  |---|---|---|---|
  | planner | opus | **opus** | 계획·항목 선정·종료 판정. 판단이 가장 많은 역할 |
  | generator | sonnet | sonnet | 변경 없음 |
  | evaluator | opus | **sonnet** | 테스트 실행·채점. ⚠️ 꼼꼼한 검수가 필요하다면 opus로 변경하는 것을 추천 |

  ```yaml
  # harness.yml
  models:
    planner: opus
    generator: sonnet
    # 테스트 실행·채점 역할. 비용 절감을 위해 sonnet으로 내렸다.
    # 꼼꼼한 검수가 필요하다면 opus로 변경하는 것을 추천한다.
    # (예: 보안·데이터 무결성이 중요한 프로젝트, sonnet 평가에서 놓친 결함이 반복될 때)
    evaluator: sonnet
  ```

- **확인 방법**: A2의 비용 기록과 REVIEW 점수, 이후 사이클에서 드러나는 결함(앞 사이클에서 PASS였던 항목의 FAIL·회귀)으로 evaluator를 sonnet으로 내린 영향을 본다. 놓친 결함이 늘면 opus로 되돌린다.

### B. 신뢰성

#### B1. `claude` 실패를 무시함 — H
- **근거**: `run.py:103-105`는 종료 코드를 로그만 남기고 다음 에이전트로 넘어간다. 한도 초과·인증 오류·네트워크 오류가 나도 planner→generator→evaluator가 계속 실행되어, 빈 사이클이 돌거나 문서가 어긋난다. Pro 5시간 한도에 걸린 지금 상황에서 가장 아픈 결함이다.
- **v2 제안**
  - 결과 JSON의 `is_error`가 `true`이면 그 사이클을 중단한다. 원인은 `subtype`으로 구분한다(A2의 필드 표). 종료 코드는 상한 도달과 오류가 모두 `1`이라 판정에 쓰지 않는다. 다만 JSON 자체가 없거나 파싱되지 않으면 오류로 본다.
    - `error_max_budget_usd`, `error_max_turns`: 상한 도달(A3). 재시도하지 않고 다음 사이클로 넘어간다.
    - 그 밖의 `error_*` 또는 `api_error_status`가 `null`이 아님: 실행 오류. 아래 규칙을 따른다.
  - 같은 오류가 연속 N회면 `HALT`에 오류 내용을 적는다.
  - 사용량 한도 오류는 재시도하지 않고 즉시 `HALT`한다.
  - `.cycle_count`는 사이클이 정상 완료된 경우에만 올린다.

#### B2. 서브프로세스 타임아웃이 없음 — M
- **근거**: `run.py:76`, `run.py:103`의 `subprocess.run`에 `timeout`이 없다. 에이전트가 멈추면 루프도 무한정 멈춘다.
- **v2 제안**: 에이전트별 타임아웃(예: 30분)을 둔다. 초과하면 프로세스 트리를 종료하고 B1의 실패로 처리한다.
- **Java 메모**: `Process.waitFor(timeout, unit)` 후 `destroyForcibly()`. Windows에서 `claude.cmd`는 자식 프로세스를 띄우므로 `ProcessHandle.descendants()`까지 종료해야 한다.

#### B3. 종료 판정 비용 — L
- **근거**: `planner.md:55`는 종료 판정 때 PRD 전체를 처음부터 다시 읽고 대조하라고 한다. 이 대조는 완료 직전, 문서가 가장 클 때 일어난다. 안전한 설계이므로 유지한다.
- **v2 제안**: 대조 결과를 `docs/COVERAGE.md`(PRD 요구 ↔ 항목·코드 대응표)로 남기고, PRD 해시가 같으면 이전 대조를 재사용한다.

### C. 권한·안전

#### C1. "읽기 전용"이 프롬프트로만 강제됨 — H
- **근거**: evaluator는 `run.py:190`에서 `Bash`를 패턴 없이 허용받는다. `Edit(docs/**)`로 편집 도구는 제한되지만 Bash로는 src/·tests/를 수정할 수 있다. generator도 `run.py:184`에서 Bash가 무제한이다.
- **v2 결정 ([0008](decisions/0008-strict-permissions.md)): 엄격**
  - planner는 Bash 없음(v1 유지).
  - generator는 빌드·테스트·의존성 추가 명령과 읽기 계열 명령만 허용한다.
  - evaluator는 테스트 명령 패턴만 허용한다. 예: `Bash(./gradlew test:*)`, `Bash(npm test:*)`.
  - 목록에 없는 것은 `--disallowedTools`로 막는다(플래그 존재 확인함). 허용 패턴은 D3의 `harness.yml`에서 생성한다.
  - 변이 검증이 필요하면 하네스가 임시 복사본 디렉터리를 만들어 주고, 그 경로에서만 쓰기를 허용한다.
  - 위험 명령 차단 훅(C2)을 2차 방어로 함께 쓴다.
- **위험과 완화**: 필요한 명령이 막혀 BLOCKED가 늘 수 있다. BLOCKED 사유에 "허용 목록에 없는 명령"이 반복되면 사람이 `harness.yml`의 허용 목록을 넓힌다.

#### C2. 무인 실행 + `acceptEdits`에 위험 명령 차단이 없음 — M
- **보류 ([0014](decisions/0014-defer-danger-hook.md))**: 스모크 테스트 뒤에 필요한지 다시 판단한다. 아래 v2 제안의 "하네스 시작 시 훅이 설치됐는지 확인하고 없으면 시작을 거부"는 철회했다(사람의 개입이 늘기 때문). 만든다면 하네스가 `--settings`로 넘긴다.
- **근거**: generator는 `run.py:185`에서 `acceptEdits`와 무제한 Bash로 무인 실행된다.
- **v2 제안**: 대상 프로젝트에 PreToolUse 훅을 설치한다. 4번 챕터의 `block-dangerous.sh`(재귀 강제 삭제, 종료 코드 2로 차단, fail-closed)를 재사용한다. 하네스 시작 시 훅이 설치됐는지 확인하고, 없으면 시작을 거부한다.

### D. 운영·이식성

#### D1. planner의 타임스탬프가 지어낸 값 — L
- **근거**: v1에서는 세 프롬프트가 각자 JOURNAL에 줄을 추가했다(`planner.md:99`, `generator.md:24`, `evaluator.md:46`). `run.py`는 JOURNAL을 건드리지 않는다. planner에는 Bash가 없어 현재 시각을 알 수 없으므로 `12:30:00` 같은 둥근 값이 찍혔다. 그 결과 실제 실행 순서와 시각 순서가 어긋난다. 예: generator `12:26:46` 다음 줄에 planner `12:35:00`.
- **v2 결정 ([0009](decisions/0009-harness-writes-journal.md)): 하네스가 기록**
  - 에이전트는 결과 JSON의 `result`에 요약 한 줄만 낸다.
  - 하네스가 실제 시각, 사이클 번호, 역할, 비용, 종료 사유를 붙여 기록한다.
    ```
    - 2026-11-24T12:26:46+09:00 [c12] generator: T7b 완료 (258 passed) · $1.20 · success
    ```
  - 프롬프트의 JOURNAL 쓰기 지시는 삭제한다.
  - A2의 비용 기록, D2의 출력 보관과 같은 지점(에이전트 실행 직후)에서 처리한다.

#### D2. 에이전트 출력을 보관하지 않음 — M
- **근거**: `run.py:103`은 출력을 캡처하지 않아 콘솔로만 흘러간다. 사이클을 나중에 되짚을 수 없다.
- **v2 제안**: `logs/cycle-{N}-{agent}.json`으로 원본 결과를 저장한다. A2의 비용 기록과 같은 지점에서 처리한다.

#### D3. Python/uv 명령이 프롬프트에 하드코딩됨 — H (v2 목적상)
- **근거**: `evaluator.md:20`(`uv run pytest -x`), `generator.md:19`(`uv run pytest -x`), `generator.md:32`(`uv add`).
- **v2 제안**
  - 대상 프로젝트에 하네스 설정 파일(예: `harness.yml`)을 두고 프롬프트에서 템플릿으로 치환한다. 설정 항목은 아래와 같다.
    - 테스트 명령: 전체 / 경로 지정
    - 빌드 명령
    - 의존성 추가 방법
    - 허용 Bash 패턴(C1)
    - 모델(A5)
    - 상한(A2·A3·B2)
  - 백엔드·프런트엔드처럼 여러 모듈인 프로젝트는 모듈별 명령을 둔다. 예: `backend: ./gradlew test`, `frontend: npm test`.

#### D4. 하네스 자체 테스트가 없음 — M
- **근거**: `run.py:118-149`의 `resolve_decisions`는 합의 / 재시도 / 3회 불발 HALT로 갈리는 상태 기계인데 테스트가 없다. `run.py:31`의 `ROOT = parse_args()`가 모듈 최상단에 있어 테스트하기도 어렵다.
- **v2 제안**
  - 경로·설정·`claude` 실행기를 생성자로 주입한다. 실행기는 인터페이스로 두고, 테스트에서는 가짜 실행기를 쓴다.
  - JUnit으로 다음을 테스트한다.
    - 결정 합의 상태 기계
    - DONE/HALT 처리
    - 비용 상한
    - 실패 처리(B1)
    - 사이클 카운터 이어받기

#### D5. 한 번에 처리하는 항목 수의 모순 — L
- **근거**: `planner.md:46`은 "다음 미완료 항목을 1~2개만 선정"하라고 하고, `generator.md:15`는 "첫 미완료 항목을 1개 선정"하라고 한다. 선정 주체가 둘이다.
- **v2 제안**: planner가 이번 사이클 항목 ID를 `docs/CURRENT`에 적고, generator와 evaluator는 그 ID만 처리·평가한다. 하네스가 파일 존재로 사이클 진행 여부를 판단할 수 있다.

## 3. Java 포팅 대응표

| v1 (Python) | v2 (Java) | 메모 |
|---|---|---|
| `subprocess.run(cmd, cwd=ROOT)` | `ProcessBuilder(cmd).directory(root)` + `waitFor(timeout)` | B2 타임아웃, stdout 캡처(D2) |
| `shutil.which("claude")` (커밋 `0c8e5d8`, 이후 `4119a9c`에서 제거) | Windows면 `claude.cmd`, 그 외 `claude`. 또는 PATH 탐색 유틸 | v1이 Windows에서 실행 실패를 겪은 지점. 재발 방지 테스트 필요 |
| `pathlib.Path`, `read_text/write_text` | `java.nio.file.Path`, `Files.readString/writeString(UTF_8)` | 인코딩을 항상 명시. Windows 기본 인코딩 문제 방지 |
| `os.environ.get` | 설정 파일 + 환경 변수 덮어쓰기 | D3 |
| `ROOT = parse_args()` (모듈 전역) | `main`에서 파싱 → `Harness(config, runner)` 생성자 주입 | D4 |
| `print(..., flush=True)` 로그 | 콘솔 + 파일 로거 | D2 |
| JSON 없음 | Jackson 또는 Gson | A2, B1 |
| `--append-system-prompt`(부트스트랩) | 동일 | 부트스트랩만 대화형이라 `inheritIO()` 사용 |

## 4. 우선순위

| 순위 | 항목 | 이유 |
|---|---|---|
| 1 | **A1** 보강 항목 규칙 | 프롬프트 몇 줄로 사이클을 가장 많이 줄인다 |
| 2 | **A2 + B1 + D2** 비용 기록·상한, 실패 시 중단, 출력 보관 | 모두 `run_agent`(실행기) 한 곳의 변경. 관측과 안전망을 한 번에 얻는다 |
| 3 | **A3** 1회 금액 상한, 평가 범위 제한 | 비용 폭주 방지 |
| 4 | **D3** 프로젝트별 명령 설정 | Java/Spring/Vue 프로젝트에 쓰려면 필수 |
| 5 | **A4** 문서 아카이브 | 장기 실행 비용 |
| 6 | **C1, C2** 권한 축소, 위험 명령 차단 | 무인 실행 안전 |
| 7 | **A5, B2, D4, D5** | 품질·유지보수 |
| 8 | **B3, D1** | 편의 |

## 5. 기술 결정

### 확정 (2026-11-24)

| 항목 | 결정 | 메모 |
|---|---|---|
| 빌드 | Gradle | JUnit·Jackson 의존성 관리 |
| JDK | 21 | record, switch 패턴 매칭 사용 가능 |
| JSON | Jackson | `claude -p --output-format json` 결과 파싱(A2·B1) |
| 설정 파일 | YAML | D3의 `harness.yml`. Jackson YAML 모듈(`jackson-dataformat-yaml`)로 읽으면 JSON과 같은 방식으로 다룰 수 있다 |
| 문서 아카이브 | 하네스가 마일스톤 완료 시 작업 지시만 이동, 결정은 유지 | A4 |
| 모델 기본값 | planner opus / generator sonnet / evaluator sonnet | A5. evaluator는 꼼꼼한 검수가 필요하면 opus로 변경 추천 |
| 비용 상한 | CLI 보고 비용 누적 $38 + 에이전트 1회 $5, 실행 전 차단 | A2·A3 ([0007](decisions/0007-cost-limit.md)) |
| REVIEW 메모 | BACKLOG에 기록, 마일스톤 끝에 결함성 항목 최대 2개만 처리 | A1 ([0010](decisions/0010-backlog-for-review-memos.md)) |
| 권한 | 엄격: 역할별 Bash 허용 목록 | C1 ([0008](decisions/0008-strict-permissions.md)) |
| JOURNAL | 하네스가 기록 | D1 ([0009](decisions/0009-harness-writes-journal.md)) |

### 미결정

없음.

## 6. 확인 필요 목록

- [x] `--max-budget-usd` 존재 (`claude --help`, `--print` 전용)
- [x] `--output-format json`, `--disallowedTools`, `--fallback-model` 존재
- [x] `--max-turns` 지원 (사용자 확인, help 출력에는 없음)
- [x] 구독 플랜의 실제 청구액은 하네스에서 계산 불가 → CLI 보고 비용의 누적으로 상한 판단, 첫 실행에서 보정 (A2)
- [x] JSON 결과의 토큰·비용·오류·종료 사유 필드명 (A2의 필드 표, 샘플은 `src/test/resources/claude-result/`)
- [x] `--max-budget-usd` 도달 시: `subtype: error_max_budget_usd`, `is_error: true`, 종료 코드 `1`. 상한을 턴 1회분 넘긴 뒤 멈춤
- [x] `--max-turns` 도달 시: `subtype: error_max_turns`, `is_error: true`, 종료 코드 `1`
- [x] 프롬프트를 표준 입력으로 전달 (9,300자 확인), `--disallowedTools`가 허용 패턴보다 우선, 허용 목록 밖 쓰기 명령은 거부·읽기 전용 명령은 통과 (0008 확인 결과)
- [ ] 사용량 한도 도달 시 `claude -p`의 출력 형태 (B1 판정 기준). 일부러 재현할 수 없다. 처음 발생할 때 `logs/`의 원본(D2)으로 확인하고 샘플에 추가한다. 그 전까지는 "알 수 없는 `error_*`"로 처리한다
- [ ] 첫 실행 보정: 크레딧 감소량과 `USAGE.csv` 합계를 비교한다. 스모크 테스트(0011)로 하고, Pro 한도를 다 쓴 상태에서 해야 비교가 된다 (A2, 0007)
