# add_quote 입력 검증 테스트: 길이 제한, 빈 값, 줄바꿈. 실제 quotes.json은 건드리지 않는다.
import sqlite3

import pytest

import main


def saved(db):
    # 테스트가 직접 DB를 열어 저장된 행을 확인한다.
    main.load_quotes()  # 거부 테스트처럼 아직 DB가 없을 수 있으므로 테이블을 보장한다
    conn = sqlite3.connect(db)
    try:
        return [{"text": t, "author": a} for t, a in conn.execute("SELECT text, author FROM quotes ORDER BY id")]
    finally:
        conn.close()


def test_정상_추가(db):
    assert "1개" in main.add_quote("시작이 반이다.", "아리스토텔레스")
    assert saved(db) == [{"text": "시작이 반이다.", "author": "아리스토텔레스"}]


def test_공백은_제거되어_저장(db):
    main.add_quote("  좋은 말  ", " 저자 ")
    assert saved(db) == [{"text": "좋은 말", "author": "저자"}]


def test_본문_경계값(db):
    main.add_quote("가" * main.MAX_TEXT_LEN, "저자")  # 300자는 허용
    with pytest.raises(ValueError, match="301자"):
        main.add_quote("가" * (main.MAX_TEXT_LEN + 1), "저자")
    assert len(saved(db)) == 1


def test_작성자_경계값(db):
    main.add_quote("본문", "가" * main.MAX_AUTHOR_LEN)
    with pytest.raises(ValueError):
        main.add_quote("본문", "가" * (main.MAX_AUTHOR_LEN + 1))


@pytest.mark.parametrize("text,author", [("", "저자"), ("   ", "저자"), ("본문", ""), ("본문", "  ")])
def test_빈값_거부(db, text, author):
    with pytest.raises(ValueError, match="비어"):
        main.add_quote(text, author)
    assert saved(db) == []


@pytest.mark.parametrize("text,author", [("a\nb", "저자"), ("a\rb", "저자"), ("본문", "a\nb")])
def test_줄바꿈_거부(db, text, author):
    with pytest.raises(ValueError, match="줄바꿈"):
        main.add_quote(text, author)
    assert saved(db) == []


@pytest.mark.parametrize("text,author", [("a\tb", "저자"), ("a\x00b", "저자"), ("본문", "a\u2028b")])
def test_제어문자_거부(db, text, author):
    with pytest.raises(ValueError, match="제어 문자"):
        main.add_quote(text, author)
    assert saved(db) == []
