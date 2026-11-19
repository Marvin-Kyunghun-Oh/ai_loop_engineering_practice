# =============================================================================
# 명언 MCP 서버 (main.py)
#
# MCP의 세 가지 기능을 모두 사용해 보는 예제입니다.
#   - 도구(Tool)     : get_random_quote(읽기), add_quote(쓰기
#   - 리소스(Resource): quote://all
#   - 프롬프트(Prompt): quote_post
#
# 실행 전 준비:
#   uv add mcp                 # MCP 파이썬 SDK 설치
#   (DB 파일 quotes.db 는 최초 실행 때 자동 생성되며, quotes.json 은 시드 데이터로 쓰입니다)
# =============================================================================

# --- import: 자바의 import와 같은 역할 ---------------------------------------
import argparse                          # 명령줄 옵션 파싱 (표준 라이브러리)
import json                              # JSON 읽기/쓰기 (표준 라이브러리)
import os                                # 환경변수 읽기 (표준 라이브러리)
import sqlite3                           # SQLite DB (표준 라이브러리, 자바의 JDBC 비슷)
from contextlib import closing           # 연결을 확실히 닫아 주는 도우미 (자바의 try-with-resources 비슷)
import unicodedata                        # 문자 종류(제어 문자 등) 판별 (표준 라이브러리)
import sys                               # stderr 출력, 종료 코드 (표준 라이브러리)
import random                            # 무작위 선택 (표준 라이브러리)
from pathlib import Path                 # 파일 경로 다루기 (자바의 java.nio.file.Path와 비슷)
from mcp.server.mcpserver import MCPServer   # MCP 서버를 쉽게 만들어 주는 클래스 (mcp 2.x에서 FastMCP → MCPServer로 개명)

# 1. 서버 객체 생성
# MCPServer("quote")로 서버 객체를 만듭니다. "quote"는 서버 이름입니다.
# 아래에서 이 객체(mcp)의 데코레이터(@mcp.tool() 등)를 함수에 붙이면,
# 해당 함수가 MCP 규격에 맞는 기능으로 외부(클로드 코드)에 노출됩니다.
mcp = MCPServer("quote")

# 데이터 저장소 경로
# __file__ 은 "지금 실행 중인 이 파일(main.py)의 경로"입니다.
# QUOTES_DB 환경변수가 있으면 그 경로를, 없으면 main.py 옆의 quotes.db 를 씁니다.
# (대문자 변수명은 파이썬에서 "상수"라는 관례적 표시입니다. 자바의 static final과 비슷)
DB_FILE = Path(os.environ.get("QUOTES_DB") or Path(__file__).parent / "quotes.db")

# quotes.json 은 이제 "시드(초기 데이터)"입니다. DB가 비어 있을 때 한 번만 가져오고, 파일은 지우지 않습니다.
QUOTES_FILE = Path(__file__).parent / "quotes.json"


def _load_seed() -> list:
    # 시드(quotes.json)를 읽어 검증합니다. add_quote와 같은 규칙(길이·개행·제어 문자)을 적용해,
    # 시드를 통해 검증되지 않은 값이 DB와 quote://all 로 흘러가지 않게 합니다.
    # 문제가 있으면 ValueError(JSON 문법 오류·UTF-8 오류도 ValueError의 하위 클래스)로 알립니다.
    data = json.loads(QUOTES_FILE.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("quotes.json은 명언 객체의 배열이어야 합니다.")
    rows = []
    for i, q in enumerate(data, start=1):
        if not isinstance(q, dict) or not isinstance(q.get("text"), str) or not isinstance(q.get("author"), str):
            raise ValueError(f"quotes.json {i}번째 항목은 문자열 text, author를 가진 객체여야 합니다.")
        rows.append((
            validate_quote_field(f"quotes.json {i}번째 본문", q["text"], MAX_TEXT_LEN),
            validate_quote_field(f"quotes.json {i}번째 작성자", q["author"], MAX_AUTHOR_LEN),
        ))
    return rows


def _connect() -> sqlite3.Connection:
    # 내부 헬퍼: DB 연결을 열고, 테이블이 없으면 만들고, 비어 있으면 시드를 가져옵니다.
    # 호출한 쪽이 closing(...) 과 with 로 커밋·종료를 책임집니다.
    # (DB_FILE 을 호출 시점에 읽으므로 테스트에서 monkeypatch 로 바꿀 수 있습니다.)
    #
    # 초기화는 BEGIN IMMEDIATE 로 "쓰기 락을 먼저 잡고" 비어 있는지 확인합니다.
    # 그래야 MCP 서버와 --search 가 빈 DB에 동시에 붙어도 시드가 두 번 들어가지 않습니다
    # (자바의 synchronized 블록 안에서 check-then-act 를 하는 것과 같은 원리).
    # isolation_level=None 은 파이썬이 트랜잭션을 자동으로 열지 않게 해서 BEGIN/COMMIT 을 직접 다루기 위함입니다.
    conn = sqlite3.connect(DB_FILE, timeout=10, isolation_level=None)
    try:
        conn.execute("BEGIN IMMEDIATE")
        try:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS quotes ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "text TEXT NOT NULL, author TEXT NOT NULL)"
            )
            empty = conn.execute("SELECT COUNT(*) FROM quotes").fetchone()[0] == 0
            if empty and QUOTES_FILE.exists():
                # 마이그레이션: quotes.json -> DB. 값은 항상 ? 바인딩으로 넘깁니다(SQL 인젝션 방지).
                # 주의: DB를 수동으로 전부 비우면 다음 연결 때 시드가 다시 들어옵니다.
                conn.executemany("INSERT INTO quotes (text, author) VALUES (?, ?)", _load_seed())
            conn.execute("COMMIT")
        except BaseException:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        # 이후 호출부의 `with conn:` 이 평소처럼 커밋하도록 기본 모드로 되돌립니다.
        conn.isolation_level = ""
    except BaseException:
        conn.close()
        raise
    return conn


def load_quotes() -> list:
    # 헬퍼 함수: DB의 모든 명언을 id 순서대로 [{"text": ..., "author": ...}, ...] 로 돌려줍니다.
    # 데코레이터가 없으므로 MCP에 노출되지 않는 내부용 함수입니다.
    with closing(_connect()) as conn, conn:
        rows = conn.execute("SELECT text, author FROM quotes ORDER BY id").fetchall()
    return [{"text": t, "author": a} for t, a in rows]


def search_quotes(keyword: str) -> list:
    # 헬퍼 함수: 명언 "본문(text)"에 keyword가 포함된 항목만 돌려줍니다.
    # 작성자(author)는 검색 대상이 아닙니다. 영문 대소문자는 구분하지 않습니다.
    # SQLite의 LIKE는 ASCII만 대소문자를 무시하므로, 기존 의미(casefold)를 지키려고 파이썬에서 거릅니다.
    keyword = keyword.strip().casefold()
    return [q for q in load_quotes() if keyword in q["text"].casefold()]


# 2. 무작위 명언 반환 도구 (읽기형)
# @mcp.tool() 을 붙인 함수는 "도구"가 됩니다.
#   - 함수 이름(get_random_quote)  → 도구 이름
#   - 독스트링(""" """ 안의 설명)  → 도구 설명
#   - 타입 힌트(매개변수/반환 타입) → 입력 스키마
# 모델(Claude)은 이 설명과 스키마를 보고 언제, 어떻게 도구를 호출할지 판단합니다.
@mcp.tool()
def get_random_quote() -> str:
    """무작위 명언 한 개를 반환합니다."""
    quotes = load_quotes()
    if not quotes:
        raise ValueError("등록된 명언이 없습니다.")   # 빈 목록이면 random.choice 가 IndexError 를 내므로 미리 막음
    quote = random.choice(quotes)          # DB에서 읽은 리스트에서 하나를 무작위로 고름
    # f'...' 는 f-string(문자열 포맷팅)입니다. { } 안의 값이 그대로 들어갑니다.
    # 자바로 치면 quote.get("text") + " - " + quote.get("author") 와 같습니다.
    return f'{quote["text"]} - {quote["author"]}'


# 입력 길이 제한: 저장된 명언은 quote://all 등으로 모델 컨텍스트에 그대로 돌아오므로 상한을 둡니다.
MAX_TEXT_LEN = 300
MAX_AUTHOR_LEN = 50


def validate_quote_field(name: str, value: str, max_len: int) -> str:
    # 앞뒤 공백을 제거하고, 비어 있거나 길거나 개행이 있으면 ValueError를 냅니다.
    # MCP가 ValueError를 오류 응답으로 돌려주므로, 모델이 메시지를 보고 입력을 고쳐 재시도할 수 있습니다.
    value = value.strip()
    if not value:
        raise ValueError(f"{name}은(는) 비어 있을 수 없습니다.")
    if len(value) > max_len:
        raise ValueError(f"{name}은(는) 1~{max_len}자여야 합니다 (현재 {len(value)}자).")
    if "\n" in value or "\r" in value:
        raise ValueError(f"{name}에는 줄바꿈을 넣을 수 없습니다.")
    # 탭·NUL 같은 제어 문자(Cc)와 유니코드 줄/문단 구분자(Zl, Zp)도 거부합니다.
    if any(unicodedata.category(ch) in ("Cc", "Zl", "Zp") for ch in value):
        raise ValueError(f"{name}에는 제어 문자를 넣을 수 없습니다.")
    return value


# 3. 명언 추가 도구 (쓰기형)
# '2'와 같은 방식의 도구지만, DB에 새 명언을 추가하는 "쓰기" 동작을 합니다.
# 매개변수 text, author 의 타입 힌트(str)가 입력 스키마가 되므로,
# Claude는 이 도구를 호출할 때 text와 author 두 문자열을 넘겨줍니다.
@mcp.tool()
def add_quote(text: str, author: str) -> str:
    """새 명언을 명언 목록에 추가합니다. 본문은 1~300자, 작성자는 1~50자이며 줄바꿈·제어 문자는 허용되지 않습니다."""
    text = validate_quote_field("명언 본문", text, MAX_TEXT_LEN)
    author = validate_quote_field("작성자", author, MAX_AUTHOR_LEN)
    # 연결은 함수마다 열고, with 로 커밋한 뒤 closing 으로 닫습니다.
    # 값은 반드시 ? 바인딩으로 넘깁니다 (자바의 PreparedStatement 와 같습니다).
    with closing(_connect()) as conn, conn:
        conn.execute("INSERT INTO quotes (text, author) VALUES (?, ?)", (text, author))
        count = conn.execute("SELECT COUNT(*) FROM quotes").fetchone()[0]
    return f"명언을 추가했습니다. 현재 {count}개입니다."


# 4. 리소스
# @mcp.resource("quote://all") 은 "quote://all" 이라는 URI로 접근할 수 있는
# 리소스를 만듭니다. 도구가 "실행하는 기능"이라면, 리소스는 "읽어 가는 데이터"입니다.
# 클로드 코드에서는 @ 멘션으로 이 리소스를 대화에 불러올 수 있습니다.
@mcp.resource("quote://all")
def all_quotes() -> str:
    """전체 명언 목록을 반환합니다."""
    # DB 내용을 기존과 같은 JSON 문자열로 돌려줍니다 (ensure_ascii=False : 한글 그대로).
    return json.dumps(load_quotes(), ensure_ascii=False, indent=2)


# 5. 프롬프트
# @mcp.prompt() 는 클로드 코드에서 슬래시 커맨드로 나타나는 "프롬프트 양식"입니다.
# 사용자가 슬래시 커맨드로 실행하면서 topic(주제)을 넣으면,
# 아래에서 만든 문장이 프롬프트로 Claude에게 전달됩니다.
@mcp.prompt()
def quote_post(topic: str) -> str:
    """명언을 인용한 짧은 글을 작성합니다."""
    # 괄호 안에 문자열 두 개를 나란히 쓰면 파이썬이 자동으로 하나로 이어 붙입니다.
    # (긴 문자열을 여러 줄로 나눠 쓰는 관용적인 방법)
    return (
        f"등록된 명언 중 '{topic}' 주제와 가장 어울리는 것을 quote://all에서 고르고, "
        "그 명언을 인용한 세 문단 분량의 짧은 글을 작성해주세요."
    )


# 6. 서버 실행 / 검색 옵션
# if __name__ == "__main__": 은 "이 파일을 직접 실행했을 때만" 아래 코드를 실행하라는 뜻입니다.
# 자바의 public static void main(String[] args) 와 같은 진입점 역할입니다.
#
# --search 키워드 : 서버를 띄우지 않고, 본문에 키워드가 포함된 명언만 출력한 뒤 종료합니다.
#                  (서버 모드가 아니므로 stdout 출력이 MCP 프로토콜을 깨뜨리지 않습니다.)
# 옵션이 없으면 기본값인 stdio 전송으로 MCP 서버를 실행합니다.
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="명언 MCP 서버")
    parser.add_argument("--search", metavar="KEYWORD",
                        help="명언 본문에 KEYWORD가 포함된 항목만 출력하고 종료")
    args = parser.parse_args()

    if args.search is None:
        mcp.run()
    elif not args.search.strip():
        parser.error("--search 키워드는 비어 있을 수 없습니다.")
    else:
        # 데이터 문제(DB 오류/깨진·잘못된 시드)는 traceback 대신 stderr 메시지와 종료 코드 1로 알립니다.
        try:
            results = search_quotes(args.search)
            lines = [f'{q["text"]} - {q["author"]}' for q in results]
        except (OSError, sqlite3.Error, ValueError, KeyError, TypeError) as e:
            print(f"명언 데이터(quotes.db)를 읽을 수 없습니다: {type(e).__name__}: {e}", file=sys.stderr)
            sys.exit(1)
        for line in lines:
            print(line)
