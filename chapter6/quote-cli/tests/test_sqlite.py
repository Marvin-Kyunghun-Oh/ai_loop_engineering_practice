# SQLite 전환 테스트: 마이그레이션, SQL 인젝션 안전성, 리소스 형식.
import json
import sqlite3
import threading

import pytest

import main


def rows(db):
    conn = sqlite3.connect(db)
    try:
        return conn.execute("SELECT text, author FROM quotes ORDER BY id").fetchall()
    finally:
        conn.close()


def test_시드_마이그레이션_한번만(tmp_path, monkeypatch):
    seed = tmp_path / "quotes.json"
    seed.write_text(json.dumps([{"text": "하나", "author": "a"}, {"text": "둘", "author": "b"}], ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(main, "DB_FILE", tmp_path / "x.db")
    monkeypatch.setattr(main, "QUOTES_FILE", seed)
    assert len(main.load_quotes()) == 2
    assert len(main.load_quotes()) == 2          # 재호출해도 중복 가져오기 없음
    main.add_quote("셋", "c")
    assert len(rows(tmp_path / "x.db")) == 3
    assert seed.exists() and len(json.loads(seed.read_text(encoding="utf-8"))) == 2  # 시드 불변


def test_DB가_비어있지_않으면_시드_무시(tmp_path, monkeypatch):
    seed = tmp_path / "quotes.json"
    seed.write_text('[{"text": "시드", "author": "s"}]', encoding="utf-8")
    monkeypatch.setattr(main, "DB_FILE", tmp_path / "x.db")
    monkeypatch.setattr(main, "QUOTES_FILE", seed)
    main.load_quotes()
    seed.write_text('[{"text": "새시드", "author": "s"}]', encoding="utf-8")
    assert [q["text"] for q in main.load_quotes()] == ["시드"]


def test_SQL_인젝션_문자열은_그냥_데이터(db):
    evil = "'); DROP TABLE quotes; --"
    main.add_quote(evil, "x' OR '1'='1")
    main.add_quote("정상", "저자")
    assert [t for t, _ in rows(db)] == [evil, "정상"]   # 테이블이 살아 있고 값 그대로 저장
    assert main.search_quotes("); DROP TABLE") == [{"text": evil, "author": "x' OR '1'='1"}]
    assert len(main.search_quotes("%")) == 0            # 와일드카드도 리터럴로 취급


def test_리소스는_JSON_문자열(db):
    main.add_quote("한글 본문", "저자")
    out = main.all_quotes()
    assert isinstance(out, str) and "한글 본문" in out and "\\u" not in out
    assert json.loads(out) == [{"text": "한글 본문", "author": "저자"}]


def test_get_random_quote_형식(db):
    main.add_quote("본문", "저자")
    assert main.get_random_quote() == "본문 - 저자"


def test_QUOTES_DB_환경변수(tmp_path, monkeypatch):
    import importlib
    monkeypatch.setenv("QUOTES_DB", str(tmp_path / "env.db"))
    try:
        importlib.reload(main)
        assert main.DB_FILE == tmp_path / "env.db"
    finally:
        monkeypatch.delenv("QUOTES_DB")
        importlib.reload(main)


def test_동시_초기화에도_시드는_한번만(tmp_path, monkeypatch):
    # 빈 DB에 여러 연결이 동시에 붙어도 BEGIN IMMEDIATE 덕분에 시드가 중복 삽입되지 않아야 한다.
    seed = tmp_path / "quotes.json"
    seed.write_text(json.dumps([{"text": f"명언{i}", "author": "a"} for i in range(20)], ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(main, "DB_FILE", tmp_path / "race.db")
    monkeypatch.setattr(main, "QUOTES_FILE", seed)
    barrier = threading.Barrier(8)
    errors = []

    def worker():
        try:
            barrier.wait()
            main.load_quotes()
        except Exception as e:  # noqa: BLE001
            errors.append(e)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert errors == []
    assert len(rows(tmp_path / "race.db")) == 20


def test_빈_DB에서_랜덤_조회는_ValueError(db):
    with pytest.raises(ValueError, match="등록된 명언이 없습니다"):
        main.get_random_quote()


@pytest.mark.parametrize("seed_text,match", [
    ('[{"text": "", "author": "a"}]', "비어"),
    (json.dumps([{"text": "가" * 301, "author": "a"}]), "301자"),
    (json.dumps([{"text": "a\nb", "author": "a"}]), "줄바꿈"),
    ('[{"text": "x"}]', "객체"),
    ('{"text": "x"}', "배열"),
])
def test_잘못된_시드는_거부되고_DB는_비어있음(tmp_path, monkeypatch, seed_text, match):
    seed = tmp_path / "quotes.json"
    seed.write_text(seed_text, encoding="utf-8")
    monkeypatch.setattr(main, "DB_FILE", tmp_path / "x.db")
    monkeypatch.setattr(main, "QUOTES_FILE", seed)
    with pytest.raises(ValueError, match=match):
        main.load_quotes()
    seed.unlink()
    assert main.load_quotes() == []   # 롤백되어 일부만 들어간 상태가 없어야 한다


def test_초기화_실패시_연결이_닫힘(tmp_path, monkeypatch):
    seed = tmp_path / "quotes.json"
    seed.write_text("{깨짐", encoding="utf-8")
    monkeypatch.setattr(main, "DB_FILE", tmp_path / "x.db")
    monkeypatch.setattr(main, "QUOTES_FILE", seed)
    opened = []
    real = sqlite3.connect
    monkeypatch.setattr(main.sqlite3, "connect", lambda *a, **k: opened.append(real(*a, **k)) or opened[-1])
    with pytest.raises(ValueError):
        main.load_quotes()
    with pytest.raises(sqlite3.ProgrammingError):   # 닫힌 연결은 사용할 수 없다
        opened[0].execute("SELECT 1")


def test_깨진_DB는_서버_경로에서도_sqlite_오류(tmp_path, monkeypatch):
    bad = tmp_path / "bad.db"
    bad.write_bytes(b"this is not a sqlite database" * 20)
    monkeypatch.setattr(main, "DB_FILE", bad)
    for call in (main.get_random_quote, main.all_quotes, lambda: main.add_quote("a", "b")):
        with pytest.raises(sqlite3.Error):
            call()
