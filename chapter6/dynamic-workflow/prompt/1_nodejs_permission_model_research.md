# 1_nodejs_permission_model_research

## 프롬프트

슬래시 커맨드 `/deep-research`

```
/deep-research node.js 20과 22 사이에서 권한 모델이 어떻게 달라졌는지 공식문서를 중심으로 조사해줘.
```

확장된 프롬프트: deep-research 워크플로 실행 지시. 질문이 충분히 구체적이어서 추가 질문 없이 다음 args로 구체화해 호출했다.

```
Workflow({ name: "deep-research", args: "node.js 20과 22 사이에서 권한 모델(Permission Model, --experimental-permission → --permission, --allow-fs-read/--allow-fs-write/--allow-child-process/--allow-worker 등)이 어떻게 달라졌는지 Node.js 공식문서와 릴리스 노트를 중심으로 조사해줘. 답변은 한국어로 작성." })
```

워크플로 단계: Scope(5개 검색 각도) → Search(5개 병렬) → Fetch(상위 15개 출처 claim 추출) → Verify(claim당 3표 적대적 검증) → Synthesize(중복 병합, 신뢰도 순위, 출처 인용)

## 답변

### 실행 과정 (순차 요약)
1. 워크플로를 백그라운드로 실행했다 (Run ID `wf_06ee6fb5-406`).
2. 서브에이전트 104개가 약 4분 17초 동안 작업했고, 오류는 0건이었다.
3. 검증을 통과한 claim 6건과 반박된 claim 5건이 나왔다.
4. 완료 후 결과를 한국어로 정리해 보고했다.

### 결론
권한 모델은 Node 20.0.0에 실험 기능으로 추가되었다. 22 초기 버전도 같은 실험 상태였고, **v22.13.0(및 v23.5.0)에서 Stable(Stability 2)로 승격**되었다.

| 항목 | Node 20 | Node 22.0~22.12 | Node 22.13+ |
|---|---|---|---|
| 안정성 | 1.1 (Active development) | 1.1 | 2 (Stable) |
| 활성화 플래그 | `--experimental-permission` | `--experimental-permission` | `--permission` (현행 문서) |
| 모드 | enforce | enforce | enforce(기본) + `--permission-audit`(감사) |

- **감사 모드:** `--permission-audit`은 위반을 diagnostics channel로 발행하고 접근은 막지 않는다. 둘을 함께 주면 `--permission`이 우선한다.
- **허용 플래그 확장:**
  - v20.0.0: `--allow-fs-read`, `--allow-fs-write`, `--allow-child-process`, `--allow-worker`
  - `--allow-addons`: v20.12.0 / v21.6.0에 추가
  - `--allow-wasi`: v22.3.0에 추가
  - 현행 문서에는 `--allow-net`, `--allow-ffi`, `--allow-openssl-store`도 있다. 도입 버전은 미확인이다.
- **파일시스템 권한:** `*` 또는 쉼표로 구분한 경로를 받는다. 와일드카드 뒤의 문자는 무시된다. 프로세스 생성과 워커 생성은 별도 플래그로 분리되어 있다.
- **구 플래그 제거:** `--experimental-permission` 제거는 v24.0.0(PR #56240, semver-major)에서 이루어졌다. 20→22 구간의 변화가 아니다.

### 주의사항
- 플래그가 v22.13.0에서 개명되었다는 부분은 공식 변경이력의 직접 인용이 아니라, 안정화 항목과 버전별 문서를 비교한 추론이다.
- 22.13 이후 구 플래그가 별칭으로 동작했는지는 확인하지 못했다.
- 일부 하위 플래그(child-process, worker, wasi, addons)는 stable 승격 이후에도 cli.html에서 1.1로 표기된다는 보고가 있다.
- 일부 출처는 nightly/test 빌드 문서이며, 문서는 시점에 따라 달라질 수 있다.
- 반박된 주장은 제외했다. v22.0.0 문서에 inspector가 포함된다는 주장과, v24.0.0에서 개명되었다는 서술이 해당한다.

### 주요 출처
- https://nodejs.org/api/permissions.html
- https://nodejs.org/dist/latest-v22.x/docs/api/cli.html
- https://nodejs.org/en/blog/release/v24.0.0
- https://nodejs.org/download/release/v22.0.0/docs/api/permissions.html
- https://r2.nodejs.org/docs/v22.8.0/api/permissions.html

### 원본 결과 위치
`/private/tmp/claude-501/-Users-okh-marvin-workspace-2026-ai-loop-engineering-practice-chapter6-dynamic-workflow/d13bb126-7e11-44bd-90cd-9546393126b7/tasks/wh1whxgks.output`
