# todo-cli

터미널에서 할 일을 추가하고 진행 상태를 관리하는 간단한 Java CLI입니다.

## 요구 사항

- JDK (Gradle Wrapper 포함, 별도 Gradle 설치 불필요)

## 실행 방법

이 디렉터리(`chapter2/todo-cli`)에서 Gradle로 실행합니다.
Windows PowerShell은 `.\gradlew.bat`, Git Bash 등은 `./gradlew`를 사용합니다.

```
./gradlew run --args="<명령> [인자]"
```

## 명령어

| 명령 | 설명 |
|---|---|
| `add <제목>` | 할 일 추가 (제목에 공백이 있어도 됨) |
| `list` | 목록 보기 |
| `start <id>` | 진행 시작 (`할 일` 상태에서만 가능) |
| `done <id>` | 완료 처리 (이미 완료된 항목은 오류) |

### 사용 예

```
$ ./gradlew run --args="add 장보기"
추가됨: [1] (할 일) 장보기
$ ./gradlew run --args="add 운동하기"
추가됨: [2] (할 일) 운동하기
$ ./gradlew run --args="start 2"
시작됨: [2] (진행 중) 운동하기
$ ./gradlew run --args="done 1"
완료됨: [1] (완료) 장보기
$ ./gradlew run --args="list"
[O] 1 장보기
[=] 2 운동하기
```

## 상태 표시

`list`는 상태별로 기호와 색을 다르게 보여줍니다.

| 상태 | 기호 | 색 |
|---|---|---|
| 할 일 | `[]` | 노랑 |
| 진행 중 | `[=]` | 청록 |
| 완료 | `[O]` | 초록 |

- 색은 터미널에 직접 출력할 때만 적용됩니다. 파이프/리다이렉트로 출력하거나 `NO_COLOR` 환경변수가 설정되어 있으면 색 없이 출력합니다.
- `gradlew run`은 출력이 파이프로 연결되므로 `build.gradle.kts`에서 `-Dtodo.color=true`로 색을 강제합니다. (`NO_COLOR`가 우선)

## 데이터 저장

- 할 일은 실행한 디렉터리의 `todos.json`에 저장됩니다. (Git에서는 제외됨)
- Gradle로 실행하면 이 프로젝트 디렉터리가 작업 디렉터리입니다.

## 오류 처리

잘못된 명령, 숫자가 아닌 id, 존재하지 않는 id, 허용되지 않는 상태 전이는 `오류: ...` 메시지를 표준 에러로 출력하고 종료 코드 1로 끝납니다.

## 테스트

```
./gradlew test
```

## 구조

- `Main` — CLI 입출력(인자 파싱, 출력, 색상)
- `TodoList` — 목록 조작 순수 로직
- `TodoStore` — JSON 파일 저장/로드
- `Todo`, `Status` — 데이터 모델
