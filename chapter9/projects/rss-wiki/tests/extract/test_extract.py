import ast
import dataclasses
from pathlib import Path

import pytest

from rss_wiki import extract
from rss_wiki.extract import Body, ContentExtractor, choose_body, html_to_text


@pytest.mark.parametrize(
    "html,expected",
    [
        ("<p>a</p><p>b</p>", "a b"),
        ("<b>un</b>believable", "unbelievable"),
        ("a<br>b", "a b"),
        ("a&amp;b &#xAC00; &lt;x&gt;", "a&b 가 <x>"),
        ("<script>bad()</script>ok<style>.x{}</style>", "ok"),
        ("<SCRIPT>bad()</SCRIPT>ok", "ok"),
        ("  x \n\t y  ", "x y"),
        ("<p>a<div>b", "a b"),
        ("", ""),
        ("<p>양자 컴퓨팅</p>", "양자 컴퓨팅"),
        ("a<br/>b", "a b"),
        ("a</script>b", "ab"),
        ("a<b>c</b>d", "acd"),
        ("Py<span>thon</span>", "Python"),
        ("<dl><dt>a</dt><dd>b</dd></dl>", "a b"),
        ("<figure>a<figcaption>b</figcaption></figure>", "a b"),
        ("<header>a</header><footer>b</footer>", "a b"),
        ("<table><tr><td>a</td></tr></table><p>b</p>", "a b"),
        ("<title>t</title>ok", "ok"),
        ("<noscript>n</noscript>ok", "ok"),
        ("<template><p>x</p></template>ok", "ok"),
    ],
)
def test_html_to_text(html, expected):
    assert html_to_text(html) == expected


BLOCK_LITERAL = (
    "p div br li ul ol h1 h2 h3 h4 h5 h6 tr td th blockquote pre section article hr "
    "dl dt dd table thead tbody tfoot caption figure figcaption header footer nav main "
    "aside details summary address"
).split()
SKIP_LITERAL = "script style title noscript template".split()


@pytest.mark.parametrize("tag", [t for t in BLOCK_LITERAL if t not in ("br", "hr")])
def test_block_tag_separates(tag):
    assert html_to_text(f"a<{tag}>b</{tag}>c") == "a b c"


@pytest.mark.parametrize("html", ["a<br>b", "a<hr>b", "a<hr/>b"])
def test_void_block_tags(html):
    assert html_to_text(html) == "a b"


@pytest.mark.parametrize("tag", SKIP_LITERAL)
def test_skip_tag_content_dropped(tag):
    assert html_to_text(f"a<{tag}>x</{tag}>ok") == "aok"


def test_tag_lists_match_literals():
    assert len(BLOCK_LITERAL) == 38
    assert set(BLOCK_LITERAL) == extract._BLOCK_TAGS
    assert set(SKIP_LITERAL) == extract._SKIP_TAGS


@pytest.mark.parametrize(
    "html,expected",
    [
        ("<noscript>a</script>b</noscript>ok", "ok"),
        ("<noscript><noscript>x</noscript>y</noscript>ok", "ok"),
        ("<template>a</noscript>b</template>ok", "ok"),
        ("a</script>b<script>x</script>c", "abc"),
        ("a</script>b", "ab"),
    ],
)
def test_skip_depth_per_tag(html, expected):
    assert html_to_text(html) == expected


def test_boundary_200_is_extracted():
    b = choose_body("x" * 200, "<p>c</p>", None, max_chars=1000)
    assert b == Body("x" * 200, "extracted", False)


def test_199_falls_back_to_content():
    assert choose_body("x" * 199, "<p>본문</p>", None, max_chars=1000) == Body("본문", "feed", False)


def test_summary_used_when_content_empty():
    assert choose_body(None, "<p> </p>", "<i>요약</i>", max_chars=100) == Body("요약", "feed", False)


def test_content_before_summary():
    assert choose_body(None, "<p>요약</p>", None, max_chars=100) == Body("요약", "feed", False)
    assert choose_body(None, "<p>C</p>", "<p>S</p>", max_chars=100).text == "C"


def test_content_equals_summary():
    assert choose_body(None, "<p>같음</p>", "<p>같음</p>", max_chars=100) == Body("같음", "feed", False)


def test_short_extracted_last_resort():
    assert choose_body("  짧음  ", None, None, max_chars=100) == Body("짧음", "extracted", False)


@pytest.mark.parametrize("ext", [None, "", "  ", "\n\t"])
@pytest.mark.parametrize("content", [None, "", "  ", "<p></p>"])
@pytest.mark.parametrize("summary", [None, "", "  ", "<p></p>"])
def test_all_empty_is_none(ext, content, summary):
    assert choose_body(ext, content, summary, max_chars=100) is None


def test_truncate_extracted():
    t = "a" * 300
    assert choose_body(t, None, None, max_chars=300) == Body(t, "extracted", False)
    b = choose_body(t, None, None, max_chars=299)
    assert len(b.text) == 299 and b.truncated is True


def test_truncate_feed():
    assert choose_body(None, "<p>abcdef</p>", None, max_chars=6) == Body("abcdef", "feed", False)
    assert choose_body(None, "<p>abcdefg</p>", None, max_chars=6) == Body("abcdef", "feed", True)


@pytest.mark.parametrize("kw", [{"max_chars": 0}, {"max_chars": 5, "min_chars": 0}])
def test_validation(kw):
    with pytest.raises(ValueError):
        choose_body(None, None, None, **kw)


def test_body_frozen():
    b = Body("a", "feed", False)
    with pytest.raises(dataclasses.FrozenInstanceError):
        b.text = "b"


def test_protocol_conformance():
    class Fake:
        def __init__(self):
            self.urls = []

        def extract(self, url):
            self.urls.append(url)
            return "본문"

    fake = Fake()
    ex: ContentExtractor = fake
    assert ex.extract("https://e.com/a") == "본문"
    assert fake.urls == ["https://e.com/a"]


def test_no_internal_imports():
    tree = ast.parse(Path(extract.__file__).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert node.level == 0
            assert not (node.module or "").startswith("rss_wiki")
        elif isinstance(node, ast.Import):
            assert not any(a.name.startswith("rss_wiki") for a in node.names)
