# 0008. 권한: 역할별 Bash 허용 목록(엄격)

- 상태: 확정
- 날짜: 2026-11-24

## 맥락
- v1은 generator(`run.py:184`)와 evaluator(`run.py:190`)에게 Bash를 패턴 없이 허용했다.
- evaluator는 `Edit(docs/**)`로 편집 도구가 제한되지만, Bash로는 `src/`·`tests/`를 수정할 수 있다. "읽기 전용"은 프롬프트로만 강제됐다.
- generator는 `--permission-mode acceptEdits`와 무제한 Bash로 무인 실행됐다. 위험 명령을 막는 장치가 없었다.

## 결정
역할별 허용 목록을 `harness.yml`에서 생성해 `--allowedTools`로 넘긴다. 목록에 없는 것은 `--disallowedTools`로 막는다.
- 보완(2026-11-24 확인 결과): `--disallowedTools Bash`는 허용 패턴보다 우선해 허용 명령까지 막는다. 그래서 Bash 패턴이 있는 역할은 허용 목록만 넘기고, 패턴이 없는 역할(planner)만 `--disallowedTools Bash`를 받는다. 아래 "확인 결과"를 본다.

| 역할 | Bash 허용 범위 |
|---|---|
| planner | 없음 (v1 유지) |
| generator | 빌드·테스트·의존성 추가 명령, 읽기 계열 명령 |
| evaluator | 테스트 명령만 |

```yaml
# harness.yml (예시. 명령은 대상 프로젝트에 맞게)
commands:
  test: "./gradlew test"
  build: "./gradlew build"
  add_dependency: null        # 의존성은 build.gradle 편집으로 추가
permissions:
  generator_bash:
    - "Bash(./gradlew build:*)"
    - "Bash(./gradlew test:*)"
    - "Bash(git status:*)"
    - "Bash(git diff:*)"
  evaluator_bash:
    - "Bash(./gradlew test:*)"
```

- 변이 검증이 필요하면 하네스가 임시 복사본 디렉터리를 만들어 주고, 그 경로에서만 쓰기를 허용한다.
- 위험 명령 차단 훅(IMPROVEMENTS C2, 4번 챕터의 `block-dangerous.sh`)을 함께 쓴다. 허용 목록이 1차 방어, 훅이 2차 방어다.

## 검토한 대안
- **느슨: 위험 명령만 차단**: 에이전트가 자유롭게 일할 수 있지만, evaluator가 코드를 고칠 수 있는 구멍이 남는다.
- **v1 그대로**: 역할 분리가 프롬프트에만 의존한다.

## 영향과 위험
- 필요한 명령이 막혀 BLOCKED가 늘 수 있다. 예: 파일 검색, 특정 스크립트 실행.
- **완화**: BLOCKED 사유에 "허용 목록에 없는 명령"이 반복되면 `harness.yml`의 허용 목록을 넓힌다. 넓히는 판단은 사람이 한다.
- 허용 패턴의 정확한 문법(`Bash(명령:*)`)은 구현 시 CLI 문서로 확인한다. → 확인함(아래).
- **엄격함의 한계(확인함)**: 읽기 전용 명령(`whoami` 등)은 허용 목록에 없어도 실행된다. 파일을 바꾸는 명령은 막히므로 "evaluator가 코드를 고치는 구멍"은 닫힌다. 다만 "허용한 명령만 실행된다"는 아니다.

## 확인 결과 (2026-11-24)
haiku로 4회 실행해 확인했다. 비용은 합계 약 $0.014다. 확인 코드는 `src/test/java/harness/claude/RealClaudeCheckTest.java`이고, 평소에는 건너뛴다(`HARNESS_REAL_CLAUDE=1`일 때만 실행).

| 설정 | 요청한 명령 | 결과 |
|---|---|---|
| allowed `Bash(echo:*)` + disallowed `Bash` | `echo harness-ok` | **막힘**. Bash 도구 자체가 빠져 `permission_denials`에도 남지 않음 |
| allowed `Bash(echo:*)`만 | `echo harness-ok` | 실행됨 (패턴 문법 `Bash(명령:*)` 확인) |
| allowed `Bash(echo:*)`만 | `touch should-not-exist.txt` | **거부됨**. 파일 생성 안 됨, `permission_denials`에 기록 |
| allowed `Bash(echo:*)`만 | `whoami` | **실행됨**. 사용자 설정에 허용 규칙이 없으므로 CLI가 읽기 전용 명령을 자동 허용하는 것으로 보인다 |

