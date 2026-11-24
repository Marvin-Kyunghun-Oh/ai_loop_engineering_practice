# 0006. 모델 기본값: planner만 opus

- 상태: 확정
- 날짜: 2026-11-24

## 맥락
- v1(`run.py:37-38`)은 planner와 evaluator의 기본값이 opus였다. 한 사이클 3회 호출 중 2회가 가장 비싼 모델이었고, 둘 다 매번 큰 문서를 읽었다.

## 결정

| 역할 | v1 | v2 기본값 |
|---|---|---|
| planner | opus | **opus** (계획·항목 선정·종료 판정. 판단이 가장 많은 역할) |
| generator | sonnet | sonnet |
| evaluator | opus | **sonnet** |

- 역할별 모델은 `harness.yml`에서 바꿀 수 있다.
- evaluator 설정에는 다음 주석을 남긴다.
  ```yaml
  models:
    planner: opus
    generator: sonnet
    # 테스트 실행·채점 역할. 비용 절감을 위해 sonnet으로 내렸다.
    # 꼼꼼한 검수가 필요하다면 opus로 변경하는 것을 추천한다.
    # (예: 보안·데이터 무결성이 중요한 프로젝트, sonnet 평가에서 놓친 결함이 반복될 때)
    evaluator: sonnet
  ```

## 검토한 대안
- **전부 sonnet**: 가장 싸지만 계획·종료 판정의 품질이 떨어질 위험이 있다.
- **v1 그대로(planner·evaluator opus)**: 품질은 좋지만 비용 문제의 주요 원인이다.
- **결정 합의가 있는 사이클만 opus로 올림**: 동적 전환은 구현이 복잡해져 보류했다.

## 영향
- evaluator를 sonnet으로 내린 영향은 두 가지로 확인한다. 하나는 비용 기록(0007)과 REVIEW 점수다. 다른 하나는 앞 사이클에서 PASS였던 항목이 나중에 FAIL이나 회귀로 드러나는지다. 놓친 결함이 늘면 opus로 되돌린다.
