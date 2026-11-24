"""본문 확보: 원문 추출기 프로토콜, HTML 텍스트화, 본문 선택.

표준 라이브러리만 쓰며 rss_wiki 내부 모듈을 import하지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Protocol

MIN_EXTRACTED_CHARS = 200

_BLOCK_TAGS = frozenset(
    {
        "p", "div", "br", "li", "ul", "ol",
        "h1", "h2", "h3", "h4", "h5", "h6",
        "tr", "td", "th", "blockquote", "pre", "section", "article", "hr",
        "dl", "dt", "dd", "table", "thead", "tbody", "tfoot", "caption",
        "figure", "figcaption", "header", "footer", "nav", "main", "aside",
        "details", "summary", "address",
    }
)
_SKIP_TAGS = frozenset({"script", "style", "title", "noscript", "template"})


class ContentExtractor(Protocol):
    """원문 페이지에서 평문 본문을 추출한다."""

    def extract(self, url: str) -> str | None:
        """url의 본문 평문을 돌려준다.

        가져오기나 추출이 실패하면 예외를 던지지 않고 ``None``을 돌려준다
        (원문 본문 추출 실패는 실패로 치지 않는다).
        """
        ...


class _TextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._skip: dict[str, int] = {}

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag in _SKIP_TAGS:
            self._skip[tag] = self._skip.get(tag, 0) + 1
        elif tag in _BLOCK_TAGS:
            self._parts.append(" ")

    def handle_startendtag(self, tag: str, attrs: list) -> None:
        if tag in _BLOCK_TAGS:
            self._parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP_TAGS:
            if self._skip.get(tag, 0) > 0:
                self._skip[tag] -= 1
        elif tag in _BLOCK_TAGS:
            self._parts.append(" ")

    def handle_data(self, data: str) -> None:
        if not any(self._skip.values()):
            self._parts.append(data)

    def text(self) -> str:
        return " ".join("".join(self._parts).split())


def html_to_text(html: str) -> str:
    """HTML을 평문으로 바꾼다.

    태그를 없애고 문자 참조를 풀며 script/style/title/noscript/template 내용은 버린다. 블록 요소
    경계에만 공백을 넣고, 연속 공백은 하나로 합쳐 앞뒤를 제거한다.
    """
    parser = _TextParser()
    parser.feed(html)
    parser.close()
    return parser.text()


@dataclass(frozen=True)
class Body:
    text: str
    source: str  # "extracted" | "feed"
    truncated: bool


def choose_body(
    extracted: str | None,
    content: str | None,
    summary: str | None,
    *,
    max_chars: int,
    min_chars: int = MIN_EXTRACTED_CHARS,
) -> Body | None:
    """요약에 쓸 본문을 고른다.

    순서: (1) 추출 텍스트(strip)가 min_chars 이상이면 extracted,
    (2) content의 텍스트화 값이 있으면 feed, (3) summary도 같은 방식으로 feed,
    (4) 짧아도 추출 텍스트가 있으면 extracted, (5) 없으면 None.
    선택한 텍스트가 max_chars보다 길면 앞 max_chars자로 자르고 truncated=True.

    Raises:
        ValueError: max_chars 또는 min_chars가 1 미만일 때.
    """
    if max_chars < 1:
        raise ValueError(f"max_chars는 1 이상이어야 합니다: {max_chars}")
    if min_chars < 1:
        raise ValueError(f"min_chars는 1 이상이어야 합니다: {min_chars}")

    ext = (extracted or "").strip()
    chosen: tuple[str, str] | None = None
    if len(ext) >= min_chars:
        chosen = (ext, "extracted")
    else:
        for raw in (content, summary):
            text = html_to_text(raw) if raw else ""
            if text:
                chosen = (text, "feed")
                break
        if chosen is None and ext:
            chosen = (ext, "extracted")
    if chosen is None:
        return None
    text, source = chosen
    if len(text) > max_chars:
        return Body(text[:max_chars], source, True)
    return Body(text, source, False)
