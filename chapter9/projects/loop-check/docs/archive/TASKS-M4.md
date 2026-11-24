# TASKS-M4.md

## M4. 최종 검증

- [x] T7. 전체 테스트 실행과 PRD 대조
  - 내용
    - PRD의 제약(표준 라이브러리만 사용, 패키지 구성, 테스트 실행 명령)을 확인한다.
  - acceptance
    - `python3 -m unittest discover -s tests -t .` 가 통과한다.
    - PRD 1번의 정상 예 5개와 2번의 오류 8종이 모두 테스트로 검증되어 있다.
  - touch: `src/durations.py`, `tests/test_durations.py`
