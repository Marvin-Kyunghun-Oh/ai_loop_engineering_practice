# 결정 U9: 위키 인덱스 재생성 방식

## 맥락
PRD 4.6: `index.md`, `feeds/{feed-slug}.md`, `tags/{tag}.md`는 자동 생성 파일이다. PRD 본문은 "실행이 끝날 때마다 DB를 기준으로 전체를 다시 생성"한다고 적었다. 개인용이라 글 수는 당분간 수백~수천 건 수준이다.

## 후보
- A: 매 실행 끝에 전체 재생성
- B: 이번 실행에서 바뀐 피드/태그의 인덱스만 갱신

## 기록 방법
`index-regeneration.planner.md` / `index-regeneration.evaluator.md` 첫 줄에 `선택: A`처럼 라벨 문자 하나만 쓴다.

합의: A (시도 1회)
