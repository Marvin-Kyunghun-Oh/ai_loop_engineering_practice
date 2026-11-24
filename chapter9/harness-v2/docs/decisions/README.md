# 의사결정 기록

harness-v2를 설계하며 사용자와 합의한 결정을 남긴다. 한 파일에 결정 하나를 적는다.

- 형식: 상태 / 날짜 / 맥락 / 결정 / 검토한 대안 / 영향
- 결정을 바꾸면 기존 파일을 지우지 않는다. 상태를 `대체됨(→ 새 번호)`으로 바꾸고 새 파일을 만든다.
- v1 하네스의 `docs/decisions/`(planner·evaluator의 블라인드 합의용 `{주제}.md`)와는 다른 용도다. 이곳은 **사람이 내린 설계 결정**의 기록이다.

| 번호 | 제목 | 상태 | 날짜 |
|---|---|---|---|
| [0001](0001-stop-rss-wiki.md) | rss-wiki 개발을 M2 중간에서 중단 | 확정 | 2026-11-24 |
| [0002](0002-rewrite-harness-in-java.md) | 하네스를 Java로 다시 작성(v2) | 확정 | 2026-11-24 |
| [0003](0003-tech-stack.md) | 기술 스택: Gradle, JDK 21, Jackson, YAML | 확정 | 2026-11-24 |
| [0004](0004-no-target-project-yet.md) | 첫 대상 프로젝트는 v2 범위에서 제외 | 확정 | 2026-11-24 |
| [0005](0005-document-archive.md) | 문서 아카이브: 하네스가 작업 지시만 옮기고 결정은 유지 | 확정 | 2026-11-24 |
| [0006](0006-model-defaults.md) | 모델 기본값: planner만 opus | 확정 | 2026-11-24 |
| [0007](0007-cost-limit.md) | 비용 상한: CLI 보고 비용 누적 $38 + 1회 $5 | 확정 | 2026-11-24 |
| [0008](0008-strict-permissions.md) | 권한: 역할별 Bash 허용 목록(엄격) | 확정 | 2026-11-24 |
| [0009](0009-harness-writes-journal.md) | JOURNAL은 하네스가 기록 | 확정 | 2026-11-24 |
| [0010](0010-backlog-for-review-memos.md) | REVIEW 메모는 BACKLOG로, 마일스톤 끝에 최대 2개만 처리 | 확정 | 2026-11-24 |
| [0011](0011-smoke-test.md) | 샘플 프로젝트로 실제 `claude` 스모크 테스트 | 확정 | 2026-11-24 |

상세한 근거와 구현 메모는 [`../IMPROVEMENTS.md`](../IMPROVEMENTS.md)에 있다.
