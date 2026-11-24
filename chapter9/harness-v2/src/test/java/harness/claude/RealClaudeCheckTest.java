package harness.claude;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import harness.policy.Role;
import harness.state.TextFiles;
import java.io.IOException;
import java.math.BigDecimal;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.List;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;

/**
 * 실제 claude로 DESIGN 9절의 CLI 동작을 확인한다. <b>비용이 든다</b> (haiku, 1회 상한 $0.05).
 *
 * <p>평소에는 건너뛴다. 실행하려면 환경 변수를 켠다.
 * <pre>
 * $env:HARNESS_REAL_CLAUDE = "1"; ./gradlew test --tests harness.claude.RealClaudeCheckTest
 * </pre>
 * 원본 로그와 리포트는 {@code build/real-claude-check/}에 남는다.
 */
@EnabledIfEnvironmentVariable(named = "HARNESS_REAL_CLAUDE", matches = "1")
class RealClaudeCheckTest {

    private static final Path OUT = Path.of("build", "real-claude-check").toAbsolutePath();
    private static final ObjectMapper JSON = new ObjectMapper();

    private final ProcessClaudeRunner runner = new ProcessClaudeRunner(ClaudeExecutable.resolve("claude"));

    @Test
    @DisplayName("1. 프롬프트를 표준 입력으로 받는다 (8,000자 초과 포함)")
    void promptFromStdin() throws IOException {
        String padding = "<!-- 이 줄은 길이 확인용 채움 문자열이다. 무시한다. -->\n".repeat(250);
        String prompt = padding + "Reply with exactly the word PONG and nothing else.";
        assertTrue(prompt.length() > 8_000, "길이: " + prompt.length());

        AgentResult result = run("1-stdin", prompt, List.of("Read"), List.of());

        report("1-stdin", "prompt length=" + prompt.length(), result);
        assertEquals(Outcome.SUCCESS, result.outcome(), result.summary());
        assertTrue(result.summary().contains("PONG"), result.summary());
    }

    @Test
    @DisplayName("2. --disallowedTools Bash 와 Bash(echo:*) 허용이 함께 있을 때 어느 쪽이 이기는가")
    void disallowedVersusAllowedPattern() throws IOException {
        String prompt = "Use the Bash tool to run exactly this command: echo harness-ok\n"
                + "Then reply with the command output only. "
                + "If the Bash tool is unavailable or the command is denied, reply with the single word DENIED.";

        AgentResult result = run("2-precedence", prompt, List.of("Bash(echo:*)"), List.of("Bash"));

        report("2-precedence", "allowed=[Bash(echo:*)] disallowed=[Bash]", result);
        assertEquals(Outcome.SUCCESS, result.outcome(), result.summary());
        // 2026-11-24 확인: 금지가 이긴다. Bash 자체가 빠져 permission_denials에도 남지 않는다.
        assertTrue(result.summary().contains("DENIED"), result.summary());
    }

    /*
     * 첫 확인(2026-11-24)에서는 2번 명령이 whoami였는데 허용 목록 밖인데도 실행됐다.
     * CLI가 읽기 전용 명령은 허용 목록과 무관하게 통과시키는 것으로 보인다(사용자 설정에 허용 규칙 없음).
     * 0008이 막으려는 것은 파일을 바꾸는 명령이므로, 쓰기 명령(touch)으로 확인한다.
     */
    @Test
    @DisplayName("3. 허용 목록만 있을 때: 허용 명령은 통과, 목록 밖 쓰기 명령은 거부")
    void allowListOnly() throws IOException {
        Path marker = OUT.resolve("3-allow-only").resolve("should-not-exist.txt");
        Files.deleteIfExists(marker);
        String prompt = "Use the Bash tool twice, one command per call:\n"
                + "1) echo harness-ok\n"
                + "2) touch should-not-exist.txt\n"
                + "Reply in two lines: the output of each command (or OK if it printed nothing), "
                + "or DENIED if that command was denied.";

        AgentResult result = run("3-allow-only", prompt, List.of("Bash(echo:*)"), List.of());

        report("3-allow-only", "allowed=[Bash(echo:*)] disallowed=[]", result);
        assertEquals(Outcome.SUCCESS, result.outcome(), result.summary());
        assertTrue(Files.notExists(marker), "허용 목록 밖 쓰기 명령이 실행됐다");
    }

    // ---- 도우미 ----

    private AgentResult run(String name, String prompt, List<String> allowed, List<String> disallowed)
            throws IOException {
        Path workDir = OUT.resolve(name);
        Files.createDirectories(workDir);
        Path rawLog = workDir.resolve("result.json");
        Files.deleteIfExists(rawLog);
        AgentRequest request = new AgentRequest(Role.GENERATOR, prompt, "haiku", allowed, disallowed, false,
                new BigDecimal("0.05"), null, Duration.ofMinutes(3), workDir, rawLog);
        return runner.run(request);
    }

    /** 결과와 permission_denials를 리포트 파일에 남긴다. */
    private void report(String name, String setting, AgentResult result) throws IOException {
        Path rawLog = OUT.resolve(name).resolve("result.json");
        String denials = "(원본 없음)";
        if (Files.exists(rawLog)) {
            JsonNode node = JSON.readTree(Files.readString(rawLog)).path("permission_denials");
            denials = node.toString();
        }
        String line = String.join(" | ",
                name, setting,
                "outcome=" + result.outcome(),
                "cost=" + result.costUsd(),
                "turns=" + result.numTurns(),
                "result=" + result.summary().replace("\n", "\\n"),
                "permission_denials=" + denials);
        TextFiles.appendLine(OUT.resolve("report.txt"), line);
        System.out.println(line);
    }
}
