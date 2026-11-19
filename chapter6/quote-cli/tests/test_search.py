# --search 옵션 테스트: 본문 검색 함수와 CLI 동작을 검증한다.
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import main  # noqa: E402


def run_cli(*args, db=None):
    # QUOTES_DB 환경변수로 DB를 임시 경로로 돌린다 (시드는 실제 quotes.json 을 읽기만 함).
    env = {**os.environ, "PYTHONUTF8": "1"}
    if db is not None:
        env["QUOTES_DB"] = str(db)
    return subprocess.run(
        [sys.executable, str(ROOT / "main.py"), *args],
        capture_output=True, text=True, encoding="utf-8", timeout=30, env=env,
    )


def seed(db, rows):
    main.load_quotes()  # 테이블 생성
    for t, a in rows:
        main.add_quote(t, a)


def test_본문에_포함된_항목만_반환(db):
    seed(db, [("실패는 성공의 어머니다.", "에디슨"), ("시작이 반이다.", "노자")])
    assert main.search_quotes("성공") == [{"text": "실패는 성공의 어머니다.", "author": "에디슨"}]


def test_작성자만_일치하면_제외(db):
    seed(db, [("시작이 반이다.", "노자")])
    assert main.search_quotes("노자") == []


def test_앞뒤_공백_키워드는_제거후_검색(db):
    seed(db, [("성공하라", "a")])
    assert main.search_quotes(" 성공 ") == main.search_quotes("성공") != []


def test_대소문자_무시(db):
    seed(db, [("Hello World", "a"), ("ÄRGER", "b")])
    assert len(main.search_quotes("hello")) == 1
    assert len(main.search_quotes("ärger")) == 1  # LIKE였다면 놓쳤을 비ASCII 대소문자


def test_cli_출력(tmp_path):
    # 실제 quotes.json 내용에 의존하지 않도록, 고정 시드를 둔 임시 폴더에서 실행한다.
    seed_json = '[{"text": "실패는 성공의 어머니다.", "author": "에디슨"}, {"text": "시작이 반이다.", "author": "노자"}]'
    r = run_cli_with_data(tmp_path, seed_json, keyword="성공")
    assert r.returncode == 0
    assert r.stdout.strip().splitlines() == ["실패는 성공의 어머니다. - 에디슨"]


def test_cli_결과없음(tmp_path):
    r = run_cli("--search", "존재하지않는키워드xyz", db=tmp_path / "t.db")
    assert r.returncode == 0 and r.stdout == ""


def test_cli_빈_키워드는_오류(tmp_path):
    assert run_cli("--search", "  ", db=tmp_path / "t.db").returncode == 2


def run_cli_with_data(tmp_path, seed_content, db_content=None, keyword="a", seed_bytes=None):
    # main.py를 임시 폴더로 복사하고, 그 옆에 원하는 quotes.json(시드)을 두어 실행한다.
    import shutil
    shutil.copy(ROOT / "main.py", tmp_path / "main.py")
    if seed_bytes is not None:
        (tmp_path / "quotes.json").write_bytes(seed_bytes)
    elif seed_content is not None:
        (tmp_path / "quotes.json").write_text(seed_content, encoding="utf-8")
    db = tmp_path / "t.db"
    if db_content is not None:
        db.write_bytes(db_content)
    return subprocess.run(
        [sys.executable, str(tmp_path / "main.py"), "--search", keyword],
        capture_output=True, text=True, encoding="utf-8", timeout=30,
        env={**os.environ, "PYTHONUTF8": "1", "QUOTES_DB": str(db)},
    )


def test_cli_시드없으면_빈_결과(tmp_path):
    r = run_cli_with_data(tmp_path, None)
    assert r.returncode == 0 and r.stdout == ""


def test_cli_깨진_시드JSON은_오류메시지(tmp_path):
    r = run_cli_with_data(tmp_path, "{깨짐")
    assert r.returncode == 1 and "Traceback" not in r.stderr


def test_cli_시드_키누락은_오류메시지(tmp_path):
    r = run_cli_with_data(tmp_path, '[{"author": "x"}]')
    assert r.returncode == 1 and "Traceback" not in r.stderr


def test_cli_깨진_DB는_오류메시지(tmp_path):
    r = run_cli_with_data(tmp_path, None, db_content=b"this is not a sqlite database" * 20)
    assert r.returncode == 1 and "quotes.db" in r.stderr and "Traceback" not in r.stderr


def test_cli_UTF8이_아닌_시드는_오류메시지(tmp_path):
    r = run_cli_with_data(tmp_path, None, seed_bytes=b"\xff\xfe\x00broken")
    assert r.returncode == 1 and "Traceback" not in r.stderr


def test_cli_검증에_걸리는_시드는_오류메시지(tmp_path):
    r = run_cli_with_data(tmp_path, '[{"text": "' + "가" * 301 + '", "author": "x"}]')
    assert r.returncode == 1 and "301자" in r.stderr and "Traceback" not in r.stderr
