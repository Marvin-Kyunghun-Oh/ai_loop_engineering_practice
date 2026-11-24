package harness.claude;

/**
 * 에이전트 1회 실행의 결과 분류 (DESIGN 5.1, IMPROVEMENTS B1).
 *
 * <p>하네스는 이 값으로 다음 행동을 정한다. 종료 코드는 쓰지 않는다.
 * 상한 도달과 오류가 모두 종료 코드 1이기 때문이다.
 */
public enum Outcome {

    /** 정상 종료. 다음 역할로 넘어간다. */
    SUCCESS,

    /** {@code --max-budget-usd}에 걸려 멈춤. 이 사이클을 중단하고 다음 사이클로 넘어간다. */
    BUDGET_LIMIT,

    /** {@code --max-turns}에 걸려 멈춤. BUDGET_LIMIT과 같게 처리한다. */
    TURN_LIMIT,

    /**
     * 결과 JSON 객체는 받았지만 형식이 예상과 다름(필수 필드 누락, type이 result가 아님).
     * 필드 이름이 바뀐 것이면 다시 돌려도 같으므로 즉시 HALT한다 (0012).
     */
    INVALID_RESULT,

    /** 실행 오류, 결과 JSON 없음·파싱 실패. 일시적일 수 있으므로 연속되면 HALT한다. */
    ERROR,

    /** 하네스가 시간 초과로 프로세스를 끝냄. ERROR와 같게 처리한다. Runner가 직접 만든다. */
    TIMEOUT
}
