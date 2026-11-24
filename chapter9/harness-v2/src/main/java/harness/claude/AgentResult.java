package harness.claude;

import java.math.BigDecimal;
import java.util.List;

/**
 * 에이전트 1회 실행 결과 (DESIGN 5.1).
 *
 * @param outcome    하네스가 다음 행동을 정하는 분류
 * @param subtype    결과 JSON의 {@code subtype} 원문. 모르면 null
 * @param costUsd    CLI가 보고한 비용. <b>모르면 null</b>이다. 0으로 채우지 않는다 (0007의 필드 누락 처리)
 * @param usage      토큰 4종. 모르면 {@link TokenUsage#ZERO}
 * @param numTurns   턴 수. 모르면 0
 * @param durationMs 실행 시간(ms). 모르면 0
 * @param summary    JOURNAL용 한 줄. {@code result}의 마지막 내용 있는 줄, 없으면 {@code errors[0]}, 둘 다 없으면 빈 문자열.
 *                   200자 자르기는 JournalWriter가 한다
 * @param errors     결과 JSON의 {@code errors}. 없으면 빈 목록
 */
public record AgentResult(
        Outcome outcome,
        String subtype,
        BigDecimal costUsd,
        TokenUsage usage,
        int numTurns,
        long durationMs,
        String summary,
        List<String> errors) {

    public AgentResult {
        errors = List.copyOf(errors);
    }

    /**
     * 결과 JSON을 쓸 수 없을 때(없음, 파싱 실패, 타임아웃)의 결과.
     * 비용을 알 수 없으므로 {@code costUsd}는 null이다.
     */
    public static AgentResult failure(Outcome outcome, String message) {
        return new AgentResult(outcome, null, null, TokenUsage.ZERO, 0, 0, message, List.of());
    }

    /** 비용을 아는지. false면 누적 비용에 더할 수 없다. */
    public boolean costKnown() {
        return costUsd != null;
    }
}
