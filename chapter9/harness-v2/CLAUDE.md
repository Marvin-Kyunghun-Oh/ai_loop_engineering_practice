# harness-v2

v1 3-Agent 루프 하네스(`chapter9/harness`, Python)를 **Java 개발자가 읽고 고칠 수 있는 코드**로 다시 작성하는 프로젝트다.
기능을 늘리는 것이 목적이 아니다. v1의 동작을 옮기면서 v1에서 드러난 결함을 고친다. 근거는 `docs/decisions/0002`다.

## 먼저 읽을 것 (순서대로)
1. `docs/STATUS.md`: 지금 어디까지 했고 다음에 무엇을 할지
2. `docs/decisions/README.md`: 사용자와 합의한 결정 목록(0001~). 결정의 이유는 각 파일에 있다
3. `docs/IMPROVEMENTS.md`: v1 결함과 v2 개선 항목(A1~D5), 우선순위(4절), 미확인 항목(6절)
4. `docs/DESIGN.md`: v2 클래스 구조, `harness.yml` 스키마, 하네스와 프롬프트가 공유하는 파일 형식(4절), 메인 루프, 테스트, 구현 순서
5. v1 원본(필요할 때)
   - `chapter9/harness/src/harness/run.py`: 루프, `DONE`/`HALT`, 결정 합의
   - `chapter9/harness/src/harness/prompts/*.md`: planner, generator, evaluator, planner_bootstrap 프롬프트
   - `chapter9/projects/rss-wiki/docs/`: v1 실행 기록(JOURNAL, REVIEW, TASKS)

## 기술 스택
Gradle, JDK 21, Jackson(JSON과 YAML), 설정 파일 `harness.yml`. 근거는 `docs/decisions/0003`이다.

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
