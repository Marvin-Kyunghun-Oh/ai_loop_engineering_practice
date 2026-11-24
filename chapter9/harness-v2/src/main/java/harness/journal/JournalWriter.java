package harness.journal;

import harness.claude.AgentResult;
import harness.policy.Role;
import harness.state.TextFiles;
import harness.state.Timestamps;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.nio.file.Path;
import java.time.Clock;
import java.util.Locale;

/**
 * 에이전트 실행마다 {@code docs/JOURNAL.md}에 한 줄을 쓴다 (0009, DESIGN 4.6).
 *
 * <pre>
 * - 2026-11-24T12:26:46+09:00 [c12] generator: T7b 완료 (258 passed) · $1.20 · success
 * - 2026-11-24T12:29:10+09:00 [c12] evaluator: T7b PASS 12/12 · $0.80 · success · PASS 12/12
 * </pre>
 */
public final class JournalWriter {

    static final int MAX_SUMMARY_LENGTH = 200;
    private static final String SEPARATOR = " · ";

    private final Path journal;
    private final Clock clock;

    public JournalWriter(Path journal, Clock clock) {
        this.journal = journal;
        this.clock = clock;
    }

    /** @param verdict REVIEW의 {@code 판정:} 값(예: {@code PASS 12/12}). evaluator가 아니거나 모르면 null */
    public void append(int cycle, Role role, AgentResult result, String verdict) {
        TextFiles.appendLine(journal, formatLine(Timestamps.now(clock), cycle, role, result, verdict));
    }

    static String formatLine(String timestamp, int cycle, Role role, AgentResult result, String verdict) {
        StringBuilder line = new StringBuilder()
                .append("- ").append(timestamp)
                .append(" [c").append(cycle).append("] ")
                .append(role.id()).append(": ")
                .append(summary(result.summary()))
                .append(SEPARATOR).append(cost(result.costUsd()))
                .append(SEPARATOR).append(subtype(result));
        if (verdict != null && !verdict.isBlank()) {
            line.append(SEPARATOR).append(verdict.strip());
        }
        return line.toString();
    }

    /** 한 줄로 만들고 200자를 넘으면 자른다. 전체 내용은 .harness/logs/의 원본에 있다. */
    static String summary(String summary) {
        if (summary == null || summary.isBlank()) {
            return "(요약 없음)";
        }
        String oneLine = summary.strip().replaceAll("\\s*\\R\\s*", " ");
        if (oneLine.length() <= MAX_SUMMARY_LENGTH) {
            return oneLine;
        }
        return oneLine.substring(0, MAX_SUMMARY_LENGTH) + "…";
    }

    /** 사람이 읽는 금액. 센트 단위로 반올림한다. 정확한 값은 USAGE.csv에 있다. */
    static String cost(BigDecimal costUsd) {
        if (costUsd == null) {
            return "$?";
        }
        return "$" + costUsd.setScale(2, RoundingMode.HALF_UP).toPlainString();
    }

    private static String subtype(AgentResult result) {
        return result.subtype() != null
                ? result.subtype()
                : result.outcome().name().toLowerCase(Locale.ROOT);
    }
}
