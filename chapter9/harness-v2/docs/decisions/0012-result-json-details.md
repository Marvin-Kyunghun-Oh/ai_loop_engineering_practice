# 0012. 결과 JSON 처리 세부: 형식 오류는 즉시 HALT, 토큰은 modelUsage 합산, 설정의 모르는 키는 거부

- 상태: 확정
- 날짜: 2026-11-24
- 보완 대상: [0003](0003-tech-stack.md), [0007](0007-cost-limit.md)

## 맥락
구현 2단계(`ResultParser`)에서 문서끼리 어긋나거나 문서에 없는 점이 세 가지 나왔다.

1. **필수 필드 누락**
   - 0007: 필수 필드가 없으면 예외로 `HALT`한다.
   - DESIGN 5.1: `ERROR`로 처리한다. 그러면 연속 2회가 되어야 `HALT`한다.
2. **예산 상한에 걸렸을 때의 토큰**
   - 실제 샘플(`error-max-budget-usd.json`)에서 `usage`가 전부 0이었다. 비용은 `$0.00196`이다.
   - 실제 토큰은 `modelUsage.{모델}`에만 있다.
3. **설정의 모르는 키**
   - 0003 영향: "Jackson은 모르는 키를 무시한다"
   - DESIGN 3절: `harness.yml`의 모르는 키는 시작을 거부한다

## 결정
1. **결과 JSON의 형식 오류는 즉시 `HALT`한다.**
   - 새 분류 `Outcome.INVALID_RESULT`를 둔다.
   - 대상: JSON 객체는 받았지만 필수 필드가 없거나, `type`이 `result`가 아닌 경우.
   - 이유: 필드 이름이 바뀐 것이면 다시 돌려도 똑같이 실패하고, 그사이 비용은 집계되지 않는다.
   - 출력이 비었거나 JSON이 아닌 경우는 지금처럼 `ERROR`다. 프로세스 비정상 종료처럼 일시적일 수 있다. 연속 `max_consecutive_errors`회면 `HALT`한다.
2. **토큰은 `modelUsage`의 모델별 값을 합산한다.**
   - 합산 대상은 `inputTokens`, `cacheCreationInputTokens`, `cacheReadInputTokens`, `outputTokens`다.
   - `modelUsage`가 없거나 비어 있으면 `usage`를 쓴다.
   - 성공 샘플과 턴 상한 샘플에서는 두 값이 같았다.
   - 비용(`total_cost_usd`)은 원래 모든 모델의 합이다. 토큰도 같은 범위로 맞추는 효과가 있다.
3. **모르는 키는 대상별로 다르게 처리한다.**
   - 결과 JSON은 무시한다. CLI가 버전마다 필드를 더하기 때문이다.
   - `harness.yml`은 거부한다. 오타가 조용히 기본값으로 바뀌는 사고를 막기 위해서다. 0003 영향의 문장은 결과 JSON에 대한 것으로 읽는다.

## 검토한 대안
- **형식 오류도 `ERROR`로 처리**: 같은 실패를 한 번 더 겪고 그 비용도 기록되지 않는다.
- **토큰은 `usage`를 그대로 사용**: 예산 상한에 걸린 실행의 토큰이 0으로 기록되어 분석이 틀어진다.

## 영향
- `DESIGN.md` 5.1의 판정 표와 6절 메인 루프에 `INVALID_RESULT`를 추가했다.
- `IMPROVEMENTS.md` A2 필드 표의 토큰 출처를 고쳤다.
