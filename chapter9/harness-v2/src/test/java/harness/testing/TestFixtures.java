package harness.testing;

import harness.claude.AgentResult;
import harness.claude.Outcome;
import harness.claude.TokenUsage;
import java.math.BigDecimal;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.List;

/** 여러 테스트가 함께 쓰는 고정 시계와 AgentResult 생성기. */
public final class TestFixtures {

    /** 2026-11-24T12:26:46+09:00 에 멈춘 시계 */
    public static final Clock FIXED_CLOCK =
            Clock.fixed(Instant.parse("2026-11-24T03:26:46Z"), ZoneOffset.ofHours(9));

    public static final String FIXED_TIME = "2026-11-24T12:26:46+09:00";

    private TestFixtures() {
    }

    public static AgentResult success(String cost, String summary) {
        return new AgentResult(Outcome.SUCCESS, "success", new BigDecimal(cost),
                new TokenUsage(10, 20, 30, 40), 3, 1500, summary, List.of());
    }

    public static AgentResult budgetLimit(String cost) {
        String message = "Reached maximum budget ($5)";
        return new AgentResult(Outcome.BUDGET_LIMIT, "error_max_budget_usd", new BigDecimal(cost),
                TokenUsage.ZERO, 20, 90000, message, List.of(message));
    }

    public static AgentResult turnLimit(String cost) {
        String message = "Reached maximum number of turns (40)";
        return new AgentResult(Outcome.TURN_LIMIT, "error_max_turns", new BigDecimal(cost),
                TokenUsage.ZERO, 40, 90000, message, List.of(message));
    }

    public static AgentResult error(String cost, String message) {
        return new AgentResult(Outcome.ERROR, "error_during_execution", new BigDecimal(cost),
                TokenUsage.ZERO, 1, 100, message, List.of(message));
    }

    public static AgentResult invalidResult() {
        return new AgentResult(Outcome.INVALID_RESULT, null, null, TokenUsage.ZERO, 0, 0,
                "결과 JSON 필수 필드 누락: total_cost_usd", List.of());
    }
}
