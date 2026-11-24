# 결정 U8: Python 3.15 의존성 호환성

## 맥락
PRD 2: 런타임은 Python 3.15, uv로 관리한다. 현재 `pyproject.toml`은 `requires-python >=3.15`, `.python-version`은 `3.15`, 로컬 venv도 CPython 3.15다. 앞으로 FastAPI(pydantic-core), Jinja2, feedparser, trafilatura(lxml) 등을 추가할 예정이며, 이 중 네이티브 확장 패키지의 3.15 휠 제공 여부가 걸린다.

## 후보
- A: Python 3.15 유지
- B: Python 3.13 또는 3.14로 낮춤

## 기록 방법
`python-version.planner.md` / `python-version.evaluator.md` 첫 줄에 `선택: A`처럼 라벨 문자 하나만 쓴다.

합의: A (시도 1회)
