# 0003. 기술 스택: Gradle, JDK 21, Jackson, YAML

- 상태: 확정
- 날짜: 2026-11-24

## 맥락
- v2에는 세 가지가 필요하다.
  - `claude -p --output-format json` 결과를 파싱하는 JSON 처리(IMPROVEMENTS A2, B1)
  - 프로젝트별 명령·모델·상한을 담는 설정 파일(D3)
  - 하네스 자체 테스트(D4)

## 결정

| 항목 | 결정 | 이유 |
|---|---|---|
| 빌드 | Gradle | JUnit·Jackson 의존성 관리 |
| JDK | 21 | record, switch 패턴 매칭 |
| JSON | Jackson | 결과 JSON 파싱 |
| 설정 파일 | YAML (`harness.yml`) | 모듈별 중첩 설정(예: backend/frontend 명령)을 표현하기 쉽다. `jackson-dataformat-yaml`로 읽으면 JSON과 같은 방식으로 다룰 수 있다 |

## 검토한 대안
- **단일 파일 `java Harness.java`**: 빌드 도구가 없어 가장 간단하지만, 외부 라이브러리와 JUnit을 쓰기 어렵다.
- **Maven**: 가능하지만 Gradle을 선택했다.
- **JDK 17**: LTS지만 21의 언어 기능을 쓰지 못한다.
- **Gson**: Jackson 하나로 JSON과 YAML을 함께 처리할 수 있어서 Jackson을 택했다.
- **TOML / properties**: properties는 의존성이 없지만 중첩 설정이 어렵다.

## 영향
- Jackson은 모르는 키를 무시(`@JsonIgnoreProperties(ignoreUnknown = true)`)하게 한다. 필수 키가 없으면 예외를 던진다(0007).
