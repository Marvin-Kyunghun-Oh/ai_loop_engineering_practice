# loop-check 검증 시나리오

하네스 v2의 두 가지를 실제 claude로 확인한다. 둘 다 pomodoro-todo 25사이클에서 한 번도 나오지 않았다.
- **A. FAIL → 재작업 루프**
- **B. 합의 불발 HALT** (STATUS "확인하지 못한 것" 2·3번)

모델: planner·generator haiku, evaluator sonnet. 상한은 `max_total_usd: 3`. 예상 비용은 합쳐서 $0.5~1.5이다(추정).

실행은 `chapter9/harness-v2`에서 한다. 하네스 코드를 바꿨으면 `./gradlew installDist`를 먼저 한다.
```
build\install\harness-v2\bin\harness-v2.bat ..\projects\loop-check
```

## 1단계: A (FAIL 재작업)
`docs/PRD.md` 그대로 실행한다(`max_iterations: 3`, 실행 한 번에 3사이클). 3사이클 안에 PASS까지 가지 못하면 같은 명령으로 다시 실행해 이어간다.

기대 흐름
| 사이클 | 기대 |
|---|---|
| c1 | T1 구현 → evaluator **FAIL**(15점 만점 6점 미만) |
| c2 | planner가 재작업 항목을 만들고 `docs/CURRENT`에 적는다. generator가 REVIEW 메모를 반영한다 |
| c3 이후 | PASS 또는 조건부. 마일스톤이 마감되거나 `DONE`이 생긴다 |

확인할 것
- `.harness/reviews.csv`에서 FAIL 줄 뒤에 같은 항목(또는 후속 항목)의 PASS·조건부 줄이 이어지는가
- FAIL 다음 사이클의 `CURRENT`가 재작업 항목인가, generator 보고가 REVIEW 메모를 언급하는가
- FAIL인 REVIEW에서 마일스톤이 마감되지 않았는가
- 메모의 `[결함]`·`[보강]` 분류와 BACKLOG 반영

FAIL이 한 번도 안 나오면: PRD M1 2번에 실패 입력을 더 추가해 재실행한다. 그 자체가 "이 수준에서는 FAIL이 안 난다"는 결과다.

## 2단계: B-1 (합의 불발 HALT, 결정적 재현)
A가 끝난 뒤에 한다.

1. `docs/PRD.md`를 `scenario/stage-b/PRD.md`로 덮어쓴다(M2와 "미해결 의사결정"이 추가됨).
2. `scenario/stage-b/decisions/` 안의 두 파일을 `docs/decisions/`로 복사한다.
   - `storage.md`: 이미 "합의 불발"이 2회 적혀 있다. 다음에 어긋나면 3회째라 HALT가 된다.
   - `storage.planner.md`: `선택: A`(JSON). PRD는 "스프레드시트로 연다"를 가장 중요한 기준으로 적어 두었으므로 evaluator는 B(CSV)를 고를 가능성이 높다.
3. `docs/DONE`이 있으면 지우고 실행한다. 3사이클이면 충분하다.

기대: evaluator가 `storage.evaluator.md`에 `선택: B`를 쓰고 → 사이클 끝에서 `docs/HALT`(`결정 합의 3회 불발: storage`) 생성.

확인할 것
- `docs/HALT`가 4줄 형식이고 `상세`에 planner·evaluator 선택 전문이 있는가
- evaluator가 `storage.planner.md`를 열지 않고 선택했는가(`.harness/logs/c{N}-evaluator.json`에서 도구 호출 확인)
- `storage.planner.md`·`storage.evaluator.md`가 하네스에 의해 지워졌는가
- 만약 evaluator도 A를 골라 합의가 났다면 그 자체가 결과다. "합의 성공" 경로를 실제 프롬프트로 처음 본 것이다

## 3단계: 재개
1. `docs/decisions/storage.md` 끝에 `합의: B`를 적는다.
2. `docs/HALT`를 지우고 다시 실행한다.

확인할 것
- 카운터가 이어지는가(같은 사이클 번호부터 재개). 합의 불발 HALT는 에이전트가 쓴 HALT처럼 카운터를 저장한다
- planner가 PRD에 `(자체 결정: 합의)`와 함께 B를 반영하는가
- `docs/decisions/storage*`가 정리되는가(planner에 Bash가 없어 못 지울 수 있다. 알려진 한계)
- M2가 CSV로 구현되는가

## 결과 기록
끝나면 `docs/JOURNAL.md`, `docs/USAGE.csv`, `.harness/reviews.csv`, `docs/HALT`를 알려 주면 점검해서 `docs/STATUS.md`에 반영한다.

## 4단계: 0017 확인 (evaluator의 결정 절차 누락 수정)
1사이클만 돈다(`max_iterations: 1`, 약 $0.15). 끝나면 `max_iterations`를 3으로 되돌린다.

준비(이미 적용됨): `docs/PRD.md`에 M3(`total_minutes`, `format_duration`)와 미해결 의사결정 `format-style`을 추가했고, `docs/decisions/`에 `format-style.md`, `format-style.planner.md`(`선택: A`)를 심었다. 이전 PRD는 `scenario/PRD-stage-b-after-run.bak.md`, 심은 파일의 원본은 `scenario/stage-c/decisions/`에 있다. `storage.md`(합의 B 완료)는 일부러 남겨 두었다.

PRD는 왕복(`parse_duration(format_duration(n)) == n`)을 가장 중요한 기준으로 두므로 A가 분명한 답이다. 그래서 evaluator도 A를 고르면 **합의 성공**(실제 프롬프트로는 처음)이 나야 한다.

기대: c13에서 planner가 결정과 무관한 `total_minutes` 항목을 고르고(`format_duration`은 합의 전 착수 금지), evaluator가 **그 사이클에** `format-style.evaluator.md`를 쓴다. 사이클 끝에 `format-style.md`에 `합의: A`가 붙는다.

확인할 것
- `.harness/logs/c13-evaluator.prompt.md`의 "대기 중인 결정"에 `format-style`만 있고 `storage`는 없는가. `.planner.md` 이름이 노출되지 않았는가
- evaluator가 첫 사이클에 선택을 썼는가(이전에는 3사이클 중 2번 놓쳤다)
- `합의: A`가 붙고 선택 파일이 지워졌는가. 다음 사이클 planner가 PRD에 `(자체 결정: 합의)`로 반영하는가(다음 실행 때)
- 평가 대상 항목에 `[결함]`이 붙었다면 근거가 있고 PRD가 허용하는 동작이 아닌가(0017의 2번)
