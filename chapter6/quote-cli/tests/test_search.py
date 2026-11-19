# --search 옵션 테스트: 본문 검색 함수와 CLI 동작을 검증한다.
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import main  # noqa: E402


def run_cli(*args):
    return subprocess.run(
        [sys.executable, str(ROOT / "main.py"), *args],
        capture_output=True, text=True, encoding="utf-8", timeout=30,
        env={**os.environ, "PYTHONUTF8": "1"},
    )


def test_본문에_포함된_항목만_반환():
    result = main.search_quotes("성공")
    assert result and all("성공" in q["text"] for q in result)


def test_작성자만_일치하면_제외(monkeypatch):
    monkeypatch.setattr(main, "load_quotes", lambda: [{"text": "시작이 반이다.", "author": "노자"}])
    assert main.search_quotes("노자") == []


def test_앞뒤_공백_키워드는_제거후_검색():
    assert main.search_quotes(" 성공 ") == main.search_quotes("성공") != []


def test_대소문자_무시(monkeypatch):
    monkeypatch.setattr(main, "load_quotes", lambda: [{"text": "Hello World", "author": "a"}])
    assert len(main.search_quotes("hello")) == 1


def test_cli_출력():
    r = run_cli("--search", "성공")
    assert r.returncode == 0
    lines = r.stdout.strip().splitlines()
    assert lines and all("성공" in l for l in lines)


def test_cli_결과없음():
    r = run_cli("--search", "존재하지않는키워드xyz")
    assert r.returncode == 0 and r.stdout == ""


def test_cli_빈_키워드는_오류():
    assert run_cli("--search", "  ").returncode == 2


def run_cli_with_data(tmp_path, content):
    # main.py를 임시 폴더로 복사하고, 그 옆에 원하는 quotes.json을 두어 실행한다.
    import shutil
    shutil.copy(ROOT / "main.py", tmp_path / "main.py")
    if content is not None:
        (tmp_path / "quotes.json").write_text(content, encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(tmp_path / "main.py"), "--search", "a"],
        capture_output=True, text=True, encoding="utf-8", timeout=30,
        env={**os.environ, "PYTHONUTF8": "1"},
    )


def test_cli_파일없음은_오류메시지(tmp_path):
    r = run_cli_with_data(tmp_path, None)
    assert r.returncode == 1 and "quotes.json" in r.stderr and "Traceback" not in r.stderr


def test_cli_깨진_JSON은_오류메시지(tmp_path):
    r = run_cli_with_data(tmp_path, "{깨짐")
    assert r.returncode == 1 and "Traceback" not in r.stderr


def test_cli_키누락은_오류메시지(tmp_path):
    r = run_cli_with_data(tmp_path, '[{"author": "x"}]')
    assert r.returncode == 1 and "Traceback" not in r.stderr
