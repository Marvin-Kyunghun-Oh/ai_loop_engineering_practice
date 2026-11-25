# smoke_run.py
# 스모크 테스트: 티켓 1건을 "실제로" 처리해 전체 흐름이 끝까지 도는지 확인하는 실행 스크립트.
# 실행: 프로젝트 루트에서 `uv run python smoke_run.py`
# 주의: 실제 Claude 호출(비용 발생)과 Langfuse 전송이 일어난다.
#
# 기대 결과: 터미널에 답변·커버리지·지연·비용이 출력되고,
#            Langfuse에 trace 1건, artifacts/app_runs.jsonl에 한 줄이 추가된다.

# .env(키·주소 등)를 환경변수로 읽어 들인다.
# app 모듈들이 import 되기 전에 먼저 호출해야, 이후 코드가 환경변수를 제대로 읽을 수 있다.
from dotenv import load_dotenv
load_dotenv()

from app.prompting import SupportTicket
from app.service import process_ticket

# 테스트용 가짜 티켓. required_keywords는 "답변에 꼭 들어가야 하는 단어"로, 평가의 기준이 된다.
ticket = SupportTicket(
    ticket_id="smoke_001",
    customer_id="c_smoke",
    subject="환불 문의",
    message="지난주에 결제한 연간 구독을 환불하고 싶습니다.",
    product="LangOps Pro",
    priority="high",
    required_keywords=["환불", "결제일", "영업일"],
)

# 티켓 처리의 전 과정(프롬프트 → Claude → 평가 → 기록)이 이 한 줄에서 실행된다.
result = process_ticket(ticket)

# 결과 확인용 출력
print("답변:", result.answer[:200])
print(f"키워드 커버리지: {result.eval_result.keyword_coverage:.2f}")
print(f"형식 통과: {result.eval_result.format_ok}")
print(f"지연: {result.claude_result.duration_ms:.0f}ms")
print(f"비용: ${result.claude_result.cost_usd:.4f}")
