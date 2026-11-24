import ast
import dataclasses

import pytest

from rss_wiki import feeds
from rss_wiki.feeds import (
    FeedEntry,
    FeedError,
    FeedFetchError,
    FeedFetcher,
    FeedParseError,
    FetchResult,
    ParsedFeed,
    entry_key,
    normalize_link,
    parse_feed,
)


@pytest.mark.parametrize(
    "src,expected",
    [
        ("HTTPS://Example.COM:443/a/b?utm_source=x&id=1#top", "https://example.com/a/b?id=1"),
        ("http://example.com:80", "http://example.com/"),
        ("http://example.com:8080/x", "http://example.com:8080/x"),
        ("https://e.com/a/?utm_medium=y", "https://e.com/a/"),
        ("https://e.com/p?b=2&a=1", "https://e.com/p?b=2&a=1"),
        ("https://e.com/A", "https://e.com/A"),
        ("  https://e.com/a  ", "https://e.com/a"),
        ("https://e.com/a?utm_x=1&utm_y=2&k=v&utm_z", "https://e.com/a?k=v"),
        ("http://e.com:443/x", "http://e.com:443/x"),
        ("https://e.com:80/x", "https://e.com:80/x"),
        ("https://E.com:abc/x#f", "https://e.com:abc/x"),
        ("https://e.com:99999/", "https://e.com:99999/"),
        ("https://e.com/a?utmost=1", "https://e.com/a?utmost=1"),
        ("http://[::1]:80/x", "http://[::1]/x"),
        ("https://u:p@E.com:443/a", "https://u:p@e.com/a"),
        ("https://U:P@E.com:abc/x", "https://U:P@e.com:abc/x"),
    ],
)
def test_normalize_link(src, expected):
    assert normalize_link(src) == expected


def _e(guid=None, link=None):
    return FeedEntry(guid=guid, link=link, title="t", published=None, content=None, summary=None)


def test_entry_key_guid():
    assert entry_key(_e(guid="  abc ", link="https://x.com/")) == "guid:abc"


@pytest.mark.parametrize("guid", [None, "", "  "])
def test_entry_key_link_fallback(guid):
    assert entry_key(_e(guid=guid, link="https://example.com/a")) == "link:https://example.com/a"


@pytest.mark.parametrize("link", [None, "", "  "])
def test_entry_key_none(link):
    assert entry_key(_e(guid=None, link=link)) is None


def test_entry_key_same_article_links():
    a = entry_key(_e(link="https://E.com/a#x"))
    b = entry_key(_e(link="https://e.com/a?utm_source=rss"))
    assert a == b


def test_entry_key_bad_port_link():
    assert entry_key(_e(link="https://e.com:abc/")) == "link:https://e.com:abc/"


def test_entry_key_unparsable_link():
    assert entry_key(_e(link="http://[::1")) is None


def test_entry_key_guid_ignores_bad_link():
    assert entry_key(_e(guid="g", link="http://[::1")) == "guid:g"


def test_entry_key_prefix_distinguishes():
    assert entry_key(_e(guid="https://e.com/a")) != entry_key(_e(link="https://e.com/a"))


def test_frozen():
    e = _e(guid="a")
    with pytest.raises(dataclasses.FrozenInstanceError):
        e.guid = "b"  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        ParsedFeed(title=None, entries=()).title = "x"  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        FetchResult(True, None, None, None).etag = "x"  # type: ignore[misc]


def test_error_hierarchy():
    assert issubclass(FeedFetchError, FeedError)
    assert issubclass(FeedParseError, FeedError)


def test_fetcher_protocol_fake():
    class Fake:
        def fetch(self, url, *, etag=None, last_modified=None):
            self.got = (etag, last_modified)
            return FetchResult(
                not_modified=False,
                feed=ParsedFeed(title="T", entries=(_e(guid="g"),)),
                etag="e1",
                last_modified=None,
            )

    f: FeedFetcher = Fake()
    r = f.fetch("https://e.com/feed", etag="x")
    assert r.feed is not None and r.feed.entries[0].guid == "g"
    assert r.etag == "e1"
    f.fetch("https://e.com/feed", etag="e1", last_modified="lm1")
    assert f.got == ("e1", "lm1")  # type: ignore[attr-defined]


def test_no_internal_imports():
    with open(feeds.__file__, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    bad = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.level > 0 or (node.module or "").startswith("rss_wiki"):
                bad.append(ast.dump(node))
        elif isinstance(node, ast.Import):
            bad.extend(a.name for a in node.names if a.name.startswith("rss_wiki"))
    assert bad == []


URL = "https://example.com/feed.xml"

RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/">
<channel><title>한국어 블로그</title>
<item><title>첫 글</title><link>https://example.com/a</link><guid>g-1</guid>
<pubDate>Fri, 20 Nov 2026 00:00:00 GMT</pubDate>
<description>요약 하나</description>
<content:encoded><![CDATA[<p>본문 하나</p>]]></content:encoded></item>
<item><title>둘째 글</title><link>/posts/1</link>
<pubDate>Sat, 21 Nov 2026 09:30:00 +0900</pubDate>
<description>요약 둘</description></item>
</channel></rss>""".encode()

ATOM = b"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"><title>A</title>
<entry><title>t</title><id>urn:x:1</id>
<link rel="self" href="https://example.com/self"/>
<link rel="alternate" href="https://example.com/alt"/>
<updated>2026-11-20T10:00:00Z</updated></entry></feed>"""


def test_parse_rss():
    f = parse_feed(RSS, url=URL)
    assert f.title == "한국어 블로그"
    assert len(f.entries) == 2
    a, b = f.entries
    assert a.title == "첫 글"
    assert a.guid == "g-1"
    assert a.published == "2026-11-20T00:00:00+00:00"
    assert a.summary == "요약 하나"
    assert "본문 하나" in a.content
    assert b.guid is None
    assert b.content is None
    assert b.link == "https://example.com/posts/1"
    assert b.published == "2026-11-21T00:30:00+00:00"
    assert entry_key(a) == "guid:g-1"
    assert entry_key(b) == "link:https://example.com/posts/1"


def test_parse_atom_updated_and_alternate():
    (e,) = parse_feed(ATOM, url=URL).entries
    assert e.guid == "urn:x:1"
    assert e.published == "2026-11-20T10:00:00+00:00"
    assert e.link == "https://example.com/alt"


def test_missing_title_and_date():
    data = b"<rss version='2.0'><channel><item><link>https://e.com/x</link></item></channel></rss>"
    (e,) = parse_feed(data, url=URL).entries
    assert e.title == "(제목 없음)"
    assert e.published is None


@pytest.mark.parametrize("data", [b"<html><body>hi</body></html>", b""])
def test_unrecognized_raises(data):
    with pytest.raises(FeedParseError, match="example.com/feed.xml"):
        parse_feed(data, url=URL)


def test_bad_link_kept():
    data = (
        b"<rss version='2.0'><channel>"
        b"<item><title>bad</title><link>http://[::1</link></item>"
        b"<item><title>ok</title><link>https://e.com/ok</link></item>"
        b"</channel></rss>"
    )
    bad, ok = parse_feed(data, url=URL).entries
    assert bad.link == "http://[::1"
    assert entry_key(bad) is None
    assert entry_key(ok) == "link:https://e.com/ok"


# ---- T6: T5 REVIEW 보강 ----


def test_bozo_feed_still_parsed():
    import feedparser

    data = (
        b"<?xml version='1.0' encoding='UTF-8'?><rss version='2.0'><channel>"
        b"<title>a&nbsp;b</title>"
        b"<item><title>t</title><link>https://e.com/x</link></item>"
        b"</channel></rss>"
    )
    d = feedparser.parse(data)
    assert d.bozo
    assert d.version
    (e,) = parse_feed(data, url=URL).entries
    assert e.title == "t"


def test_empty_values_become_none():
    data = (
        b"<rss version='2.0'><channel><title></title>"
        b"<item><title>t</title><link>https://e.com/x</link>"
        b"<guid></guid><description></description></item>"
        b"</channel></rss>"
    )
    f = parse_feed(data, url=URL)
    assert f.title is None
    (e,) = f.entries
    assert e.guid is None
    assert e.summary is None


def test_bad_link_whitespace_stripped():
    data = (
        b"<rss version='2.0'><channel><item><title>t</title>"
        b"<link>  http://[::1  </link></item></channel></rss>"
    )
    (e,) = parse_feed(data, url=URL).entries
    assert e.link == "http://[::1"


# ---- T6: HttpFeedFetcher ----

from rss_wiki.feeds import HttpFeedFetcher, HttpResponse, urllib_get  # noqa: E402


class FakeGet:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def __call__(self, url, headers, timeout):
        self.calls.append((url, dict(headers), timeout))
        return self.response


def _resp(status=200, headers=None, body=RSS, url=URL):
    return HttpResponse(status=status, headers=headers or {}, body=body, url=url)


def test_fetch_no_conditional_headers():
    g = FakeGet(_resp())
    HttpFeedFetcher(timeout=7, http_get=g).fetch(URL)
    url, headers, timeout = g.calls[0]
    assert url == URL
    assert headers == {"User-Agent": "rss-wiki/0.1"}
    assert timeout == 7


def test_fetch_conditional_headers():
    g = FakeGet(_resp())
    HttpFeedFetcher(timeout=5, http_get=g).fetch(URL, etag="e1", last_modified="lm1")
    headers = g.calls[0][1]
    assert headers["If-None-Match"] == "e1"
    assert headers["If-Modified-Since"] == "lm1"


def test_fetch_304_keeps_given_values():
    g = FakeGet(_resp(304, body=b""))
    r = HttpFeedFetcher(timeout=5, http_get=g).fetch(URL, etag="e1", last_modified="lm1")
    assert r.not_modified is True
    assert r.feed is None
    assert r.etag == "e1"
    assert r.last_modified == "lm1"


def test_fetch_304_uses_response_headers():
    g = FakeGet(_resp(304, headers={"etag": "e9", "last-modified": "lm9"}, body=b""))
    r = HttpFeedFetcher(timeout=5, http_get=g).fetch(URL, etag="e1")
    assert (r.etag, r.last_modified) == ("e9", "lm9")


def test_fetch_200():
    g = FakeGet(_resp(headers={"etag": "E", "last-modified": "LM"}))
    r = HttpFeedFetcher(timeout=5, http_get=g).fetch(URL)
    assert r.not_modified is False
    assert len(r.feed.entries) == 2
    assert (r.etag, r.last_modified) == ("E", "LM")


def test_fetch_200_without_headers():
    r = HttpFeedFetcher(timeout=5, http_get=FakeGet(_resp())).fetch(URL)
    assert r.etag is None and r.last_modified is None


def test_fetch_resolves_relative_against_final_url():
    g = FakeGet(_resp(url="https://cdn.example.org/f.xml"))
    r = HttpFeedFetcher(timeout=5, http_get=g).fetch(URL)
    assert r.feed.entries[1].link == "https://cdn.example.org/posts/1"


@pytest.mark.parametrize("status", [404, 500])
def test_fetch_http_error(status):
    g = FakeGet(_resp(status, body=b""))
    with pytest.raises(FeedFetchError) as ei:
        HttpFeedFetcher(timeout=5, http_get=g).fetch(URL)
    assert str(status) in str(ei.value)
    assert URL in str(ei.value)


def test_fetch_html_is_parse_error():
    g = FakeGet(_resp(body=b"<html><body>hi</body></html>"))
    with pytest.raises(FeedParseError):
        HttpFeedFetcher(timeout=5, http_get=g).fetch(URL)


@pytest.mark.parametrize("t", [0, -1])
def test_timeout_must_be_positive(t):
    with pytest.raises(ValueError):
        HttpFeedFetcher(timeout=t)


def test_http_fetcher_satisfies_protocol():
    f: FeedFetcher = HttpFeedFetcher(timeout=1, http_get=FakeGet(_resp()))
    assert f.fetch(URL).feed is not None


@pytest.mark.parametrize("exc", [lambda: __import__("urllib.error").error.URLError("boom"), lambda: TimeoutError("t")])
def test_urllib_get_maps_errors(monkeypatch, exc):
    err = exc()

    def boom(*a, **k):
        raise err

    monkeypatch.setattr("urllib.request.urlopen", boom)
    with pytest.raises(FeedFetchError, match="example.com") as ei:
        urllib_get(URL, {}, 1)
    assert ei.value.__cause__ is err


def test_urllib_get_http_error_returns_response(monkeypatch):
    import email.message
    import urllib.error

    hdrs = email.message.Message()
    hdrs["ETag"] = "abc"

    def boom(*a, **k):
        raise urllib.error.HTTPError(URL, 304, "Not Modified", hdrs, None)

    monkeypatch.setattr("urllib.request.urlopen", boom)
    r = urllib_get(URL, {}, 1)
    assert r.status == 304
    assert r.body == b""
    assert r.headers["etag"] == "abc"


def test_absolute_strips_on_urljoin_failure():
    # feedparser가 이미 공백을 제거하므로 내부 헬퍼를 직접 확인한다.
    assert feeds._absolute(URL, "  http://[::1  ") == "http://[::1"


# ---- T6r: HttpFeedFetcher 견고성 ----

import email.message  # noqa: E402
import http.client  # noqa: E402
import urllib.request  # noqa: E402


class FakeUrlopen:
    def __init__(self, *, headers=None, final_url="https://e.com/final", body=b"BODY", exc=None):
        self.requests = []
        self.timeouts = []
        self._headers = headers or {}
        self._final = final_url
        self._body = body
        self._exc = exc

    def __call__(self, req, timeout=None):
        self.requests.append(req)
        self.timeouts.append(timeout)
        if self._exc is not None:
            raise self._exc
        msg = email.message.Message()
        for k, v in self._headers.items():
            msg[k] = v
        outer = self

        class R:
            status = 200
            headers = msg

            def read(self):
                return outer._body

            def geturl(self):
                return outer._final

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        return R()


def test_urllib_get_success_path(monkeypatch):
    fake = FakeUrlopen(headers={"ETag": "X"})
    monkeypatch.setattr(urllib.request, "urlopen", fake)
    r = urllib_get(
        "https://e.com/feed", {"User-Agent": "ua/1", "If-None-Match": "e1"}, 7.5
    )
    req = fake.requests[0]
    assert req.get_header("User-agent") == "ua/1"
    assert req.get_header("If-none-match") == "e1"
    assert fake.timeouts == [7.5]
    assert r.headers["etag"] == "X"
    assert r.url == "https://e.com/final"
    assert r.body == b"BODY"


def test_custom_user_agent():
    g = FakeGet(_resp())
    HttpFeedFetcher(timeout=1, user_agent="custom/9", http_get=g).fetch(URL)
    assert g.calls[0][1]["User-Agent"] == "custom/9"


def test_header_normalization_in_response_and_fetch():
    r = HttpResponse(200, {"ETag": "X", "Last-Modified": "LM"}, RSS, URL)
    assert all(k == k.lower() for k in r.headers)
    res = HttpFeedFetcher(timeout=1, http_get=FakeGet(r)).fetch(URL)
    assert res.etag == "X" and res.last_modified == "LM"
    r304 = HttpResponse(304, {"ETag": "Y"}, b"", URL)
    res = HttpFeedFetcher(timeout=1, http_get=FakeGet(r304)).fetch(URL)
    assert res.not_modified and res.etag == "Y"


def test_non_ascii_url_encoded(monkeypatch):
    fake = FakeUrlopen()
    monkeypatch.setattr(urllib.request, "urlopen", fake)
    urllib_get("https://e.com/tag/한글/feed?q=값", {}, 1)
    assert (
        fake.requests[0].full_url
        == "https://e.com/tag/%ED%95%9C%EA%B8%80/feed?q=%EA%B0%92"
    )
    urllib_get("https://e.com/a%20b", {}, 1)
    assert fake.requests[1].full_url == "https://e.com/a%20b"


@pytest.mark.parametrize("bad", ["not a url", "http://[::1"])
def test_invalid_url_wrapped(monkeypatch, bad):
    monkeypatch.setattr(urllib.request, "urlopen", FakeUrlopen())
    with pytest.raises(FeedFetchError) as ei:
        urllib_get(bad, {}, 1)
    assert bad in str(ei.value)
    if bad.startswith("http"):  # scheme 없는 입력은 scheme 검사에서 원인 없이 거부됨(T6s)
        assert isinstance(ei.value.__cause__, ValueError)
    with pytest.raises(FeedFetchError):
        HttpFeedFetcher(timeout=1).fetch(bad)


@pytest.mark.parametrize(
    "exc", [ConnectionResetError(), http.client.IncompleteRead(b"")]
)
def test_urllib_get_maps_more_errors(monkeypatch, exc):
    monkeypatch.setattr(urllib.request, "urlopen", FakeUrlopen(exc=exc))
    with pytest.raises(FeedFetchError) as ei:
        urllib_get(URL, {}, 1)
    assert ei.value.__cause__ is exc


@pytest.mark.parametrize("status", [204, 299])
def test_fetch_2xx_boundary_ok(status):
    res = HttpFeedFetcher(timeout=1, http_get=FakeGet(_resp(status=status))).fetch(URL)
    assert res.not_modified is False and res.feed is not None


def test_fetch_300_is_error():
    with pytest.raises(FeedFetchError, match="300"):
        HttpFeedFetcher(timeout=1, http_get=FakeGet(_resp(status=300))).fetch(URL)


# ---- T6s: URL scheme 제한과 응답 방어 ----


def _reject_urls(tmp_path):
    f = tmp_path / "feed.xml"
    f.write_bytes(RSS)
    return [f.as_uri(), "ftp://x/y", "javascript:alert(1)", "//e.com/feed"]


@pytest.mark.parametrize("idx", [0, 1, 2, 3])
def test_fetch_rejects_non_http_scheme(tmp_path, idx):
    url = _reject_urls(tmp_path)[idx]
    g = FakeGet(_resp())
    with pytest.raises(FeedFetchError) as ei:
        HttpFeedFetcher(timeout=1, http_get=g).fetch(url)
    assert url in str(ei.value)
    assert g.calls == []


@pytest.mark.parametrize("idx", [0, 1, 2, 3])
def test_urllib_get_rejects_non_http_scheme(tmp_path, monkeypatch, idx):
    url = _reject_urls(tmp_path)[idx]
    fake = FakeUrlopen()
    monkeypatch.setattr(urllib.request, "urlopen", fake)
    with pytest.raises(FeedFetchError) as ei:
        urllib_get(url, {}, 1)
    assert url in str(ei.value)
    assert fake.requests == []


def test_require_http_url_wraps_urlsplit_value_error():
    with pytest.raises(FeedFetchError) as ei:
        feeds._require_http_url("http://[::1")
    assert isinstance(ei.value.__cause__, ValueError)


@pytest.mark.parametrize("url", ["HTTPS://e.com/feed", "Http://e.com/feed"])
def test_fetch_scheme_case_insensitive(url):
    g = FakeGet(_resp(url=url))
    r = HttpFeedFetcher(timeout=1, http_get=g).fetch(url)
    assert len(g.calls) == 1
    assert len(r.feed.entries) == 2


def test_fetch_non_int_status():
    g = FakeGet(HttpResponse(status=None, headers={}, body=RSS, url=URL))
    with pytest.raises(FeedFetchError, match="None"):
        HttpFeedFetcher(timeout=1, http_get=g).fetch(URL)


def test_fetch_bool_status_rejected():
    g = FakeGet(HttpResponse(status=True, headers={}, body=RSS, url=URL))
    with pytest.raises(FeedFetchError, match="잘못된 HTTP 상태"):
        HttpFeedFetcher(timeout=1, http_get=g).fetch(URL)


def test_urllib_get_http_error_without_headers(monkeypatch):
    import urllib.error

    def boom(*a, **k):
        raise urllib.error.HTTPError(URL, 304, "nm", None, None)

    monkeypatch.setattr(urllib.request, "urlopen", boom)
    r = urllib_get(URL, {}, 1)
    assert r.status == 304
    assert r.headers == {}
