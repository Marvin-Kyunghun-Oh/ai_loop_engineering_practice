## 프롬프트

워크플로를 사용하여 데이터 저장을 JSON이 아닌 SQLite로 바꿔줘.

## 답변

워크플로(구현 1 → 검토·테스트 병렬 2, 에이전트 3개)로 진행했다.

1. `main.py`: 저장소를 `sqlite3` 기반 `quotes.db`로 전환했다(`QUOTES_DB` 환경변수로 경로 변경 가능). 빈 DB일 때 `quotes.json`을 시드로 1회 가져오고, SQL은 `?` 바인딩만 쓴다. 검색은 casefold 의미를 유지하려고 파이썬에서 거른다. 입력 검증과 CLI 종료 코드는 유지했다.
2. 테스트: `conftest.py`, `test_sqlite.py`(마이그레이션, 인젝션, 리소스 형식 등)를 추가해 전체 28개가 통과했다. `--search` 실행도 정상(종료 코드 0)이다.
3. `.gitignore`(`quotes.db`), README, CLAUDE.md를 갱신했다.

코드 검토 결과(미반영): 시드 마이그레이션 동시 실행 경쟁 조건, 빈 DB의 `get_random_quote` `IndexError`, 시드가 입력 검증을 우회, 비UTF-8 시드의 `UnicodeDecodeError`, SQLite 저널 `.gitignore` 누락, `CLAUDE.md`/README의 chapter4 표기. 문서와 동작이 반대로 적힌 README 2곳만 바로 고쳤다.

## 결정 사항과 처리 결과

| 결정 | 처리 |
|---|---|
| 워크플로로 진행 | 구현 1 + 검토·테스트 병렬 2로 실행 |
| JSON → SQLite 전환 | 구현 완료, 테스트 28개 통과 |
| (세부 설계는 위임) | `quotes.json`은 시드로 유지, `quotes.db`는 gitignore |
| 검토 지적 처리 | README 모순 2건만 반영, 나머지는 사용자 결정 대기 |
