package harness;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import harness.config.ConfigLoader;
import harness.config.HarnessConfig;
import harness.cost.UsageRecord;
import harness.prompt.PromptRenderer;
import harness.state.ProjectFiles;
import harness.state.TextFiles;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Clock;
import java.util.List;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * 스모크 검사({@link SmokeChecks})와 샘플 프로젝트 자체를 비용 없이 확인한다.
 * {@code HARNESS_SMOKE} 없이 {@code ./gradlew smokeTest}를 돌려도 이 테스트는 실행된다. claude를 부르지 않는다.
 */
class SmokeChecksTest {

    private static final String RESULT_JSON = "{\"type\":\"result\",\"subtype\":\"success\",\"is_error\":false,"
            + "\"total_cost_usd\":0.1,\"num_turns\":3,\"result\":\"T1 선정\",\"permission_denials\":[]}";

    @TempDir
    Path dir;

    ProjectFiles files;

    @BeforeEach
    void setUp() {
        files = new ProjectFiles(dir);
        files.createDirectories();
        writeValidProject();
    }

    @Test
    @DisplayName("샘플 프로젝트: harness.yml이 읽히고 프롬프트 템플릿이 모두 치환되며 PRD가 있다")
    void sampleProjectIsValid() throws Exception {
        Path sample = Path.of(SmokeChecksTest.class.getResource("/sample-project").toURI());

        HarnessConfig config = ConfigLoader.load(sample.resolve("harness.yml"));
        new PromptRenderer(config, Clock.systemDefaultZone()).checkTemplates();

        assertTrue(Files.exists(sample.resolve("docs/PRD.md")));
        assertEquals("haiku", config.models().planner());
        assertEquals("haiku", config.models().generator());
        assertEquals("haiku", config.models().evaluator());
    }

    @Test
    @DisplayName("정상 폴더는 모든 검사를 통과한다")
    void validProjectPasses() {
        SmokeChecks.Report report = SmokeChecks.inspect(dir, Harness.EXIT_OK);

        assertTrue(report.allPassed(), report.toMarkdown());
    }

    @Test
    @DisplayName("예산 소진 HALT는 정상 종료로 보지만, 다른 HALT는 실패다")
    void haltReasons() {
        TextFiles.write(files.halt(), "사유: 예산 소진\n상세: x\n");
        assertTrue(SmokeChecks.inspect(dir, Harness.EXIT_HALT).allPassed());

        TextFiles.write(files.halt(), "사유: CURRENT 누락\n상세: x\n");
        assertFalse(SmokeChecks.inspect(dir, Harness.EXIT_HALT).allPassed());
    }

    @Test
    @DisplayName("REVIEW에 평가 대상 줄이 없으면 실패")
    void reviewWithoutTarget() {
        TextFiles.write(files.review(), "판정: PASS 9/9\n핵심 결정: -\n");

        assertFailed("REVIEW.md");
    }

    @Test
    @DisplayName("JOURNAL에 에이전트가 직접 쓴 형식의 줄이 있으면 실패")
    void journalWithAgentLine() {
        TextFiles.appendLine(files.journal(), "- 2026-11-24T12:30:00 planner: 직접 쓴 줄");

        assertFailed("JOURNAL.md");
    }

    @Test
    @DisplayName("프롬프트에 {{가 남아 있으면 실패")
    void leftoverVariable() {
        TextFiles.write(files.logsDir().resolve("c1-planner.prompt.md"), "명령: {{commands.test}}");

        assertFailed("{{...}}");
    }

    @Test
    @DisplayName("허용 목록의 명령이 거부됐으면 실패, 목록 밖 명령의 거부는 참고만")
    void permissionDenials() {
        String denied = "{\"type\":\"result\",\"subtype\":\"success\",\"is_error\":false,\"total_cost_usd\":0.1,"
                + "\"permission_denials\":[{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"rm -rf src\"}}]}";
        TextFiles.write(files.logsDir().resolve("c1-generator.json"), denied);
        SmokeChecks.Report outside = SmokeChecks.inspect(dir, Harness.EXIT_OK);
        assertTrue(outside.allPassed(), outside.toMarkdown());
        assertTrue(outside.info().stream().anyMatch(line -> line.contains("rm -rf src")));

        String allowedDenied = denied.replace("rm -rf src", "python3 -m unittest discover");
        TextFiles.write(files.logsDir().resolve("c1-generator.json"), allowedDenied);
        assertFailed("permission_denials");
    }

    @Test
    @DisplayName("USAGE.csv 줄 수가 원본 로그 수와 다르면 실패")
    void usageRowMismatch() {
        TextFiles.write(files.logsDir().resolve("c2-planner.json"), RESULT_JSON);

        assertFailed("USAGE.csv");
    }

    private void assertFailed(String nameFragment) {
        SmokeChecks.Report report = SmokeChecks.inspect(dir, Harness.EXIT_OK);
        assertFalse(report.allPassed(), "실패해야 한다:\n" + report.toMarkdown());
        List<SmokeChecks.Check> failed = report.checks().stream().filter(c -> !c.ok()).toList();
        assertTrue(failed.stream().anyMatch(c -> c.name().contains(nameFragment)),
                nameFragment + " 검사가 실패해야 한다: " + failed);
    }

    /** 사이클 1을 3역할이 정상으로 마친 뒤의 폴더를 손으로 만든다. */
    private void writeValidProject() {
        TextFiles.write(files.tasks(), "# TASKS\n\n## M1. 문자열\n\n- [x] T1. reverse 구현\n  - 내용\n");
        TextFiles.write(files.review(), "판정: PASS 11/12\n핵심 결정: -\n메모: 없음\n\n"
                + "평가 대상: T1 · 사이클 1 · 2026-11-24T12:26:46+09:00\n");
        TextFiles.write(files.reviewsCsv(), "task_id,cycle,verdict,key_decision\nT1,1,PASS 11/12,-\n");
        TextFiles.write(files.journal(),
                "- 2026-11-24T12:26:46+09:00 [c1] planner: T1 선정 · $0.10 · success\n"
                        + "- 2026-11-24T12:27:46+09:00 [c1] generator: T1 완료 · $0.20 · success\n"
                        + "- 2026-11-24T12:28:46+09:00 [c1] evaluator: T1 PASS 11/12 · $0.10 · success · PASS 11/12\n");
        String row = ",1,%s,haiku,success,0.10,1,2,3,4,3,1000";
        TextFiles.write(files.usageCsv(), UsageRecord.CSV_HEADER + "\n"
                + "2026-11-24T12:26:46+09:00" + row.formatted("planner") + "\n"
                + "2026-11-24T12:27:46+09:00" + row.formatted("generator") + "\n"
                + "2026-11-24T12:28:46+09:00" + row.formatted("evaluator") + "\n");
        for (String role : List.of("planner", "generator", "evaluator")) {
            TextFiles.write(files.logsDir().resolve("c1-" + role + ".json"), RESULT_JSON);
            TextFiles.write(files.logsDir().resolve("c1-" + role + ".prompt.md"), "# 프롬프트 " + role);
        }
        files.saveCycleCount(1);
    }
}
