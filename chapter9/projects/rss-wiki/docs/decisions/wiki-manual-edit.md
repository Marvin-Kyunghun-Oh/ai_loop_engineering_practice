# 결정 U5: 사용자가 위키 파일을 직접 고쳤을 때

## 맥락
PRD 4.6/5: 글별 Markdown 파일이 요약의 정본이며 Obsidian 등에서 열어 편집할 수 있다. 인덱스 파일(`index.md`, `feeds/`, `tags/`)은 실행마다 DB 기준으로 전체 재생성한다. v1에서 같은 글을 다시 요약하는 경로는 실패 글의 수동 재시도뿐이다.

## 후보
- A: 재요약하면 글 파일을 덮어씀
- B: frontmatter에 해시를 두고 사용자 수정을 감지하면 덮어쓰지 않음
- C: 요약 영역만 마커로 구분해 그 영역만 갱신

## 기록 방법
`wiki-manual-edit.planner.md` / `wiki-manual-edit.evaluator.md` 첫 줄에 `선택: A`처럼 라벨 문자 하나만 쓴다.

합의: A (시도 1회)
