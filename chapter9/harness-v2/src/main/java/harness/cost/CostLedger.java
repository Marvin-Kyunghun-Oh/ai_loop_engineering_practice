package harness.cost;

import harness.claude.AgentResult;
import harness.policy.Role;
import harness.state.TextFiles;
import harness.state.Timestamps;
import java.math.BigDecimal;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Clock;
import java.util.List;

/**
 * 누적 비용 장부 (0007, DESIGN 5.4).
 *
 * <ul>
 *   <li>시작할 때 {@code USAGE.csv}의 {@code cost_usd} 합으로 누적 비용을 복원한다.</li>
 *   <li>에이전트 실행 전에 {@link #canAfford}로 "누적 + 1회 상한 &lt;= 누적 상한"을 검사한다.</li>
 *   <li>실행 후 {@link #record}로 한 줄을 추가하고 누적에 더한다. 오류로 끝난 실행도 기록한다.</li>
 * </ul>
 * 금액은 double 누적 오차를 피하려고 {@link BigDecimal}로 다룬다.
 */
public final class CostLedger {

    private final Path csv;
    private final BigDecimal maxTotalUsd;
    private final Clock clock;
    private BigDecimal total;

    private CostLedger(Path csv, BigDecimal maxTotalUsd, Clock clock, BigDecimal total) {
        this.csv = csv;
        this.maxTotalUsd = maxTotalUsd;
        this.clock = clock;
        this.total = total;
    }

    /** {@code USAGE.csv}에서 누적 비용을 복원한다. 파일이 없으면 0에서 시작한다. */
    public static CostLedger load(Path csv, BigDecimal maxTotalUsd, Clock clock) {
        return new CostLedger(csv, maxTotalUsd, clock, sumCost(csv));
    }

    /** 다음 실행이 1회 상한까지 써도 누적 상한 안인가. 같으면 허용한다. */
    public boolean canAfford(BigDecimal maxAgentUsd) {
        return total.add(maxAgentUsd).compareTo(maxTotalUsd) <= 0;
    }

    /**
     * 실행 결과를 USAGE.csv에 한 줄 추가하고 누적에 더한다.
     * 비용을 모르면(결과 JSON 없음, 타임아웃) 빈 칸으로 쓰고 누적에는 더하지 않는다.
     */
    public void record(int cycle, Role role, String model, AgentResult result) {
        if (!Files.exists(csv)) {
            TextFiles.appendLine(csv, UsageRecord.CSV_HEADER);
        }
        UsageRecord record = UsageRecord.of(Timestamps.now(clock), cycle, role, model, result);
        TextFiles.appendLine(csv, record.toCsvLine());
        if (result.costKnown()) {
            total = total.add(result.costUsd());
        }
    }

    public BigDecimal total() {
        return total;
    }

    public BigDecimal maxTotalUsd() {
        return maxTotalUsd;
    }

    /**
     * 형식이 틀린 줄은 건너뛰지 않고 예외를 던진다.
     * 건너뛰면 누적 비용이 실제보다 작게 복원되어 상한이 늦게 걸린다.
     */
    private static BigDecimal sumCost(Path csv) {
        if (!Files.exists(csv)) {
            return BigDecimal.ZERO;
        }
        List<String> lines = TextFiles.read(csv).lines().toList();
        if (lines.isEmpty()) {
            return BigDecimal.ZERO;
        }
        if (!lines.getFirst().strip().equals(UsageRecord.CSV_HEADER)) {
            throw new IllegalStateException("USAGE.csv 머리줄이 다르다: " + csv
                    + "\n  기대: " + UsageRecord.CSV_HEADER + "\n  실제: " + lines.getFirst());
        }

        BigDecimal sum = BigDecimal.ZERO;
        for (int i = 1; i < lines.size(); i++) {
            String line = lines.get(i).strip();
            if (line.isEmpty()) {
                continue;
            }
            String[] columns = line.split(",", -1);
            int lineNumber = i + 1;
            if (columns.length != UsageRecord.COLUMN_COUNT) {
                throw new IllegalStateException("USAGE.csv " + lineNumber + "번째 줄의 칸 수가 "
                        + columns.length + "개다 (기대 " + UsageRecord.COLUMN_COUNT + "개): " + csv);
            }
            String cost = columns[UsageRecord.COST_COLUMN].strip();
            if (cost.isEmpty()) {
                continue;   // 비용을 모르는 실행
            }
            try {
                sum = sum.add(new BigDecimal(cost));
            } catch (NumberFormatException e) {
                throw new IllegalStateException("USAGE.csv " + lineNumber + "번째 줄의 cost_usd를 읽을 수 없다: \""
                        + cost + "\" (" + csv + ")");
            }
        }
        return sum;
    }
}
