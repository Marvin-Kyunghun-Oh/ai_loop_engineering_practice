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
#   quotes.json 파일 준비      # 이 파일과 같은 폴더에 둡니다
# =============================================================================

# --- import: 자바의 import와 같은 역할 ---------------------------------------
import argparse                          # 명령줄 옵션 파싱 (표준 라이브러리)
import json                              # JSON 읽기/쓰기 (표준 라이브러리)
import sys                               # stderr 출력, 종료 코드 (표준 라이브러리)
import random                            # 무작위 선택 (표준 라이브러리)
from pathlib import Path                 # 파일 경로 다루기 (자바의 java.nio.file.Path와 비슷)
from mcp.server.mcpserver import MCPServer   # MCP 서버를 쉽게 만들어 주는 클래스 (mcp 2.x에서 FastMCP → MCPServer로 개명)

# 1. 서버 객체 생성
# MCPServer("quote")로 서버 객체를 만듭니다. "quote"는 서버 이름입니다.
# 아래에서 이 객체(mcp)의 데코레이터(@mcp.tool() 등)를 함수에 붙이면,
# 해당 함수가 MCP 규격에 맞는 기능으로 외부(클로드 코드)에 노출됩니다.
mcp = MCPServer("quote")

# 명언 데이터 파일 경로
# __file__ 은 "지금 실행 중인 이 파일(main.py)의 경로"입니다.
# .parent 로 그 폴더를 구하고, / 연산자로 "quotes.json"을 이어 붙입니다.
# → main.py와 같은 폴더에 있는 quotes.json을 가리킵니다.
# (대문자 변수명은 파이썬에서 "상수"라는 관례적 표시입니다. 자바의 static final과 비슷)
QUOTES_FILE = Path(__file__).parent / "quotes.json"


def load_quotes() -> list:
    # 헬퍼 함수: quotes.json을 읽어 파이썬 리스트로 돌려줍니다.
    # 데코레이터가 없으므로 MCP에 노출되지 않는 내부용 함수입니다.
    # "-> list"는 반환 타입 힌트입니다 (자바의 List<...> 반환 선언과 비슷).
    # 파일 내용 예: [{"text": "명언 내용", "author": "작가"}, ...]
    return json.loads(QUOTES_FILE.read_text(encoding="utf-8"))


def search_quotes(keyword: str) -> list:
    # 헬퍼 함수: 명언 "본문(text)"에 keyword가 포함된 항목만 돌려줍니다.
    # 작성자(author)는 검색 대상이 아닙니다. 영문 대소문자는 구분하지 않습니다.
    # 자바의 text.toLowerCase().contains(...) 와 같습니다.
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
    quote = random.choice(load_quotes())   # 리스트에서 하나를 무작위로 고름
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
    return value


# 3. 명언 추가 도구 (쓰기형)
# '2'와 같은 방식의 도구지만, 파일에 새 명언을 추가하는 "쓰기" 동작을 합니다.
# 매개변수 text, author 의 타입 힌트(str)가 입력 스키마가 되므로,
# Claude는 이 도구를 호출할 때 text와 author 두 문자열을 넘겨줍니다.
@mcp.tool()
def add_quote(text: str, author: str) -> str:
    """새 명언을 명언 목록에 추가합니다. 본문은 1~300자, 작성자는 1~50자이며 줄바꿈은 허용되지 않습니다."""
    text = validate_quote_field("명언 본문", text, MAX_TEXT_LEN)
    author = validate_quote_field("작성자", author, MAX_AUTHOR_LEN)
    quotes = load_quotes()                              # 기존 목록 읽기
    quotes.append({"text": text, "author": author})     # 새 명언을 목록 끝에 추가
    QUOTES_FILE.write_text(                             # 파일에 다시 저장
        # ensure_ascii=False : 한글을 \uXXXX로 바꾸지 않고 그대로 저장
        # indent=2           : 사람이 읽기 좋게 2칸 들여쓰기
        json.dumps(quotes, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    # len(quotes) 는 리스트 길이입니다 (자바의 quotes.size()).
    return f"명언을 추가했습니다. 현재 {len(quotes)}개입니다."


# 4. 리소스
# @mcp.resource("quote://all") 은 "quote://all" 이라는 URI로 접근할 수 있는
# 리소스를 만듭니다. 도구가 "실행하는 기능"이라면, 리소스는 "읽어 가는 데이터"입니다.
# 클로드 코드에서는 @ 멘션으로 이 리소스를 대화에 불러올 수 있습니다.
@mcp.resource("quote://all")
def all_quotes() -> str:
    """전체 명언 목록을 반환합니다."""
    return QUOTES_FILE.read_text(encoding="utf-8")   # JSON 파일 내용을 문자열 그대로 반환


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
        # 데이터 파일 문제(없음/깨진 JSON/키 누락)는 traceback 대신 stderr 메시지와 종료 코드 1로 알립니다.
        try:
            results = search_quotes(args.search)
            lines = [f'{q["text"]} - {q["author"]}' for q in results]
        except (OSError, json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"quotes.json을 읽을 수 없습니다: {type(e).__name__}: {e}", file=sys.stderr)
            sys.exit(1)
        for line in lines:
            print(line)
