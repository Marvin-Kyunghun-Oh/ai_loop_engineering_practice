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
| 어느 답변이 어느 프롬프트로 만들어졌는지 모른다 | 프롬프트를 **Langfuse에서 버전으로 관리**하고, 호출마다 사용한 버전을 연결한다 | Prompts 메뉴, generation의 Prompt 링크 |
| 품질 개선이 비용·속도를 희생했는지 모른다 | 토큰·비용·지연을 **같이 기록**한다 | generation의 Usage/Cost, `latency_ms` 점수 |
| 특정 고객·우선순위만 따로 보고 싶다 | `user_id`, `tags`를 trace에 붙인다 | 사용자/태그 필터 |

한 줄 요약: **"프롬프트를 감으로 고치지 말고, 측정 → 비교 → 개선의 순환을 돌린다. 이 프로젝트는 그중 '측정 장치'를 만든다."**

> 아직 하지 않은 것: 프롬프트를 실제로 바꿔 전/후를 비교하는 실험 결과는 포함되어 있지 않습니다. 측정 장치와 프롬프트 버전 관리를 갖춘 뒤의 다음 단계입니다. (아래 "7. 직접 해 보기" 참고)

---

## 2. 이 프로젝트에서 체감할 수 있는 Langfuse 기능

| Langfuse 개념 | 한 줄 설명 | 코드 위치 |
|---|---|---|
| **trace** | 실행 1건 전체. 목록의 한 줄 | `support_ticket_trace` (`app/langfuse_ops.py`) |
| **span** | trace 안의 구간. 시작~끝 시간이 자동 기록 | 같은 함수의 root span |
| **generation** | LLM 호출 전용 구간. 모델·토큰·비용을 함께 기록 | `claude_generation` |
| **prompt / label** | Langfuse에 버전으로 보관되는 프롬프트. `production` label이 붙은 버전이 현재 운영 버전 | `client.get_prompt` (`app/service.py`), 등록은 `app/seed_prompts.py` |
| **evaluator** | 평가 단계를 구분해서 보여주는 구간 | `quality_evaluator` |
| **score** | trace에 붙는 숫자 점수. 비교·필터의 근거 | `record_scores` |
| **user_id / tags** | trace를 고객별·태그별로 걸러 보는 꼬리표 | `propagate_attributes` |
| **flush** | 모아 둔 기록을 서버로 강제 전송 | `support_ticket_trace`의 `finally` |

한 건을 처리하면 Langfuse에는 다음 트리가 만들어집니다.

```
support-ticket-run          (trace의 root span: 티켓 입력, product/priority 메타데이터)
├─ claude-p-answer          (generation: 프롬프트, 답변, 모델, 토큰, 비용 + 사용한 프롬프트 버전 링크)
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
 1. get_prompt           Langfuse에서 프롬프트 조회          app/service.py → client.get_prompt("support-answer-v1", label="production")
        ▼
 2. compile_prompt       프롬프트의 {{변수}}에 티켓 값 채우기  app/prompting.py
        ▼
 3. trace 열기           "티켓 1건 처리 시작"               app/langfuse_ops.py  support_ticket_trace
        ▼
 4.   generation 열기    "Claude 호출 구간" 시작 + 프롬프트 버전 연결   claude_generation(prompt=...)
        ▼
 5.     run_claude       claude CLI 실제 호출               app/claude_runner.py
        ▼
 6.     gen.update       답변·토큰·비용을 generation에 기록  (service.py)
        ▼
 7.   evaluator 열기     "품질 평가 구간" 시작              quality_evaluator
        ▼
 8.     evaluate         키워드·형식·길이 판정              app/evaluator.py
        ▼
 9.   record_scores      판정을 Langfuse 점수로 기록        record_scores
        ▼
10. trace 닫기 + flush   기록 전송                          support_ticket_trace의 finally
        ▼
11. append_run           로컬 JSONL에도 한 줄 기록          app/history.py → artifacts/app_runs.jsonl
        ▼
12. RunResult 반환       웹 결과 화면 / 터미널 출력
```

> 프롬프트 본문은 코드나 파일이 아니라 **Langfuse에 있습니다.** 프롬프트를 새 버전으로 올리고 `production` label만 옮기면, 코드 수정 없이 다음 실행부터 새 버전이 쓰입니다. (SDK가 프롬프트를 잠시 캐시하므로 반영까지 최대 약 1분 걸릴 수 있습니다.)

핵심은 `with` 블록의 **중첩**입니다. 블록의 시작과 끝이 곧 구간의 시작과 끝이고, 안에 중첩된 블록이 자식 구간이 됩니다. 그래서 위의 트리가 자동으로 만들어집니다.

---

## 4. 파일·클래스 지도

| 파일 | 핵심 클래스/함수 | 역할 | 연관 |
|---|---|---|---|
| `app/prompting.py` | `SupportTicket`, `compile_prompt` | 입력 데이터 모델 + Langfuse 프롬프트 변수 치환 | 모든 단계의 입력. 프롬프트 본문은 Langfuse에서 받아 옴 |
| `prompts/support_answer.md` | (등록 원본) | 프롬프트 본문. `{{name}}` 이중 중괄호 | `app/seed_prompts.py`가 Langfuse에 등록. **실행 시에는 이 파일을 읽지 않고 Langfuse 것을 사용** |
| `app/claude_runner.py` | `ClaudeResult`, `run_claude` | `claude -p` CLI 호출, 답변·비용·시간 표준화 | 결과가 `evaluator`, `langfuse_ops`, `history`로 전달됨 |
| `app/evaluator.py` | `EvalResult`, `evaluate` | 규칙 기반 품질 평가 (외부 호출 없음) | 결과가 score와 화면의 근거가 됨 |
| `app/langfuse_ops.py` | `get_client`, `support_ticket_trace`, `claude_generation`, `quality_evaluator`, `record_scores` | Langfuse 클라이언트 생성 + trace/generation/평가/점수 전송 | `service.py`에서 호출. `get_client`는 `seed_prompts.py`도 사용 |
| `app/seed_prompts.py` | `main` | `prompts/support_answer.md`를 Langfuse에 새 버전으로 등록 (label `production`) | 한 번 실행하는 명령. `python -m app.seed_prompts` |
| `app/history.py` | `append_run` | Langfuse와 별개의 로컬 JSONL 기록 | Langfuse가 안 돼도 결과 확인 가능 |
| `app/service.py` | `RunResult`, `process_ticket` | 위 부품들을 순서대로 엮는 총괄 | 웹과 스모크가 공통으로 호출 |
| `app/web_app.py` | `index`, `run` (FastAPI) | 웹 폼 입력 → `process_ticket` → 결과 화면 | `templates/form.html`, `result.html` |
| `smoke_run.py` | (스크립트) | 터미널에서 티켓 1건 실제 실행 | `process_ticket` |

데이터가 흐르는 방향: `SupportTicket` + (Langfuse 프롬프트 객체) → 프롬프트 문자열 → `ClaudeResult` → `EvalResult` → `RunResult`.

---

## 5. 사용자 가이드

> 모든 명령은 **프로젝트 루트(`llmops_lab/`)** 에서 실행하세요. `prompts/`, `templates/`, `artifacts/` 경로가 상대 경로입니다. (Langfuse 설치 단계만 별도 폴더에서 합니다.)

### 준비물
- Python 3.15, [uv](https://docs.astral.sh/uv/), Claude Code CLI(`claude`)
- Docker (Langfuse를 내 컴퓨터에 설치하는 경우)

### 단계 1. Langfuse 준비

Langfuse는 두 가지 중 하나로 준비합니다.

- **클라우드**: [cloud.langfuse.com](https://cloud.langfuse.com)에서 가입합니다. 설치가 필요 없습니다. → 아래 "프로젝트와 API 키 만들기"로 이동
- **내 컴퓨터에 설치(셀프호스팅)**: 아래 순서를 따릅니다.

```bash
# 프로젝트 폴더 밖의 원하는 위치에서 실행하세요.
git clone https://github.com/langfuse/langfuse.git
cd langfuse
docker compose up -d
```

1. 컨테이너가 모두 뜰 때까지 1~2분 기다립니다. (`docker compose ps`로 상태 확인, `docker compose logs -f langfuse-web`에서 준비 완료 메시지 확인)
2. 브라우저에서 `http://localhost:3000`에 접속합니다.
3. **Sign up**으로 계정을 만듭니다. (내 컴퓨터에만 저장되는 계정입니다.)
4. 종료할 때는 `docker compose down`, 데이터까지 지우려면 `docker compose down -v`입니다.

> 이 방법은 **로컬 실습용**입니다. 외부에 공개하는 서버로 쓰려면 `docker-compose.yml`의 `# CHANGEME` 표시된 비밀번호·키를 반드시 바꾸세요.

**프로젝트와 API 키 만들기**
1. Langfuse 화면에서 Organization → Project를 만듭니다. (이름은 자유, 예: `llmops-lab`)
2. 프로젝트 **Settings → API Keys → Create new API key**를 누릅니다.
3. 화면에 나온 Public Key와 Secret Key를 복사합니다. (**Secret Key는 이때만 보입니다**)

### 단계 2. 프로젝트 설치와 `.env` 설정

```bash
uv sync
```

프로젝트 루트에 `.env` 파일을 만듭니다. (`.gitignore`에 포함되어 커밋되지 않습니다)

```dotenv
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_BASE_URL=http://localhost:3000   # 클라우드는 https://cloud.langfuse.com

CLAUDE_BIN=claude              # claude CLI 경로 (기본값 claude)
CLAUDE_MODEL=sonnet            # 사용할 모델 (기본값 sonnet)
CLAUDE_TIMEOUT_SECONDS=120     # 호출 제한 시간 (기본값 120)
```

### 단계 3. 프롬프트를 Langfuse에 업로드

이 프로젝트는 실행할 때 프롬프트를 파일이 아니라 **Langfuse에서 읽어 옵니다.** 그래서 처음 한 번은 프롬프트를 올려 두어야 합니다. 안 올리면 `support-answer-v1`을 찾을 수 없다는 오류가 납니다.

**방법 1. 명령으로 올리기 (권장)**
```bash
uv run python -m app.seed_prompts
```
- `prompts/support_answer.md`를 이름 `support-answer-v1`, label `production`으로 등록하고 `등록 완료` 메시지를 출력합니다.
- 같은 이름으로 다시 실행하면 **새 버전**(v2, v3 …)이 만들어지고 `production` label이 새 버전으로 옮겨집니다. 이전 버전은 지워지지 않습니다.

**방법 2. Langfuse 화면에서 직접 만들기**
1. 왼쪽 메뉴 **Prompts → New prompt**
2. Name `support-answer-v1`, Type `Text`, 본문 입력
3. **Set the "production" label**을 켜고 저장

**확인**: Prompts 메뉴에 `support-answer-v1`이 보이고, 버전 옆에 `production` label이 붙어 있어야 합니다.

**주의할 점**
- 변수는 `{{ticket_id}}`처럼 **이중 중괄호**로 씁니다. `{ticket_id}`(단일)는 치환되지 않아 Claude가 변수 이름 그대로 받습니다. (답변이 "티켓 정보가 비어 있다"고 나오고 키워드 커버리지가 0이 되는 증상)
- 사용하는 변수는 `ticket_id`, `customer_id`, `product`, `priority`, `subject`, `message`, `required_keywords` 7개입니다.
- `prompts/support_answer.md`를 고쳐도 **다시 올리기 전까지는 반영되지 않습니다.** 실행 때 읽는 것은 Langfuse에 있는 버전입니다.
- 코드(`app/service.py`)의 프롬프트 이름과 등록한 이름이 정확히 같아야 합니다.

### 단계 4. 실행

#### 방법 A. 웹 화면으로 실행
```bash
uv run uvicorn app.web_app:app --reload
```
1. 브라우저에서 `http://127.0.0.1:8000` 접속
2. 문의 정보를 입력 (필수 키워드는 쉼표로 구분: `환불, 결제일, 영업일`)
3. 제출 → 약 10초 후 답변과 점수(커버리지·형식·길이·지연·비용)가 화면에 표시됩니다.

#### 방법 B. 스모크 테스트 (터미널, 티켓 1건)
```bash
uv run python smoke_run.py
```
터미널에 답변 일부·커버리지·지연·비용이 출력됩니다.

### 실행 후 확인할 곳
1. **Langfuse 화면**: `ticket_id`로 방금 trace를 찾아 트리(generation·evaluator)와 점수 4개를 확인합니다. generation에는 사용한 **프롬프트 이름·버전 링크**가 붙어 있습니다.
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
2. Langfuse 화면에서 `support-answer-v1` 프롬프트의 `## 다음 단계` 섹션을 지운 새 버전을 만들어 `production` label을 옮기고, 같은 티켓으로 다시 실행합니다. (`prompts/support_answer.md`를 고치고 `seed_prompts`를 다시 실행해도 됩니다. 반영까지 최대 약 1분 걸릴 수 있습니다.)
3. Langfuse에서 두 trace의 `format_ok`, `latency_ms`, 비용을 나란히 비교합니다. Prompts 메뉴의 버전별 화면에서는 버전마다 호출 수·비용·지연·점수가 모아져 보입니다.
4. 실험 후 `production` label을 원래 버전으로 되돌립니다.

---

## 8. 알아둘 점
- 웹 요청은 Claude 호출이 끝날 때까지(약 10초) 대기합니다. 혼자 쓰는 용도 기준입니다.
- 통합 테스트(`@pytest.mark.integration`)는 아직 pytest 마커로 등록하지 않아 경고가 납니다.
- 단위 테스트(`tests/test_prompting.py`)는 Langfuse에 접속하지 않고 `{{변수}}`를 치환하는 가짜 프롬프트 객체로 `compile_prompt`를 검증합니다.
- Langfuse에 접속할 수 없으면 프롬프트 조회 단계에서 실패합니다. (조회 실패 시 쓸 기본 프롬프트(fallback)는 아직 두지 않았습니다.)
- 프롬프트 이름 `support-answer-v1`에 버전 표기가 들어 있지만, 실제 버전은 Langfuse가 v1, v2 …로 따로 관리합니다.
- `src/llmops_lab/`는 `uv init`이 만든 기본 골격이며, 실제 코드는 `app/`에 있습니다.
