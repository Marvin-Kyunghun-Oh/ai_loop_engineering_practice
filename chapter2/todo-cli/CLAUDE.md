# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

`todo-cli`는 책 "요즘 AI 루프 엔지니어링"의 실습 로그 저장소(`ai_loop_engineering_practice`) 중 chapter2 실습 프로젝트입니다. 현재는 Gradle `init`으로 생성된 뼈대만 있고 소스 코드(`src/`)는 아직 없습니다.

- 상위 저장소의 git 루트는 `ai_loop_engineering_practice/`이며, 이 디렉터리(`chapter2/todo-cli`)는 독립된 Gradle 프로젝트입니다. Gradle 명령은 반드시 이 디렉터리에서 실행합니다.
- chapter1(`../../chapter1/quote-cli`)은 Gradle 없이 단일 `Quote.java` + `QuoteTest.java` 구조였고, `prompt/` 폴더에 단계별 프롬프트(구현 → 테스트 작성 → README 작성)를 기록하는 방식을 썼습니다. 같은 워크플로를 따를 가능성이 높습니다.

## 빌드 및 테스트 명령

Gradle Wrapper(Gradle 9.8.2)를 사용합니다. Windows PowerShell에서는 `.\gradlew.bat`, Git Bash에서는 `./gradlew`를 사용합니다.

```
./gradlew build                              # 컴파일 + 테스트
./gradlew test                               # 전체 테스트
./gradlew test --tests "ClassName"           # 특정 테스트 클래스만
./gradlew test --tests "ClassName.method"    # 단일 테스트 메서드
```

## 빌드 구성

- Java 플러그인만 적용(`build.gradle.kts`), 의존성은 JUnit 5(`junit-bom:5.11.4`, Jupiter)뿐입니다. `application` 플러그인과 `mainClass`는 아직 설정되지 않아 `./gradlew run`은 동작하지 않습니다. CLI 진입점을 추가하려면 `application` 플러그인을 먼저 추가해야 합니다.
- `gradle.properties`에서 configuration cache가 켜져 있습니다(`org.gradle.configuration-cache=true`). 빌드 스크립트에 캐시와 호환되지 않는 코드를 넣지 않도록 주의합니다.
- `gradle/libs.versions.toml`(버전 카탈로그)은 비어 있으며, 현재 의존성 버전은 `build.gradle.kts`에 직접 적혀 있습니다.
- 표준 Gradle 레이아웃을 따릅니다: `src/main/java`, `src/test/java`.

## 개발 규칙

- 패키지 관리와 실행은 gradle로 한다.
- 기능을 추가하면 gradle test를 꼭 통과시킨다.
- CLI 입출력과 순수 로직(목록 조작)은 파일을 나눈다.
- 모든 문서작성과 주석은 한국어로 작성한다.
- 내가 `(프롬프트)`라는 키워드를 넣으면, 해당 프롬프트를 있는 그대로 `/prompt/seq_{어떤요청인지 요약한 제목}.md`에 보관한다.
  - 제목은 에이전트가 요약하되, 문장이 아닌 `단어 + '_'`의 조합으로 생성한다.(영어로)
  - seq는 1부터 채번된 문서번호