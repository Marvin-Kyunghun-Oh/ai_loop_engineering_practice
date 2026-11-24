package harness.cost;

import static harness.testing.TestFixtures.FIXED_CLOCK;
import static harness.testing.TestFixtures.FIXED_TIME;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import harness.claude.AgentResult;
import harness.claude.Outcome;
import harness.policy.Role;
import harness.testing.TestFixtures;
import java.io.IOException;
import java.math.BigDecimal;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class CostLedgerTest {

    private static final BigDecimal MAX_TOTAL = new BigDecimal("38");
    private static final BigDecimal MAX_AGENT = new BigDecimal("5");

    @TempDir
    Path dir;

    Path csv() {
        return dir.resolve("USAGE.csv");
    }

    @Test
    @DisplayName("파일이 없으면 누적 0에서 시작")
    void startsFromZero() {
        CostLedger ledger = CostLedger.load(csv(), MAX_TOTAL, FIXED_CLOCK);

        assertEquals(0, BigDecimal.ZERO.compareTo(ledger.total()));
        assertTrue(ledger.canAfford(MAX_AGENT));
    }

    @Test
    @DisplayName("기록하면 머리줄과 함께 4.5 형식으로 쓴다")
    void recordWritesCsv() throws IOException {
        CostLedger ledger = CostLedger.load(csv(), MAX_TOTAL, FIXED_CLOCK);

        ledger.record(12, Role.GENERATOR, "sonnet", TestFixtures.success("1.20", "T7b 완료"));

        assertEquals(List.of(
                UsageRecord.CSV_HEADER,
                FIXED_TIME + ",12,generator,sonnet,success,1.20,10,20,30,40,3,1500"),
                Files.readAllLines(csv()));
        assertEquals(new BigDecimal("1.20"), ledger.total());
    }

    @Test
    @DisplayName("기존 CSV에서 누적을 복원하고, 이어서 기록한다")
    void restoresTotalFromCsv() throws IOException {
        CostLedger first = CostLedger.load(csv(), MAX_TOTAL, FIXED_CLOCK);
        first.record(1, Role.PLANNER, "opus", TestFixtures.success("0.10", "계획"));
        first.record(1, Role.GENERATOR, "sonnet", TestFixtures.success("0.20", "구현"));

        CostLedger restored = CostLedger.load(csv(), MAX_TOTAL, FIXED_CLOCK);
        restored.record(1, Role.EVALUATOR, "sonnet", TestFixtures.success("0.30", "평가"));

        // double로 더하면 0.6000000000000001이 된다
        assertEquals(new BigDecimal("0.60"), restored.total());
        assertEquals(4, Files.readAllLines(csv()).size(), "머리줄은 한 번만 쓴다");
    }

    @Test
    @DisplayName("오류로 끝난 실행도 비용을 기록한다")
    void recordsErrorRuns() {
        CostLedger ledger = CostLedger.load(csv(), MAX_TOTAL, FIXED_CLOCK);

        ledger.record(3, Role.GENERATOR, "sonnet", TestFixtures.budgetLimit("5.31"));

        assertEquals(new BigDecimal("5.31"), ledger.total());
    }

    @Test
    @DisplayName("비용을 모르면 빈 칸으로 쓰고 누적에 더하지 않는다")
    void unknownCost() throws IOException {
        CostLedger ledger = CostLedger.load(csv(), MAX_TOTAL, FIXED_CLOCK);

        ledger.record(3, Role.GENERATOR, "sonnet", AgentResult.failure(Outcome.TIMEOUT, "30분 초과"));

        assertEquals(0, BigDecimal.ZERO.compareTo(ledger.total()));
        assertEquals(FIXED_TIME + ",3,generator,sonnet,timeout,,0,0,0,0,0,0", Files.readAllLines(csv()).get(1));
        assertEquals(0, BigDecimal.ZERO.compareTo(CostLedger.load(csv(), MAX_TOTAL, FIXED_CLOCK).total()));
    }

    @Test
    @DisplayName("canAfford 경계: 누적 + 1회 상한이 누적 상한과 같으면 허용, 1센트 넘으면 거부")
    void canAffordBoundary() {
        CostLedger ledger = CostLedger.load(csv(), MAX_TOTAL, FIXED_CLOCK);
        ledger.record(1, Role.GENERATOR, "sonnet", TestFixtures.success("33.00", "x"));
        assertTrue(ledger.canAfford(MAX_AGENT), "33 + 5 = 38");

        ledger.record(1, Role.EVALUATOR, "sonnet", TestFixtures.success("0.01", "x"));
        assertFalse(ledger.canAfford(MAX_AGENT), "33.01 + 5 > 38");
    }

    @Test
    @DisplayName("머리줄이 다르면 예외")
    void wrongHeader() throws IOException {
        Files.writeString(csv(), "cycle,agent,cost\n1,planner,0.1\n");

        assertThrows(IllegalStateException.class, () -> CostLedger.load(csv(), MAX_TOTAL, FIXED_CLOCK));
    }

    @Test
    @DisplayName("깨진 줄은 건너뛰지 않고 줄 번호와 함께 예외 (누적이 작게 복원되면 상한이 늦게 걸린다)")
    void brokenLine() throws IOException {
        Files.writeString(csv(), UsageRecord.CSV_HEADER + "\n"
                + FIXED_TIME + ",1,planner,opus,success,abc,0,0,0,0,1,1\n");

        IllegalStateException e = assertThrows(IllegalStateException.class,
                () -> CostLedger.load(csv(), MAX_TOTAL, FIXED_CLOCK));
        assertTrue(e.getMessage().contains("2번째 줄"), e.getMessage());
    }
}
