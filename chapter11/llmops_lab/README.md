# llmops_lab — Langfuse로 LLM 답변 품질을 "눈에 보이게" 만들기

고객 문의 1건을 받아 Claude로 답변 초안을 만들고, 그 답변의 **품질·비용·지연을 Langfuse에 기록**해 두는 실습 프로젝트입니다.
(책 chapter11 예제를 따라 만들고, 흐름을 이해하기 위해 주석과 문서를 보강했습니다.)

---

## 1. 왜 만들었나

LLM 앱은 에러 없이 돌아가도 **답변이 좋은지는 코드만 봐서 알 수 없습니다.** 프롬프트를 고칠 때마다 "나아진 것 같다"는 감에 의존하게 되는 것이 문제입니다.

이 프로젝트는 그 감을 **측정 가능한 숫자**로 바꾸는 연습입니다.

| 풀고 싶은 문제 | 이 프로젝트의 해법 | Langfuse에서 확인하는 곳 |
|---|---|---|
| 한 번의 실행에서 무슨 일이 있었는지 모른다 | 실행 1건을 **trace**로 기록하고 구간(span)으로 나눈다 | trace 상세 화면의 트리 |
| 답변이 좋은지 판단할 기준이 없다 | 키워드·형식·길이를 **score**(점수)로 남긴다 | trace의 Scores |
| 프롬프트를 바꾸면 좋아졌는지 비교할 수 없다 | 같은 기준의 점수가 쌓여 **전/후 비교**가 가능하다 | trace 목록, 점수 필터 |
| 품질 개선이 비용·속도를 희생했는지 모른다 | 토큰·비용·지연을 **같이 기록**한다 | generation의 Usage/Cost, `latency_ms` 점수 |
| 특정 고객·우선순위만 따로 보고 싶다 | `user_id`, `tags`를 trace에 붙인다 | 사용자/태그 필터 |

한 줄 요약: **"프롬프트를 감으로 고치지 말고, 측정 → 비교 → 개선의 순환을 돌린다. 이 프로젝트는 그중 '측정 장치'를 만든다."**

> 아직 하지 않은 것: 프롬프트를 실제로 바꿔 전/후를 비교하는 실험은 포함되어 있지 않습니다. 측정 장치를 갖춘 뒤의 다음 단계입니다. (아래 "7. 직접 해 보기" 참고)

---

## 2. 이 프로젝트에서 체감할 수 있는 Langfuse 기능

| Langfuse 개념 | 한 줄 설명 | 코드 위치 |
|---|---|---|
| **trace** | 실행 1건 전체. 목록의 한 줄 | `support_ticket_trace` (`app/langfuse_ops.py`) |
| **span** | trace 안의 구간. 시작~끝 시간이 자동 기록 | 같은 함수의 root span |
| **generation** | LLM 호출 전용 구간. 모델·토큰·비용을 함께 기록 | `claude_generation` |
| **evaluator** | 평가 단계를 구분해서 보여주는 구간 | `quality_evaluator` |
| **score** | trace에 붙는 숫자 점수. 비교·필터의 근거 | `record_scores` |
| **user_id / tags** | trace를 고객별·태그별로 걸러 보는 꼬리표 | `propagate_attributes` |
| **flush** | 모아 둔 기록을 서버로 강제 전송 | `support_ticket_trace`의 `finally` |

한 건을 처리하면 Langfuse에는 다음 트리가 만들어집니다.

```
support-ticket-run          (trace의 root span: 티켓 입력, product/priority 메타데이터)
├─ claude-p-answer          (generation: 프롬프트, 답변, 모델, 토큰, 비용)
└─ quality-check            (evaluator: 키워드 커버리지·형식·길이 결과)
   + score 4개: keyword_coverage, format_ok, response_length_ok, latency_ms
```

---

## 3. 전체 사이클 (티켓 1건이 처리되는 순서)

`app/service.py`의 `process_ticket`이 아래 순서로 부품들을 이어 붙입니다.

```
[웹 폼 / smoke_run.py]
        │  SupportTicket 생성
        ▼
 1. render_prompt        티켓 → 프롬프트 문장              app/prompting.py  + prompts/support_answer.md
        ▼
 2. trace 열기           "티켓 1건 처리 시작"               app/langfuse_ops.py  support_ticket_trace
        ▼
 3.   generation 열기    "Claude 호출 구간" 시작            claude_generation
        ▼
 4.     run_claude       claude CLI 실제 호출               app/claude_runner.py
        ▼
 5.     gen.update       답변·토큰·비용을 generation에 기록  (service.py)
        ▼
 6.   evaluator 열기     "품질 평가 구간" 시작              quality_evaluator
        ▼
 7.     evaluate         키워드·형식·길이 판정              app/evaluator.py
        ▼
 8.   record_scores      판정을 Langfuse 점수로 기록        record_scores
        ▼
 9. trace 닫기 + flush   기록 전송                          support_ticket_trace의 finally
        ▼
10. append_run           로컬 JSONL에도 한 줄 기록          app/history.py → artifacts/app_runs.jsonl
        ▼
11. RunResult 반환       웹 결과 화면 / 터미널 출력
```

핵심은 `with` 블록의 **중첩**입니다. 블록의 시작과 끝이 곧 구간의 시작과 끝이고, 안에 중첩된 블록이 자식 구간이 됩니다. 그래서 위의 트리가 자동으로 만들어집니다.

---

## 4. 파일·클래스 지도

| 파일 | 핵심 클래스/함수 | 역할 | 연관 |
|---|---|---|---|
| `app/prompting.py` | `SupportTicket`, `render_prompt` | 입력 데이터 모델 + 템플릿 치환 | 모든 단계의 입력. `prompts/support_answer.md`를 읽음 |
| `prompts/support_answer.md` | (템플릿) | 프롬프트 본문. `{name}` 단일 중괄호 | `render_prompt`가 `str.format()`으로 채움 |
| `app/claude_runner.py` | `ClaudeResult`, `run_claude` | `claude -p` CLI 호출, 답변·비용·시간 표준화 | 결과가 `evaluator`, `langfuse_ops`, `history`로 전달됨 |
| `app/evaluator.py` | `EvalResult`, `evaluate` | 규칙 기반 품질 평가 (외부 호출 없음) | 결과가 score와 화면의 근거가 됨 |
| `app/langfuse_ops.py` | `get_client`, `support_ticket_trace`, `claude_generation`, `quality_evaluator`, `record_scores` | Langfuse 전송 전담 | `service.py`에서만 호출 |
| `app/history.py` | `append_run` | Langfuse와 별개의 로컬 JSONL 기록 | Langfuse가 안 돼도 결과 확인 가능 |
| `app/service.py` | `RunResult`, `process_ticket` | 위 부품들을 순서대로 엮는 총괄 | 웹과 스모크가 공통으로 호출 |
| `app/web_app.py` | `index`, `run` (FastAPI) | 웹 폼 입력 → `process_ticket` → 결과 화면 | `templates/form.html`, `result.html` |
| `smoke_run.py` | (스크립트) | 터미널에서 티켓 1건 실제 실행 | `process_ticket` |

데이터가 흐르는 방향: `SupportTicket` → (프롬프트 문자열) → `ClaudeResult` → `EvalResult` → `RunResult`.

---

## 5. 사용자 가이드

### 준비
- Python 3.15, [uv](https://docs.astral.sh/uv/), Claude Code CLI(`claude`), Langfuse 계정/프로젝트
- 의존성 설치: `uv sync`
- 프로젝트 루트에 `.env` 파일을 만듭니다. (`.gitignore`에 포함되어 커밋되지 않습니다)

```dotenv
LANGFUSE_PUBLIC_KEY=...
LANGFUSE_SECRET_KEY=...
LANGFUSE_BASE_URL=...          # 예: https://cloud.langfuse.com

CLAUDE_BIN=claude              # claude CLI 경로 (기본값 claude)
CLAUDE_MODEL=sonnet            # 사용할 모델 (기본값 sonnet)
CLAUDE_TIMEOUT_SECONDS=120     # 호출 제한 시간 (기본값 120)
```

> 모든 명령은 **프로젝트 루트(`llmops_lab/`)** 에서 실행하세요. 템플릿·기록 파일 경로가 상대 경로입니다.

### 방법 A. 웹 화면으로 실행
```bash
uv run uvicorn app.web_app:app --reload
```
1. 브라우저에서 `http://127.0.0.1:8000` 접속
2. 문의 정보를 입력 (필수 키워드는 쉼표로 구분: `환불, 결제일, 영업일`)
3. 제출 → 약 10초 후 답변과 점수(커버리지·형식·길이·지연·비용)가 화면에 표시됩니다.

### 방법 B. 스모크 테스트 (터미널, 티켓 1건)
```bash
uv run python smoke_run.py
```
터미널에 답변 일부·커버리지·지연·비용이 출력됩니다.

### 실행 후 확인할 곳
1. **Langfuse 화면**: `ticket_id`로 방금 trace를 찾아 트리(generation·evaluator)와 점수 4개를 확인합니다.
2. **로컬 기록**: `artifacts/app_runs.jsonl`에 한 줄이 추가됩니다. (git 제외)

### 테스트
```bash
uv run pytest -m "not integration"   # 단위 테스트 (외부 호출 없음, 무료)
uv run pytest tests/test_claude_runner.py   # 통합 테스트 (실제 claude 호출, 비용 발생)
```

---

## 6. 평가 기준 (현재)

| 점수 | 기준 | 한계 |
|---|---|---|
| `keyword_coverage` | 필수 키워드 중 답변에 포함된 비율 (0~1) | 단순 포함 여부만 봄 |
| `format_ok` | `요약`·`답변`·`다음 단계` 문자열이 모두 있는지 | 제목(`##`) 여부와 순서는 검사하지 않음 |
| `response_length_ok` | 50자 이상 4000자 이하 | 기준값이 코드에 고정되어 있음 |
| `latency_ms` | Claude 응답 시간(밀리초) | 점수 기록만 하고 판정은 안 함 |

의도적으로 **규칙 기반**으로 만들었습니다. 외부 호출이 없어 빠르고, 단위 테스트가 가능하며, 결과가 매번 같기 때문입니다.

---

## 7. 직접 해 보기: 점수 비교 실험

이 프로젝트의 가치는 "비교"에서 나옵니다. 아래처럼 해 보세요.

1. 웹 화면(또는 `smoke_run.py`)으로 티켓을 한 번 실행합니다.
2. `prompts/support_answer.md`에서 `## 다음 단계` 섹션을 지우고 같은 티켓으로 다시 실행합니다.
3. Langfuse에서 두 trace의 `format_ok`, `latency_ms`, 비용을 나란히 비교합니다.
4. 실험 후 프롬프트 파일을 원래대로 되돌립니다.

---

## 8. 알아둘 점
- 웹 요청은 Claude 호출이 끝날 때까지(약 10초) 대기합니다. 혼자 쓰는 용도 기준입니다.
- 통합 테스트(`@pytest.mark.integration`)는 아직 pytest 마커로 등록하지 않아 경고가 납니다.
- `src/llmops_lab/`는 `uv init`이 만든 기본 골격이며, 실제 코드는 `app/`에 있습니다.
