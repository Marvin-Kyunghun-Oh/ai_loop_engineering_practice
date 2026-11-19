# add_quote 입력 검증 테스트: 길이 제한, 빈 값, 줄바꿈. 실제 quotes.json은 건드리지 않는다.
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import main  # noqa: E402


@pytest.fixture
def quotes_file(tmp_path, monkeypatch):
    f = tmp_path / "quotes.json"
    f.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(main, "QUOTES_FILE", f)
    return f


def saved(f):
    return json.loads(f.read_text(encoding="utf-8"))


def test_정상_추가(quotes_file):
    assert "1개" in main.add_quote("시작이 반이다.", "아리스토텔레스")
    assert saved(quotes_file) == [{"text": "시작이 반이다.", "author": "아리스토텔레스"}]


def test_공백은_제거되어_저장(quotes_file):
    main.add_quote("  좋은 말  ", " 저자 ")
    assert saved(quotes_file) == [{"text": "좋은 말", "author": "저자"}]


def test_본문_경계값(quotes_file):
    main.add_quote("가" * main.MAX_TEXT_LEN, "저자")  # 300자는 허용
    with pytest.raises(ValueError, match="301자"):
        main.add_quote("가" * (main.MAX_TEXT_LEN + 1), "저자")
    assert len(saved(quotes_file)) == 1


def test_작성자_경계값(quotes_file):
    main.add_quote("본문", "가" * main.MAX_AUTHOR_LEN)
    with pytest.raises(ValueError):
        main.add_quote("본문", "가" * (main.MAX_AUTHOR_LEN + 1))


@pytest.mark.parametrize("text,author", [("", "저자"), ("   ", "저자"), ("본문", ""), ("본문", "  ")])
def test_빈값_거부(quotes_file, text, author):
    with pytest.raises(ValueError, match="비어"):
        main.add_quote(text, author)
    assert saved(quotes_file) == []


@pytest.mark.parametrize("text,author", [("a\nb", "저자"), ("a\rb", "저자"), ("본문", "a\nb")])
def test_줄바꿈_거부(quotes_file, text, author):
    with pytest.raises(ValueError, match="줄바꿈"):
        main.add_quote(text, author)
    assert saved(quotes_file) == []
