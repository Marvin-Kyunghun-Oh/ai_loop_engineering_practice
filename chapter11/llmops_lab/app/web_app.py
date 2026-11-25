# app/web_app.py
# 명령줄 대신 웹 폼으로 고객 문의를 받아 process_ticket을 실행하고 결과를 보여주는 FastAPI 앱.
# 흐름: GET / (입력 폼) → 제출 → POST /run (티켓 생성 → 파이프라인 실행) → 결과 화면
# 실행: 프로젝트 루트에서 `uv run uvicorn app.web_app:app --reload` 후 http://127.0.0.1:8000 접속
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv

from .prompting import SupportTicket
from .service import process_ticket

# 1. .env 로드
#    Langfuse 키·Claude 설정은 환경변수로 읽는다. 클라이언트와 CLI 설정은 첫 요청 때
#    만들어지므로, 서버 시작 시점에 한 번만 불러오면 충분하다.
load_dotenv()

# FastAPI 앱 객체. uvicorn이 `app.web_app:app`으로 이 객체를 찾아 서버를 띄운다.
app = FastAPI(title="고객 문의 답변 도우미")
# HTML 템플릿(templates/form.html, result.html) 위치. 상대 경로이므로 프로젝트 루트에서 실행해야 한다.
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """문의 입력 폼(form.html)을 보여준다."""
    return templates.TemplateResponse(request, "form.html")


# 2. 폼 입력을 받아 파이프라인 실행
#    Form(...)은 필수 입력, 기본값이 있는 항목(priority, required_keywords)은 생략 가능하다.
@app.post("/run", response_class=HTMLResponse)
async def run(
    request: Request,
    ticket_id: str = Form(...),
    customer_id: str = Form(...),
    subject: str = Form(...),
    message: str = Form(...),
    product: str = Form(...),
    priority: str = Form("normal"),
    required_keywords: str = Form(""),
):
    """폼 값으로 SupportTicket을 만들어 process_ticket을 실행하고, 결과 화면(result.html)을 반환한다.

    절차: 폼 값 수신 → 키워드 문자열을 리스트로 변환 → 티켓 생성 → 파이프라인 실행 → 화면 렌더링
    """
    ticket = SupportTicket(
        ticket_id=ticket_id,
        customer_id=customer_id,
        subject=subject,
        message=message,
        product=product,
        priority=priority,
        # "환불, 결제일" 같은 쉼표 구분 입력 → ["환불", "결제일"] (공백·빈 항목은 제거)
        required_keywords=[
            k.strip() for k in required_keywords.split(",") if k.strip()
        ],
    )
    # Claude 호출(수 초 소요)이 끝날 때까지 이 요청은 대기한다. (동기 호출이라 서버가 그동안 막힐 수 있음)
    result = process_ticket(ticket)
    return templates.TemplateResponse(
        request,
        "result.html",
        {
            "ticket": ticket,
            "result": result,
        },
    )
