# llmops_lab 프로젝트 지침

## 프로젝트 개요
고객 문의 1건을 Claude(`claude -p`)로 처리하고, 답변 품질·비용·지연을 **Langfuse에 trace/score로 기록**하는 실습 프로젝트.
목적은 프롬프트 품질을 "감"이 아니라 "측정 가능한 숫자"로 비교하는 것. 상세 흐름과 사용법은 `README.md` 참고.

## 구조와 처리 흐름
`process_ticket`(`app/service.py`)이 총괄: 프롬프트 렌더링 → trace → generation(Claude 호출) → evaluator(평가) → score → 로컬 JSONL 기록.

| 파일 | 역할 |
|---|---|
| `app/prompting.py` | `SupportTicket`, `render_prompt` (템플릿: `prompts/support_answer.md`) |
| `app/claude_runner.py` | `run_claude`, `ClaudeResult` — claude CLI 호출 |
| `app/evaluator.py` | `evaluate`, `EvalResult` — 규칙 기반 평가 (키워드·형식·길이) |
| `app/langfuse_ops.py` | Langfuse trace/generation/evaluator/score 전송 |
| `app/history.py` | `artifacts/app_runs.jsonl` 로컬 기록 |
| `app/service.py` | `process_ticket` 총괄 |
| `app/web_app.py` + `templates/` | FastAPI 웹 폼 |
| `smoke_run.py` | 실제 호출 스모크 테스트 |

## 실행·테스트 명령 (프로젝트 루트에서 실행)
- 웹: `uv run uvicorn app.web_app:app --reload`
- 스모크: `uv run python smoke_run.py` (실제 Claude·Langfuse 호출, 비용 발생)
- 단위 테스트: `uv run pytest -m "not integration"`
- 통합 테스트(`tests/test_claude_runner.py`)는 실제 호출이라 사용자가 요청할 때만 실행한다.

## 작업 시 주의사항
- 경로(`prompts/`, `templates/`, `artifacts/`)가 상대 경로라 항상 프로젝트 루트에서 실행한다.
- 프롬프트 템플릿은 `str.format()` 방식이므로 플레이스홀더는 `{name}` 단일 중괄호, 리터럴 중괄호는 `{{ }}`.
- Langfuse 구간은 `with` 중첩으로 trace 트리를 만든다. 평가 구간과 `record_scores`도 **root `with` 블록 안**에 둔다. (밖에 두면 별도 trace가 됨)
- `.env`(키 포함)와 `artifacts/`는 `.gitignore` 대상이다. 절대 커밋하지 않고, 내용을 출력할 때는 값을 마스킹한다.
- 평가 로직을 바꾸면 `tests/test_evaluator.py`를 함께 갱신한다.

## 주석 규칙 (한국어)
- **기본**: 파일 상단은 목적·핵심 기능을 2줄 이하로 요약하고, 절차는 `A → B → C`로 적는다. 클래스/함수는 docstring으로 2줄 이하.
- **상세 모드**: 사용자가 흐름 이해를 위해 "상세하게"를 요청하면 2줄 제한을 풀고, 파일 상단에 흐름도·용어 정의·"왜 이런 구조인가"를 적는다. (예: `service.py`, `langfuse_ops.py`)
- 주의사항은 짧게 명시한다. 상수/설정값에는 의미와 제약(예: 상대 경로)을 한 줄로 적는다.
- 주석 작업에서는 **로직을 바꾸지 않는다.** 의심 지점은 수정하지 말고 보고한다.

## 테스트 규칙
- 테스트 함수명은 **한글**로 작성한다. 예: `test_필수_키워드가_없어도_프롬프트가_렌더링된다`
- 각 테스트 첫머리에 "무엇을 넣고 무엇을 확인하는지"를 한 줄 주석으로 적는다.
- 테스트 파일 상단에 검증 대상 모듈과 목적을 한 줄로 적는다.

## 작업 방식 (사용자 선호)
- **언어**: 사용자에게 보이는 모든 답변은 한국어로 작성한다.
- **학습 목적**: 사용자는 책 예제를 따라 치며 배우는 중이다. 동작 원리와 "왜 이런 구조인가"를 이해할 수 있게 설명하고, 용어는 처음 나올 때 정의한다.
- **요청 범위만 수행**: 사용자가 코드를 직접 작성하고, Claude는 요청받은 평가·주석 보강·커밋/푸시를 맡는다. 요청하지 않은 코드 작성이나 범위 확장은 하지 않는다.
- **"참고만 해"라고 하면** 코드·plan·파일을 만들지 않고 내용만 기억한다.
- **설명 질문**에는 코드 변경 없이 대화로 답한다.
- **의심 지점**(버그 가능성 등)은 임의로 고치지 않고 보고한다. 사용자가 "고쳐줘"라고 하면 그때 수정한다.
- **커밋 전 점검**: `.env` 같은 시크릿이 스테이징되면 제외하고 알린다. `main`에서는 바로 커밋하지 않고 브랜치를 만든다.
- 브랜치는 `feat/chap11-llmops-lab`. 커밋 메시지는 한국어 `feat(chap11): ...` / `docs(chap11): ...` 형식.
