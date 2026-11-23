import asyncio

import pytest

from rss_wiki.pipeline.extractor import extract_article, strip_html
from rss_wiki.pipeline.fetcher import (FeedFetchError, ParsedFeed, fetch_feed, fetch_many,
                                       parse_feed_bytes)
from rss_wiki.pipeline.retry import with_backoff

RSS = """<?xml version="1.0"?><rss version="2.0"><channel><title>테스트 피드</title>
<item><title>글 하나</title><link>https://a.com/1</link><guid>g1</guid>
<pubDate>Sun, 22 Nov 2026 09:00:00 GMT</pubDate><description>&lt;p&gt;요약&lt;/p&gt;</description></item>
<item><title>링크 없음</title></item>
</channel></rss>""".encode()


def run(c):
    return asyncio.run(c)


async def nosleep(_):
    pass


def test_parse_feed_bytes():
    feed = parse_feed_bytes(RSS)
    assert feed.title == "테스트 피드" and len(feed.entries) == 1
    e = feed.entries[0]
    assert (e.url, e.title) == ("https://a.com/1", "글 하나")
    assert e.published_at == "2026-11-22T09:00:00+00:00" and "요약" in e.raw_summary


def test_parse_garbage_raises():
    with pytest.raises(FeedFetchError):
        parse_feed_bytes(b"this is not a feed")


def test_fetch_feed_retries_then_succeeds():
    calls, sleeps = [], []

    async def download(url, timeout):
        calls.append(1)
        if len(calls) < 3:
            raise ConnectionError("reset")
        return RSS

    async def sl(s):
        sleeps.append(s)

    feed = run(fetch_feed("https://a.com/rss", download=download, sleep=sl))
    assert len(feed.entries) == 1 and sleeps == [2, 4]


def test_fetch_feed_gives_up_after_three_retries():
    calls = []

    async def download(url, timeout):
        calls.append(1)
        raise ConnectionError("down")

    with pytest.raises(FeedFetchError) as e:
        run(fetch_feed("https://a.com/rss", download=download, sleep=nosleep))
    assert len(calls) == 4 and e.value.attempts == 4


def test_fetch_feed_timeout():
    async def slow(url, timeout):
        await asyncio.sleep(5)

    with pytest.raises(FeedFetchError, match="타임아웃"):
        run(fetch_feed("https://a.com/rss", download=slow, timeout=0.05, sleep=nosleep))


def test_fetch_many_limits_concurrency_and_isolates_failures():
    active = peak = 0

    async def fake(url):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0.01)
        active -= 1
        if "bad" in url:
            raise FeedFetchError("nf")
        return ParsedFeed(title=url)

    feeds = [(i, f"https://a.com/{i}") for i in range(12)] + [(99, "https://bad.com")]
    res = run(fetch_many(feeds, fetch=fake, concurrency=5))
    assert peak == 5 and len(res) == 13
    assert isinstance(res[99], FeedFetchError) and res[3].title == "https://a.com/3"


def test_with_backoff_non_retryable_passes_through():
    async def boom():
        raise KeyError("x")

    with pytest.raises(KeyError):
        run(with_backoff(boom, retryable=(ValueError,), sleep=nosleep))


def test_strip_html():
    assert strip_html("<p>안녕 <b>세상</b></p><script>x()</script>&amp;") == "안녕 세상 &"


def test_extract_success():
    r = run(extract_article("https://a.com/1", "<p>요약</p>", extract=lambda u: "<p>전문 본문</p>"))
    assert (r.content, r.source, r.error) == ("전문 본문", "extracted", None)


def test_extract_error_retried_then_falls_back_to_rss():
    calls = []

    def boom(url):
        calls.append(1)
        raise ConnectionError("fail")

    r = run(extract_article("https://a.com/1", "<p>RSS 요약</p>", extract=boom, sleep=nosleep))
    assert (r.content, r.source, r.attempts) == ("RSS 요약", "rss", 4)
    assert len(calls) == 4 and "ConnectionError" in r.error


def test_extract_empty_falls_back_without_retry():
    calls = []

    def empty(url):
        calls.append(1)

    r = run(extract_article("https://a.com/1", "요약", extract=empty, sleep=nosleep))
    assert r.source == "rss" and r.content == "요약" and len(calls) == 1 and "비어" in r.error


def test_extract_timeout_falls_back():
    import time

    r = run(extract_article("https://a.com/1", "요약", extract=lambda u: time.sleep(0.5),
                            timeout=0.05, sleep=nosleep))
    assert r.source == "rss" and "타임아웃" in r.error
