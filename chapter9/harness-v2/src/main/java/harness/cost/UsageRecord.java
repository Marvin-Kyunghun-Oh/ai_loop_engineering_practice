package harness.cost;

import harness.claude.AgentResult;
import harness.claude.TokenUsage;
import harness.policy.Role;
import java.math.BigDecimal;
import java.util.Locale;

/**
 * {@code docs/USAGE.csv}의 한 줄 (DESIGN 4.5).
 *
 * @param subtype 결과 JSON의 {@code subtype}. 결과 JSON이 없으면 Outcome 이름(예: {@code timeout})
 * @param costUsd 모르면 null. CSV에는 빈 칸으로 쓴다
 */
public record UsageRecord(
        String timestamp,
        int cycle,
        Role role,
        String model,
        String subtype,
        BigDecimal costUsd,
        TokenUsage usage,
        int turns,
        long durationMs) {

    public static final String CSV_HEADER =
            "timestamp,cycle,role,model,subtype,cost_usd,input,cache_creation,cache_read,output,turns,duration_ms";

    public static final int COLUMN_COUNT = 12;
    public static final int CYCLE_COLUMN = 1;
    public static final int ROLE_COLUMN = 2;
    public static final int SUBTYPE_COLUMN = 4;
    public static final int COST_COLUMN = 5;

    public static UsageRecord of(String timestamp, int cycle, Role role, String model, AgentResult result) {
        String subtype = result.subtype() != null
                ? result.subtype()
                : result.outcome().name().toLowerCase(Locale.ROOT);
        return new UsageRecord(timestamp, cycle, role, model, subtype, result.costUsd(),
                result.usage(), result.numTurns(), result.durationMs());
    }

    public String toCsvLine() {
        return String.join(",",
                timestamp,
                Integer.toString(cycle),
                role.id(),
                model,
                subtype,
                costUsd == null ? "" : costUsd.toPlainString(),
                Long.toString(usage.input()),
                Long.toString(usage.cacheCreation()),
                Long.toString(usage.cacheRead()),
                Long.toString(usage.output()),
                Integer.toString(turns),
                Long.toString(durationMs));
    }
}
