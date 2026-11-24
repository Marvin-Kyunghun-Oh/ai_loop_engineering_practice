"""피드 수집 계층의 데이터 타입, 가져오기 프로토콜, 글 식별 키, 피드 파싱."""

from __future__ import annotations

import http.client
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from urllib.parse import urljoin, urlsplit, urlunsplit

import feedparser

_DEFAULT_PORTS = {"http": 80, "https": 443}


@dataclass(frozen=True)
class FeedEntry:
    guid: str | None
    link: str | None
    title: str
    published: str | None  # ISO8601
    content: str | None
    summary: str | None


@dataclass(frozen=True)
class ParsedFeed:
    title: str | None
    entries: tuple[FeedEntry, ...]


@dataclass(frozen=True)
class FetchResult:
    not_modified: bool
    feed: ParsedFeed | None  # not_modified이면 None
    etag: str | None
    last_modified: str | None


class FeedError(Exception):
    """피드 수집 오류의 기반. 파이프라인은 이것만 잡아 해당 피드를 건너뛴다."""


class FeedFetchError(FeedError):
    """네트워크·HTTP 오류."""


class FeedParseError(FeedError):
    """파싱 오류."""


class FeedFetcher(Protocol):
    def fetch(
        self, url: str, *, etag: str | None = None, last_modified: str | None = None
    ) -> FetchResult:
        """피드를 가져온다.

        Raises:
            FeedFetchError: 네트워크·HTTP 오류.
            FeedParseError: 파싱 오류.
        """
        ...


def normalize_link(url: str) -> str:
    """link를 비교 가능한 형태로 정규화한다.

    공백·fragment·`utm_*` 쿼리 제거, scheme·host 소문자, 기본 포트 제거, 빈 path는 `/`.
    포트를 해석할 수 없으면(숫자가 아니거나 범위 초과) 기본 포트 제거를 하지 않고
    netloc의 `@` 뒤(host:port 원문)를 소문자로 쓴다(userinfo는 그대로).

    Raises:
        ValueError: `urlsplit`이 거부하는 link(예: `http://[::1`).
    """
    parts = urlsplit(url.strip())
    scheme = parts.scheme.lower()
    userinfo_part, at, hostport = parts.netloc.rpartition("@")
    try:
        port = parts.port
    except ValueError:
        netloc = (userinfo_part + at) + hostport.lower()
    else:
        host = (parts.hostname or "").lower()
        if ":" in host:  # IPv6
            host = f"[{host}]"
        netloc = host
        if parts.username is not None:
            userinfo = parts.username
            if parts.password is not None:
                userinfo += ":" + parts.password
            netloc = f"{userinfo}@{netloc}"
        if port is not None and _DEFAULT_PORTS.get(scheme) != port:
            netloc += f":{port}"
    kept = [q for q in parts.query.split("&") if q and not q.startswith("utm_")]
    path = parts.path or "/"
    return urlunsplit((scheme, netloc, path, "&".join(kept), ""))


def entry_key(entry: FeedEntry) -> str | None:
    """글 식별 키. guid 우선, 없으면 정규화한 link, 둘 다 없으면 None.

    예외를 던지지 않는다. 해석할 수 없는 link는 `None`.
    """
    if entry.guid and entry.guid.strip():
        return "guid:" + entry.guid.strip()
    if entry.link and entry.link.strip():
        try:
            return "link:" + normalize_link(entry.link)
        except ValueError:
            return None
    return None


_NO_TITLE = "(제목 없음)"


def _iso(entry) -> str | None:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if not parsed:
        return None
    return datetime(*parsed[:6], tzinfo=UTC).isoformat()


def _absolute(base: str, link: str | None) -> str | None:
    if not link or not link.strip():
        return None
    try:
        return urljoin(base, link.strip())
    except ValueError:
        return link.strip()


def parse_feed(data: bytes, *, url: str) -> ParsedFeed:
    """RSS 2.0·Atom 1.0 바이트를 `ParsedFeed`로 파싱한다.

    항목 하나의 잘못된 link(`urljoin`이 거부)는 예외 없이 앞뒤 공백만 제거한 원문을 유지한다.
    형식은 식별됐지만 bozo인 경우는 항목을 그대로 쓴다.

    Raises:
        FeedParseError: 피드 형식을 식별하지 못함(HTML, 빈 데이터 등). 메시지에 url 포함.
    """
    d = feedparser.parse(data)
    if not d.get("version"):
        raise FeedParseError(f"피드 형식을 식별할 수 없음: {url}")
    entries = []
    for e in d.entries:
        title = (e.get("title") or "").strip() or _NO_TITLE
        contents = e.get("content") or []
        content = contents[0].get("value") if contents else None
        entries.append(
            FeedEntry(
                guid=e.get("id") or None,
                link=_absolute(url, e.get("link")),
                title=title,
                published=_iso(e),
                content=content,
                summary=e.get("summary") or None,
            )
        )
    return ParsedFeed(title=(d.feed.get("title") or None), entries=tuple(entries))


DEFAULT_USER_AGENT = "rss-wiki/0.1"


@dataclass(frozen=True)
class HttpResponse:
    status: int
    headers: Mapping[str, str]  # 생성 시 키를 소문자로 정규화
    body: bytes
    url: str  # 리다이렉트 후 최종 URL

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "headers", {k.lower(): v for k, v in self.headers.items()}
        )


HttpGet = Callable[[str, Mapping[str, str], float], HttpResponse]


def _lower_headers(msg) -> dict[str, str]:
    return {k.lower(): v for k, v in msg.items()}


_URL_SAFE = "/%:@!$&'()*+,;=~"


def _encode_url(url: str) -> str:
    """path·query의 비ASCII 문자를 퍼센트 인코딩한다(기존 `%XX`는 유지)."""
    parts = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit(
        parts._replace(
            path=urllib.parse.quote(parts.path, safe=_URL_SAFE),
            query=urllib.parse.quote(parts.query, safe=_URL_SAFE),
        )
    )


_ALLOWED_SCHEMES = ("http", "https")


def _require_http_url(url: str) -> None:
    """http/https가 아닌 scheme(file, ftp 등)이면 `FeedFetchError`."""
    try:
        scheme = urllib.parse.urlsplit(url).scheme.lower()
    except ValueError as e:
        raise FeedFetchError(f"잘못된 피드 URL: {url} ({e!r})") from e
    if scheme not in _ALLOWED_SCHEMES:
        raise FeedFetchError(
            f"허용되지 않는 URL scheme(허용: {', '.join(_ALLOWED_SCHEMES)}): {url}"
        )


def urllib_get(url: str, headers: Mapping[str, str], timeout: float) -> HttpResponse:
    """`urllib`로 GET한다. HTTP 오류 상태(304 포함)는 예외 없이 `HttpResponse`로 돌려준다.

    Raises:
        FeedFetchError: http/https 이외의 scheme·잘못된 URL·네트워크 오류·타임아웃
            (원인은 `__cause__`).
    """
    _require_http_url(url)
    try:
        req = urllib.request.Request(_encode_url(url), headers=dict(headers))
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return HttpResponse(
                status=resp.status,
                headers=_lower_headers(resp.headers),
                body=resp.read(),
                url=resp.geturl(),
            )
    except urllib.error.HTTPError as e:
        return HttpResponse(
            status=e.code, headers=_lower_headers(e.headers or {}), body=b"", url=url
        )
    except (
        ValueError,
        urllib.error.URLError,
        TimeoutError,
        OSError,
        http.client.HTTPException,
    ) as e:
        raise FeedFetchError(f"피드를 가져오지 못함: {url} ({e!r})") from e


class HttpFeedFetcher:
    """조건부 요청을 지원하는 HTTP 피드 가져오기. `FeedFetcher`를 만족한다."""

    def __init__(
        self,
        *,
        timeout: float,
        user_agent: str = DEFAULT_USER_AGENT,
        http_get: HttpGet = urllib_get,
    ) -> None:
        if timeout <= 0:
            raise ValueError(f"timeout은 0보다 커야 함: {timeout}")
        self._timeout = timeout
        self._user_agent = user_agent
        self._http_get = http_get

    def fetch(
        self, url: str, *, etag: str | None = None, last_modified: str | None = None
    ) -> FetchResult:
        """피드를 가져온다.

        Raises:
            FeedFetchError: http/https 이외의 scheme·네트워크 오류·정수가 아닌 상태·
                2xx/304 이외의 상태 코드.
            FeedParseError: 응답을 피드로 파싱하지 못함.
        """
        _require_http_url(url)
        headers = {"User-Agent": self._user_agent}
        if etag:
            headers["If-None-Match"] = etag
        if last_modified:
            headers["If-Modified-Since"] = last_modified
        resp = self._http_get(url, headers, self._timeout)
        if not isinstance(resp.status, int) or isinstance(resp.status, bool):
            raise FeedFetchError(f"잘못된 HTTP 상태 {resp.status!r}: {url}")
        if resp.status == 304:
            return FetchResult(
                not_modified=True,
                feed=None,
                etag=resp.headers.get("etag") or etag,
                last_modified=resp.headers.get("last-modified") or last_modified,
            )
        if 200 <= resp.status < 300:
            return FetchResult(
                not_modified=False,
                feed=parse_feed(resp.body, url=resp.url),
                etag=resp.headers.get("etag"),
                last_modified=resp.headers.get("last-modified"),
            )
        raise FeedFetchError(f"HTTP {resp.status}: {url}")
