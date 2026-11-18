# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 개발 규칙

- 내가 `(프롬프트)`라는 키워드를 넣으면, 해당 프롬프트를 있는 그대로 `/prompt/seq_{어떤요청인지 요약한 제목}.md`에 보관한다.
  - 제목은 에이전트가 요약하되, 문장이 아닌 `단어 + '_'`의 조합으로 생성한다.(영어로)
  - seq는 1부터 채번된 문서번호

## 프로젝트 개요

개인 할 일 관리용 작은 FastAPI + SQLAlchemy + SQLite 웹 API. 책 3장 스킬 실습용 예제 저장소이며, 기본 브랜치는 `main`. Python >=3.14, 패키지 관리는 uv.

## 명령어

```
uv sync                                   # 의존성 설치
uv run python scripts/seed.py             # 데모 할 일 100개 생성 (task_keeper.db)
uv run uvicorn app.main:app --reload      # 서버 실행 (docs: /docs)
SQLALCHEMY_ECHO=1 uv run uvicorn app.main:app   # 실행되는 SQL 출력 (N+1 확인용)
uv run pytest                             # 전체 테스트
uv run pytest tests/test_smoke.py::<test_name>  # 단일 테스트
```

린터/포매터 설정은 없다.

## 구조

- `app/main.py` → 엔드포인트, `app/services/task_service.py` → 쿼리/비즈니스 로직, `app/models.py` → `Task`↔`Tag` 다대다, `app/schemas.py` → 요청/응답 스키마. 엔드포인트는 `app/database.py`의 `get_db` 의존성으로 세션을 받는다.
- 테스트(`tests/conftest.py`)는 `get_db`를 `dependency_overrides`로 교체해 테스트마다 메모리 SQLite(`StaticPool`)를 사용한다. 실제 DB 파일에 의존하지 않는다.
- 의도적으로 남겨둔 버그: `list_tasks()`의 태그 N+1 조회. 수정 방향은 `selectinload(Task.tags)` 적용(README 참고). 이 수정이 3.8 실습(이슈 → 커밋 → PR → 리뷰 → 리뷰 반영)의 작업 내용이다.
- `.claude/skills/`에 실습용 프로젝트 스킬이 있다(예: `create-issue`).
