# 0002. 하네스를 Java로 다시 작성(v2)

- 상태: 확정
- 날짜: 2026-11-24

## 맥락
- v1 하네스(`chapter9/harness/src/harness/run.py`, 208줄)는 실습 때문에 Python으로 작성했다. 사용자는 Java 개발자이고 Python 문법에 익숙하지 않다.
- 하네스가 하는 일은 세 가지뿐이다. 서브프로세스 실행(`claude -p`), `docs/` 파일 읽기·쓰기, 루프와 종료 신호 확인이다. 언어에 의존하는 부분이 없다. 핵심은 프롬프트 4개와 파일 규약이다.
- v1 평가는 10점 만점에 약 7점이었다(실습용 기준). 역할·권한 분리는 좋았지만 비용 통제·관측(3점)과 오류 처리(4점)가 약했다.

## 결정
- 하네스를 **Java로 다시 작성해 v2**를 만든다. 위치는 `chapter9/harness-v2`다.
- 목표는 **Java 개발자가 읽고 고칠 수 있는 하네스**다. 기능을 늘리기보다 v1의 동작을 옮기면서 `IMPROVEMENTS.md`의 결함을 고친다.
- 프롬프트 4개(planner, generator, evaluator, planner_bootstrap)와 파일 기반 상태 규약(`DONE`, `HALT`, `.cycle_count`, 블라인드 결정 합의)은 유지한다.

## 검토한 대안
- **Python 유지 + Java 개념에 빗댄 주석 추가**: 코드는 안정적이지만 사용자가 직접 고쳐 가며 쓰기 어렵다.
- **Node.js/TypeScript**: 분량은 Python과 비슷하지만 사용자의 주력 언어가 아니다.
- **Agent SDK 사용**: 비용 정보를 객체로 받을 수 있지만, `claude -p --output-format json`으로도 같은 정보를 얻을 수 있어 필수가 아니다.

## 영향
- 이미 38사이클로 검증된 코드를 다시 쓰므로 새로운 버그가 생길 수 있다. 그래서 v2는 JUnit 테스트를 갖춘다(IMPROVEMENTS D4).
- 하네스 언어와 대상 프로젝트 언어는 서로 독립이다. 프롬프트의 `uv run pytest` 같은 명령은 프로젝트 설정으로 분리한다(IMPROVEMENTS D3).
