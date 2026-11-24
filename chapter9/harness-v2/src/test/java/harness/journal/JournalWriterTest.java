package harness.journal;

import static harness.testing.TestFixtures.FIXED_CLOCK;
import static harness.testing.TestFixtures.FIXED_TIME;
import static org.junit.jupiter.api.Assertions.assertEquals;
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

class JournalWriterTest {

    @TempDir
    Path dir;

    @Test
    @DisplayName("result가 있으면 그 요약을 쓴다 (4.6)")
    void successLine() {
        String line = JournalWriter.formatLine(FIXED_TIME, 12, Role.GENERATOR,
                TestFixtures.success("1.2", "T7b 완료 (258 passed)"), null);

        assertEquals("- " + FIXED_TIME + " [c12] generator: T7b 완료 (258 passed) · $1.20 · success", line);
    }

    @Test
    @DisplayName("evaluator는 판정을 끝에 덧붙인다")
    void evaluatorVerdict() {
        String line = JournalWriter.formatLine(FIXED_TIME, 12, Role.EVALUATOR,
                TestFixtures.success("0.8", "T7b PASS 12/12"), "PASS 12/12");

        assertTrue(line.endsWith(" · $0.80 · success · PASS 12/12"), line);
    }

    @Test
    @DisplayName("result가 null이면 errors[0]이 요약이다 (ResultParser가 채운다)")
    void errorLine() {
        String line = JournalWriter.formatLine(FIXED_TIME, 13, Role.GENERATOR,
                TestFixtures.budgetLimit("5.31"), null);

        assertEquals("- " + FIXED_TIME + " [c13] generator: Reached maximum budget ($5) · $5.31 · error_max_budget_usd",
                line);
    }

    @Test
    @DisplayName("비용을 모르면 $?, subtype이 없으면 Outcome 이름")
    void unknownCostAndSubtype() {
        String line = JournalWriter.formatLine(FIXED_TIME, 4, Role.PLANNER,
                AgentResult.failure(Outcome.TIMEOUT, "30분 초과로 종료"), null);

        assertTrue(line.endsWith("planner: 30분 초과로 종료 · $? · timeout"), line);
    }

    @Test
    @DisplayName("200자를 넘으면 자른다")
    void truncatesLongSummary() {
        String summary = JournalWriter.summary("가".repeat(250));

        assertEquals(201, summary.length());
        assertTrue(summary.endsWith("…"));
    }

    @Test
    @DisplayName("요약이 여러 줄이거나 비어 있어도 한 줄로 쓴다")
    void oneLine() {
        assertEquals("첫 줄 둘째 줄", JournalWriter.summary("첫 줄\n  둘째 줄\n"));
        assertEquals("(요약 없음)", JournalWriter.summary(""));
    }

    @Test
    @DisplayName("금액은 센트 단위로 반올림한다")
    void costFormat() {
        assertEquals("$0.00", JournalWriter.cost(new BigDecimal("0.00271608")));
        assertEquals("$0.01", JournalWriter.cost(new BigDecimal("0.005")));
        assertEquals("$12.00", JournalWriter.cost(new BigDecimal("12")));
    }

    @Test
    @DisplayName("파일에 줄을 이어 붙인다. 기존 내용이 줄바꿈 없이 끝나도 줄이 붙지 않는다")
    void appendsToFile() throws IOException {
        Path journal = dir.resolve("JOURNAL.md");
        Files.writeString(journal, "# JOURNAL");
        JournalWriter writer = new JournalWriter(journal, FIXED_CLOCK);

        writer.append(1, Role.PLANNER, TestFixtures.success("0.5", "T1 선정"), null);
        writer.append(1, Role.GENERATOR, TestFixtures.success("1", "T1 완료"), null);

        List<String> lines = Files.readAllLines(journal);
        assertEquals(3, lines.size());
        assertEquals("# JOURNAL", lines.get(0));
        assertEquals("- " + FIXED_TIME + " [c1] planner: T1 선정 · $0.50 · success", lines.get(1));
    }
}
