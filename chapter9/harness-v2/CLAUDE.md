# harness-v2

v1 3-Agent 루프 하네스(`chapter9/harness`, Python)를 **Java 개발자가 읽고 고칠 수 있는 코드**로 다시 작성하는 프로젝트다.
기능을 늘리는 것이 목적이 아니다. v1의 동작을 옮기면서 v1에서 드러난 결함을 고친다. 근거는 `docs/decisions/0002`다.

## 먼저 읽을 것 (순서대로)
README.md의 "1년 뒤 읽는 순서"와 같다.
1. `README.md`: 폴더 구조, 실행 흐름(메서드 이름 포함). 하네스를 쓰는 방법(새 프로젝트 적용, `harness.yml`, HALT 재개, 완료 확인, 개선)은 `docs/USER_GUIDE.md`에 있다
2. `docs/STATUS.md`: 지금 어디까지 했고 다음에 무엇을 할지
3. `docs/decisions/README.md`: 사용자와 합의한 결정 목록(0001~0017). 결정의 이유는 각 파일에 있다
4. `docs/DESIGN.md`: v2 클래스 구조, `harness.yml` 스키마, 하네스와 프롬프트가 공유하는 파일 형식(4절), 메인 루프(6절), 테스트
5. `docs/IMPROVEMENTS.md`: v1 결함과 v2 개선 항목(A1~D5), 우선순위(4절), 미확인 항목(6절)
6. v1 원본(필요할 때)
   - `chapter9/harness/src/harness/run.py`: 루프, `DONE`/`HALT`, 결정 합의
   - `chapter9/harness/src/harness/prompts/*.md`: planner, generator, evaluator, planner_bootstrap 프롬프트
   - `chapter9/projects/rss-wiki/docs/`: v1 실행 기록(JOURNAL, REVIEW, TASKS)
   - `chapter9/projects/pomodoro-todo/docs/`: v2 실행 기록(JOURNAL, USAGE.csv, REVIEW, BACKLOG, TASKS, archive/). v2로 25사이클을 돌려 `DONE`까지 간 사례
   - `chapter9/projects/loop-check/`: 합의 불발 HALT·재개와 FAIL 재작업을 확인하려고 만든 작은 검증 프로젝트. 시나리오는 `scenario/SCENARIO.md`, 실행 기록은 `docs/`. 15사이클, FAIL은 유도하지 못했다

## 기술 스택
Gradle, JDK 21, Jackson(JSON과 YAML), 설정 파일 `harness.yml`. 근거는 `docs/decisions/0003`이다.
패키지 구성과 실행 흐름은 `README.md`에 있다.

## 명령어 (`chapter9/harness-v2`에서 실행)
- `./gradlew test`: 단위 테스트. 가짜 claude를 쓰므로 무료다. 단계가 끝날 때마다 통과를 확인한다.
- `$env:HARNESS_SMOKE = "1"; ./gradlew smokeTest`: 실제 claude로 샘플 프로젝트를 돌린다. **유료**(약 $0.05). 사용자 승인 없이 실행하지 않는다.
- `$env:HARNESS_REAL_CLAUDE = "1"; ./gradlew test --tests harness.claude.RealClaudeCheckTest`: 실제 CLI 동작 확인. **유료**(약 $0.014). 마찬가지로 승인을 받는다.
- 대상 프로젝트 실행(루프)은 **유료**이고 사용자가 터미널에서 직접 돌린다. 내가 돌리지 않는다.
  - 실행은 `installDist`로 통일한다. `./gradlew installDist` 후 터미널에서 직접 실행한다. 하네스 코드를 바꿨으면 실행 전에 `installDist`를 다시 한다.
    - Windows: `build\install\harness-v2\bin\harness-v2.bat ..\projects\<project>`
    - macOS/Linux: `build/install/harness-v2/bin/harness-v2 ../projects/<project>` (코드를 읽어 문제없다고 판단했을 뿐 실제로 돌려 보지는 않았다)
  - `./gradlew run`은 안내하지 않는다. 터미널 입력을 연결하지 않아 PRD 없는 Bootstrap(대화형 `claude`, TTY 필요)이 실패하고, Claude Code의 `!`도 마찬가지일 가능성이 높다. 일반 루프는 되지만 DONE·HALT 종료 코드가 `BUILD FAILED`로 보인다.
- 실행 결과를 점검할 때는 `projects/<project>/docs/`의 JOURNAL, USAGE.csv, REVIEW, BACKLOG, TASKS와 `.harness/`를 읽고, 사이클 순서·합의 이행·역할별 책임을 본다. 점검에서 나온 수정은 `docs/STATUS.md`에 기록한다.

## 작업 규칙
- **v1은 수정하지 않는다.** `chapter9/harness/`와 `chapter9/projects/rss-wiki/`는 기록용이다. 프롬프트도 v2로 복사한 뒤 고친다.
- **결정은 사용자가 내린다.**
  - 결정이 필요한 일은 내 의견과 근거를 먼저 설명한다. 사용자가 결정한 뒤 진행한다.
  - 사용자가 "답변만"이라고 하면 작업하지 않는다.
- **결정 기록**
  - 새 결정은 `docs/decisions/{번호}-{주제}.md`에 남기고 README 목차를 갱신한다.
  - 결정을 바꿀 때는 기존 파일을 지우지 않는다. 상태를 `대체됨(→ 새 번호)`으로 바꾸고 새 파일을 만든다.
  - `IMPROVEMENTS.md`의 해당 항목도 함께 갱신한다.
- **진행 상태**: 작업 단위가 끝날 때마다 `docs/STATUS.md`를 갱신한다. 진행 상태는 이 파일(CLAUDE.md)에 적지 않는다.
- **README 유지**: 클래스·패키지·실행 흐름이 바뀌면 `README.md`의 폴더 설명과 "실행 흐름"도 함께 고친다. 메서드 이름이 틀리면 1년 뒤 길잡이 역할을 못 한다.
- **보류한 훅**: Bash 허용 목록 훅(0013)과 위험 명령 차단 훅(0014)은 사용자가 보류하기로 했다. 사용자가 다시 정하기 전에는 만들지 않는다.
- **비용에 민감하다.**
  - 사용자는 Pro 플랜에 남은 크레딧이 한정적이다.
  - `claude -p` 실행처럼 사용량을 쓰는 작업은 미리 알리고 진행한다.
  - **비용 때문에 범위나 검증을 줄이고 싶으면 스스로 정하지 않는다.** 비용과 효과(무엇을 못 확인하게 되는지)를 함께 보여 주고 사용자의 결정을 받는다(0011).
  - 서브에이전트는 요청이 있을 때만 쓴다.
- **Git**
  - 브랜치: `feat/chap9-harness-v2`. `feat/chap9-harness-setup`에서 분기했고, 둘 다 main에 병합하지 않았다.
  - 커밋 메시지: `type(scope): 한글 설명`. 예: `docs(harness-v2): ...`
  - 커밋과 푸시는 사용자가 요청할 때만 한다. PR은 만들지 않는다.

## 사용자
- Java 개발자이고 Python 문법에 익숙하지 않다.
- 코드는 읽기 쉽게 쓴다. 영리한 축약보다 명확한 이름과 구조를 우선한다.
- 설명은 Java 개념에 빗대어 한다.
- 답변은 한국어로, 짧게 한다. 사용자가 냉정한 평가를 원할 때는 듣기 좋은 말보다 근거 있는 판단을 준다.
