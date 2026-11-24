package harness;

import static harness.testing.TestFixtures.FIXED_CLOCK;
import static harness.testing.TestFixtures.FIXED_TIME;
import static harness.testing.TestFixtures.budgetLimit;
import static harness.testing.TestFixtures.error;
import static harness.testing.TestFixtures.invalidResult;
import static harness.testing.TestFixtures.success;
import static harness.testing.TestFixtures.turnLimit;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import harness.claude.AgentRequest;
import harness.config.ConfigLoader;
import harness.config.HarnessConfig;
import harness.cost.UsageRecord;
import harness.policy.Role;
import harness.state.ProjectFiles;
import harness.state.TextFiles;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.PrintStream;
import java.io.UncheckedIOException;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.List;
import java.util.function.Consumer;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/** 메인 루프를 가짜 실행기로 검증한다 (DESIGN 7절 Harness 행). claude를 부르지 않는다. */
class HarnessTest {

    @TempDir
    Path projectDir;

    ProjectFiles files;
    FakeClaudeRunner runner;
    ByteArrayOutputStream console;

    @BeforeEach
    void setUp() {
        files = new ProjectFiles(projectDir);
        files.createDirectories();
        TextFiles.write(files.prd(), "# PRD\n");
        runner = new FakeClaudeRunner(files);
        console = new ByteArrayOutputStream();
    }

    @Nested
    @DisplayName("정상 흐름")
    class NormalFlow {

        @Test
        @DisplayName("한 사이클을 planner → generator → evaluator 순서로 돌고, 다음 사이클 planner의 DONE으로 끝난다")
        void fullCycleThenDone() {
            runner.expect(Role.PLANNER, writeCurrent("T1"), success("0.50", "T1 선정"))
                    .expect(Role.GENERATOR, success("1.20", "T1 완료 (12 passed)"))
                    .expect(Role.EVALUATOR, success("0.80", "T1 PASS 10/10"))
                    .expect(Role.PLANNER, writeDone(), success("0.30", "모든 항목 완료"));

            int exit = harness(config()).run();

            assertEquals(Harness.EXIT_OK, exit);
            runner.assertAllStepsUsed();
            assertEquals(List.of(Role.PLANNER, Role.GENERATOR, Role.EVALUATOR, Role.PLANNER), runner.calledRoles());
            assertEquals(2, files.readCycleCount());
            assertEquals(List.of(
                    "- " + FIXED_TIME + " [c1] planner: T1 선정 · $0.50 · success",
                    "- " + FIXED_TIME + " [c1] generator: T1 완료 (12 passed) · $1.20 · success",
                    "- " + FIXED_TIME + " [c1] evaluator: T1 PASS 10/10 · $0.80 · success",
                    "- " + FIXED_TIME + " [c2] planner: 모든 항목 완료 · $0.30 · success"),
                    lines(files.journal()));
            assertEquals(5, lines(files.usageCsv()).size(), "머리줄 + 4회");
        }

        @Test
        @DisplayName("역할별 요청: 모델, 도구, 상한, 원본 로그 위치")
        void requestsPerRole() {
            runner.expect(Role.PLANNER, writeCurrent("T1"), success("0.5", "x"))
                    .expect(Role.GENERATOR, success("0.5", "x"))
                    .expect(Role.EVALUATOR, success("0.5", "x"))
                    .expect(Role.PLANNER, writeDone(), success("0.5", "x"));

            harness(config()).run();

            AgentRequest planner = runner.requests().get(0);
            assertEquals("opus", planner.model());
            assertEquals(List.of("Read", "Glob", "Grep", "Edit(docs/**)", "Write(docs/**)"), planner.allowedTools());
            assertEquals(List.of("Bash"), planner.disallowedTools());
            assertFalse(planner.acceptEdits());
            assertEquals(new BigDecimal("5"), planner.maxBudgetUsd());
            assertNull(planner.maxTurns());
            assertEquals(Duration.ofMinutes(30), planner.timeout());
            assertEquals(files.root(), planner.workDir());
            assertEquals(files.logsDir().resolve("c1-planner.json"), planner.rawLogFile());
            assertEquals("prompt:planner:c1", planner.prompt());

            AgentRequest generator = runner.requests().get(1);
            assertEquals("sonnet", generator.model());
            assertTrue(generator.acceptEdits());
            assertEquals(List.of(), generator.disallowedTools());
            assertTrue(generator.allowedTools().contains("Bash(./gradlew test:*)"));
            assertTrue(generator.allowedTools().contains("Edit"));

            AgentRequest evaluator = runner.requests().get(2);
            assertTrue(evaluator.allowedTools().contains("Bash(./gradlew test:*)"));
            assertFalse(evaluator.allowedTools().contains("Bash(./gradlew build:*)"));
            assertFalse(evaluator.allowedTools().contains("Edit"), "evaluator는 docs/ 밖을 고칠 수 없다");

            assertEquals(files.logsDir().resolve("c2-planner.json"), runner.requests().get(3).rawLogFile());
        }

        @Test
        @DisplayName("max_turns를 설정하면 역할별로 넘긴다")
        void maxTurnsPerRole() {
            runner.expect(Role.PLANNER, writeDone(), success("0.5", "x"));

            harness(config("max_turns: null", "max_turns: { planner: 15 }")).run();

            assertEquals(15, runner.requests().get(0).maxTurns());
        }

        @Test
        @DisplayName("이전 실행의 사이클 번호와 누적 비용을 이어받는다")
        void resumesFromPreviousRun() {
            files.saveCycleCount(7);
            TextFiles.write(files.usageCsv(), UsageRecord.CSV_HEADER + "\n"
                    + FIXED_TIME + ",7,evaluator,sonnet,success,30.00,0,0,0,0,1,1\n");
            runner.expect(Role.PLANNER, writeDone(), success("0.5", "x"));

            harness(config()).run();

            assertEquals(8, files.readCycleCount());
            assertTrue(consoleText().contains("누적 비용 $30.00"), consoleText());
        }

        @Test
        @DisplayName("max_iterations에 도달하면 정상 종료")
        void stopsAtMaxIterations() {
            runner.expect(Role.PLANNER, writeCurrent("T1"), success("0.1", "x"))
                    .expect(Role.GENERATOR, success("0.1", "x"))
                    .expect(Role.EVALUATOR, success("0.1", "x"));

            int exit = harness(config("max_iterations: 50", "max_iterations: 1")).run();

            assertEquals(Harness.EXIT_OK, exit);
            runner.assertAllStepsUsed();
            assertEquals(1, files.readCycleCount());
        }
    }

    @Nested
    @DisplayName("에이전트가 남긴 종료 신호")
    class AgentSignals {

        @Test
        @DisplayName("사이클 시작 때 지난 DONE을 지운다")
        void staleDoneIsDeleted() {
            TextFiles.write(files.done(), "");
            runner.expect(Role.PLANNER, writeCurrent("T1"), success("0.1", "x"))
                    .expect(Role.GENERATOR, success("0.1", "x"))
                    .expect(Role.EVALUATOR, success("0.1", "x"));

            harness(config("max_iterations: 50", "max_iterations: 1")).run();

            runner.assertAllStepsUsed();
        }

        @Test
        @DisplayName("planner가 HALT를 남기면 카운터를 저장하고 멈춘다 (v1과 같음)")
        void plannerHalt() {
            runner.expect(Role.PLANNER, f -> TextFiles.write(f.halt(), "PRD가 모호하다"), success("0.5", "x"));

            int exit = harness(config()).run();

            assertEquals(Harness.EXIT_HALT, exit);
            assertEquals(List.of(Role.PLANNER), runner.calledRoles());
            assertEquals(1, files.readCycleCount());
        }

        @Test
        @DisplayName("시작할 때 HALT가 있으면 아무것도 실행하지 않는다")
        void haltBeforeStart() {
            TextFiles.write(files.halt(), "사유: 이전 실행\n");

            int exit = harness(config()).run();

            assertEquals(Harness.EXIT_HALT, exit);
            assertEquals(List.of(), runner.calledRoles());
        }

        @Test
        @DisplayName("PRD가 없으면 실행하지 않는다 (부트스트랩은 10단계)")
        void noPrd() throws IOException {
            Files.delete(files.prd());

            int exit = harness(config()).run();

            assertEquals(Harness.EXIT_HALT, exit);
            assertEquals(List.of(), runner.calledRoles());
        }
    }

    @Nested
    @DisplayName("CURRENT (4.1)")
    class Current {

        @Test
        @DisplayName("planner가 CURRENT를 쓰지 않으면 generator로 넘어가지 않고 HALT")
        void missingCurrent() {
            runner.expect(Role.PLANNER, success("0.5", "x"));

            int exit = harness(config()).run();

            assertEquals(Harness.EXIT_HALT, exit);
            assertEquals(List.of(Role.PLANNER), runner.calledRoles());
            assertTrue(haltText().startsWith("사유: CURRENT 누락\n"), haltText());
            assertEquals(0, files.readCycleCount());
        }

        @Test
        @DisplayName("지난 사이클의 CURRENT는 사이클 시작 때 지운다. 옛 항목으로 generator가 돌지 않는다")
        void staleCurrentIsDeleted() {
            TextFiles.write(files.current(), "T0\n");
            runner.expect(Role.PLANNER, success("0.5", "x"));

            harness(config()).run();

            assertTrue(haltText().startsWith("사유: CURRENT 누락\n"), haltText());
        }

        @Test
        @DisplayName("CURRENT 형식이 틀리면 HALT")
        void invalidCurrent() {
            runner.expect(Role.PLANNER, writeCurrent("T1, T2"), success("0.5", "x"));

            harness(config()).run();

            assertEquals(List.of(Role.PLANNER), runner.calledRoles());
            assertTrue(haltText().startsWith("사유: CURRENT 형식 오류\n"), haltText());
        }
    }

    @Nested
    @DisplayName("비용 상한 (0007)")
    class Budget {

        @Test
        @DisplayName("시작 전 누적 + 1회 상한이 누적 상한을 넘으면 실행하지 않고 HALT")
        void blockedBeforeFirstAgent() {
            TextFiles.write(files.usageCsv(), UsageRecord.CSV_HEADER + "\n"
                    + FIXED_TIME + ",14,evaluator,sonnet,success,34.10,0,0,0,0,1,1\n");

            int exit = harness(config()).run();

            assertEquals(Harness.EXIT_HALT, exit);
            assertEquals(List.of(), runner.calledRoles());
            assertEquals("""
                    사유: 예산 소진
                    상세: 누적 $34.10 + 에이전트 1회 상한 $5.00 > 상한 $38.00
                    사이클: 1 / 역할: planner (실행 전)
                    재개: 이 파일을 지우고 harness.yml의 limits.max_total_usd를 올린다
                    """, haltText());
        }

        @Test
        @DisplayName("사이클 중간에 상한에 닿으면 다음 역할을 실행하지 않는다")
        void blockedMidCycle() {
            TextFiles.write(files.usageCsv(), UsageRecord.CSV_HEADER + "\n"
                    + FIXED_TIME + ",1,evaluator,sonnet,success,30.00,0,0,0,0,1,1\n");
            runner.expect(Role.PLANNER, writeCurrent("T1"), success("3.50", "x"));

            int exit = harness(config()).run();

            assertEquals(Harness.EXIT_HALT, exit);
            assertEquals(List.of(Role.PLANNER), runner.calledRoles());
            assertTrue(haltText().contains("역할: generator (실행 전)"), haltText());
            assertEquals(0, files.readCycleCount(), "중단된 사이클은 카운트하지 않는다");
        }
    }

    @Nested
    @DisplayName("상한 도달과 실행 오류 (B1)")
    class Failures {

        @Test
        @DisplayName("상한 도달이면 사이클을 중단하고 같은 번호로 다시 돈다")
        void limitAbortsCycleAndKeepsCounter() {
            runner.expect(Role.PLANNER, writeCurrent("T1"), success("0.5", "T1 선정"))
                    .expect(Role.GENERATOR, budgetLimit("5.31"))
                    .expect(Role.PLANNER, writeCurrent("T2"), success("0.5", "T2 선정"))
                    .expect(Role.GENERATOR, success("1.0", "T2 완료"))
                    .expect(Role.EVALUATOR, success("0.5", "T2 PASS"));

            int exit = harness(config("max_iterations: 50", "max_iterations: 2")).run();

            assertEquals(Harness.EXIT_OK, exit);
            runner.assertAllStepsUsed();
            assertEquals(1, files.readCycleCount(), "두 번 시도했지만 완료한 사이클은 1개");
            List<String> journal = lines(files.journal());
            assertEquals(5, journal.size());
            assertTrue(journal.stream().allMatch(line -> line.contains("[c1]")), "JOURNAL에 [c1]이 반복된다");
            assertTrue(journal.get(1).endsWith("· $5.31 · error_max_budget_usd"), journal.get(1));
            assertTrue(Files.exists(files.logsDir().resolve("c1-planner.json")));
            assertTrue(Files.exists(files.logsDir().resolve("c1-planner-2.json")), "원본 로그를 덮어쓰지 않는다");
        }

        @Test
        @DisplayName("같은 항목에서 상한 도달이 2회 연속이면 HALT")
        void sameTaskLimitTwiceHalts() {
            runner.expect(Role.PLANNER, writeCurrent("T1"), success("0.5", "x"))
                    .expect(Role.GENERATOR, budgetLimit("5.10"))
                    .expect(Role.PLANNER, writeCurrent("T1"), success("0.5", "x"))
                    .expect(Role.GENERATOR, turnLimit("2.00"));

            int exit = harness(config()).run();

            assertEquals(Harness.EXIT_HALT, exit);
            runner.assertAllStepsUsed();
            assertTrue(haltText().startsWith("사유: 상한 도달 반복\n"), haltText());
            assertTrue(haltText().contains("T1에서"), haltText());
            assertTrue(haltText().contains("c1-generator-2.json"), haltText());
        }

        @Test
        @DisplayName("다른 항목에서 상한에 걸리면 HALT하지 않는다")
        void differentTaskLimitDoesNotHalt() {
            runner.expect(Role.PLANNER, writeCurrent("T1"), success("0.5", "x"))
                    .expect(Role.GENERATOR, budgetLimit("5.10"))
                    .expect(Role.PLANNER, writeCurrent("T2"), success("0.5", "x"))
                    .expect(Role.GENERATOR, budgetLimit("5.10"));

            int exit = harness(config("max_iterations: 50", "max_iterations: 2")).run();

            assertEquals(Harness.EXIT_OK, exit);
            assertFalse(files.isHalted());
        }

        @Test
        @DisplayName("실행 오류가 max_consecutive_errors회 연속이면 HALT (원본 로그 경로 포함)")
        void consecutiveErrorsHalt() {
            runner.expect(Role.PLANNER, error("0.01", "API Error: 529 Overloaded"))
                    .expect(Role.PLANNER, error("0.01", "API Error: 529 Overloaded"));

            int exit = harness(config()).run();

            assertEquals(Harness.EXIT_HALT, exit);
            runner.assertAllStepsUsed();
            assertTrue(haltText().startsWith("사유: 실행 오류 2회 연속\n"), haltText());
            assertTrue(haltText().contains("API Error: 529"), haltText());
            assertTrue(haltText().contains(".harness"), haltText());
            assertEquals(0, files.readCycleCount());
        }

        @Test
        @DisplayName("오류 사이에 성공이 끼면 연속 횟수가 처음부터 다시 센다")
        void successResetsErrorCount() {
            runner.expect(Role.PLANNER, error("0.01", "일시 오류"))
                    .expect(Role.PLANNER, writeCurrent("T1"), success("0.5", "x"))
                    .expect(Role.GENERATOR, error("0.01", "일시 오류"))
                    .expect(Role.PLANNER, writeDone(), success("0.5", "x"));

            int exit = harness(config()).run();

            assertEquals(Harness.EXIT_OK, exit);
            runner.assertAllStepsUsed();
        }

        @Test
        @DisplayName("결과 JSON 형식 오류는 한 번만으로 즉시 HALT (0012)")
        void invalidResultHaltsImmediately() {
            runner.expect(Role.PLANNER, invalidResult());

            int exit = harness(config()).run();

            assertEquals(Harness.EXIT_HALT, exit);
            assertTrue(haltText().startsWith("사유: 결과 JSON 형식 오류\n"), haltText());
            assertTrue(haltText().contains("total_cost_usd"), haltText());
            List<String> usage = lines(files.usageCsv());
            assertTrue(usage.get(1).contains(",invalid_result,,"), "비용을 모르면 빈 칸: " + usage.get(1));
        }
    }

    // ---- 도우미 ----

    private Harness harness(HarnessConfig config) {
        return new Harness(config, files, runner,
                (role, cycle) -> "prompt:" + role.id() + ":c" + cycle,
                FIXED_CLOCK, new PrintStream(console, true, StandardCharsets.UTF_8));
    }

    /** 테스트용 정상 harness.yml. 문자열 쌍으로 일부를 바꿀 수 있다. */
    private HarnessConfig config(String... replacements) {
        String yaml = readResource("/config/harness.yml");
        for (int i = 0; i < replacements.length; i += 2) {
            assertTrue(yaml.contains(replacements[i]), "바꿀 문자열이 없다: " + replacements[i]);
            yaml = yaml.replace(replacements[i], replacements[i + 1]);
        }
        TextFiles.write(files.harnessYml(), yaml);
        return ConfigLoader.load(files.harnessYml());
    }

    private static Consumer<ProjectFiles> writeCurrent(String taskId) {
        return f -> TextFiles.write(f.current(), taskId + "\n");
    }

    private static Consumer<ProjectFiles> writeDone() {
        return f -> TextFiles.write(f.done(), "");
    }

    private String haltText() {
        return TextFiles.read(files.halt());
    }

    private String consoleText() {
        return console.toString(StandardCharsets.UTF_8);
    }

    private static List<String> lines(Path file) {
        return TextFiles.read(file).lines().toList();
    }

    private static String readResource(String path) {
        try (InputStream in = HarnessTest.class.getResourceAsStream(path)) {
            return new String(in.readAllBytes(), StandardCharsets.UTF_8);
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }
}
