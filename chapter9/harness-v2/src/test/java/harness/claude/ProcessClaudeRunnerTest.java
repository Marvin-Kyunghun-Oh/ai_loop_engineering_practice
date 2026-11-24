package harness.claude;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import harness.policy.Role;
import java.io.IOException;
import java.math.BigDecimal;
import java.net.URISyntaxException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.List;
import java.util.Locale;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * 실제 claude 대신 {@link FakeClaudeMain}을 래퍼 스크립트로 실행해 프로세스 처리를 검증한다. 비용이 들지 않는다.
 * Windows에서는 .cmd 래퍼라서 인자가 cmd.exe를 거친다. npm 설치판 claude.cmd와 같은 경로다.
 */
class ProcessClaudeRunnerTest {

    private static final boolean WINDOWS =
            System.getProperty("os.name", "").toLowerCase(Locale.ROOT).startsWith("windows");

    @TempDir
    Path workDir;

    @TempDir
    Path recordDir;

    Path rawLog;

    @BeforeEach
    void setUp() throws IOException {
        Path logs = workDir.resolve(".harness/logs");
        Files.createDirectories(logs);
        rawLog = logs.resolve("c1-generator.json");
    }

    @Test
    @DisplayName("명령줄: 프롬프트는 인자에 없고, 도구 목록은 맨 뒤에 온다")
    void buildCommand() {
        ProcessClaudeRunner runner = new ProcessClaudeRunner("claude");

        List<String> command = runner.buildCommand(request("prompt", Duration.ofMinutes(30)));

        assertEquals(List.of("claude", "-p", "--output-format", "json", "--model", "sonnet",
                "--max-budget-usd", "5", "--max-turns", "40", "--permission-mode", "acceptEdits",
                "--allowedTools", "Read", "Edit(docs/**)", "Bash(./gradlew test:*)",
                "--disallowedTools", "Bash"), command);
    }

    @Test
    @DisplayName("선택 옵션이 없으면 넣지 않는다")
    void buildCommandWithoutOptionals() {
        AgentRequest planner = new AgentRequest(Role.PLANNER, "p", "opus", List.of("Read"), List.of(), false,
                new BigDecimal("0.50"), null, Duration.ofMinutes(1), workDir, rawLog);

        List<String> command = new ProcessClaudeRunner("claude").buildCommand(planner);

        assertEquals(List.of("claude", "-p", "--output-format", "json", "--model", "opus",
                "--max-budget-usd", "0.50", "--allowedTools", "Read"), command);
    }

    @Test
    @DisplayName("프롬프트 파일 이름")
    void promptFileName() {
        assertEquals("c1-generator.prompt.md", ProcessClaudeRunner.promptFileFor(rawLog).getFileName().toString());
    }

    @Test
    @DisplayName("성공: 프롬프트(한글, 8,000자 초과)는 표준 입력으로, 인자는 그대로, 결과 JSON은 원본 로그로")
    void success() throws Exception {
        String prompt = "# 생성자\n" + "한글 프롬프트 {{commands.test}} ".repeat(500);   // 약 12,500자
        assertTrue(prompt.length() > 8_000);
        ProcessClaudeRunner runner = new ProcessClaudeRunner(fakeClaude("success").toString());
        AgentRequest request = request(prompt, Duration.ofMinutes(1));

        AgentResult result = runner.run(request);

        assertEquals(Outcome.SUCCESS, result.outcome(), result.summary());
        assertEquals(new BigDecimal("0.00271608"), result.costUsd());
        assertEquals(prompt, Files.readString(recordDir.resolve("stdin.txt"), StandardCharsets.UTF_8));
        List<String> expectedArgs = runner.buildCommand(request).subList(1, runner.buildCommand(request).size());
        assertEquals(expectedArgs, Files.readAllLines(recordDir.resolve("args.txt"), StandardCharsets.UTF_8),
                "괄호·별표·공백이 든 인자가 그대로 전달돼야 한다");
        assertEquals(workDir.toRealPath(), Path.of(Files.readString(recordDir.resolve("cwd.txt"))).toRealPath());
        assertTrue(Files.readString(rawLog).contains("\"subtype\": \"success\""), "원본 로그");
        assertEquals(prompt, Files.readString(ProcessClaudeRunner.promptFileFor(rawLog), StandardCharsets.UTF_8));
    }

    @Test
    @DisplayName("결과 JSON이 아니면 ERROR, 요약에 종료 코드를 덧붙인다")
    void garbageOutput() throws Exception {
        ProcessClaudeRunner runner = new ProcessClaudeRunner(fakeClaude("garbage").toString());

        AgentResult result = runner.run(request("p", Duration.ofMinutes(1)));

        assertEquals(Outcome.ERROR, result.outcome());
        assertTrue(result.summary().startsWith("결과 JSON 파싱 실패"), result.summary());
        assertTrue(result.summary().endsWith("(종료 코드 3)"), result.summary());
    }

    @Test
    @DisplayName("시간을 넘기면 TIMEOUT, 자식 프로세스까지 끝낸다")
    void timeoutKillsProcessTree() throws Exception {
        ProcessClaudeRunner runner = new ProcessClaudeRunner(fakeClaude("sleep").toString());

        long start = System.nanoTime();
        AgentResult result = runner.run(request("p", Duration.ofSeconds(5)));
        long elapsedMs = (System.nanoTime() - start) / 1_000_000;

        assertEquals(Outcome.TIMEOUT, result.outcome());
        assertEquals("제한 시간 5초을 넘겨 종료했다", result.summary());
        assertTrue(elapsedMs < 30_000, "120초 동안 기다리지 않아야 한다: " + elapsedMs + "ms");

        long pid = Long.parseLong(Files.readString(recordDir.resolve("pid.txt")).strip());
        assertFalse(ProcessHandle.of(pid).map(ProcessHandle::isAlive).orElse(false),
                "래퍼(cmd.exe) 아래의 java 프로세스도 끝나야 한다");
    }

    @Test
    @DisplayName("실행 파일이 없으면 ERROR")
    void missingExecutable() {
        ProcessClaudeRunner runner = new ProcessClaudeRunner(workDir.resolve("no-such-claude.exe").toString());

        AgentResult result = runner.run(request("p", Duration.ofMinutes(1)));

        assertEquals(Outcome.ERROR, result.outcome());
        assertTrue(result.summary().startsWith("claude를 실행하지 못했다"), result.summary());
    }

    // ---- 도우미 ----

    private AgentRequest request(String prompt, Duration timeout) {
        return new AgentRequest(Role.GENERATOR, prompt, "sonnet",
                List.of("Read", "Edit(docs/**)", "Bash(./gradlew test:*)"), List.of("Bash"), true,
                new BigDecimal("5"), 40, timeout, workDir, rawLog);
    }

    /** FakeClaudeMain을 실행하는 래퍼 스크립트를 만든다. */
    private Path fakeClaude(String mode) throws IOException, URISyntaxException {
        Path java = Path.of(System.getProperty("java.home"), "bin", WINDOWS ? "java.exe" : "java");
        Path classes = Path.of(FakeClaudeMain.class.getProtectionDomain().getCodeSource().getLocation().toURI());
        Path stdout = Path.of(getClass().getResource("/claude-result/success.json").toURI());

        if (WINDOWS) {
            Path script = recordDir.resolve("fake-claude.cmd");
            Files.writeString(script, String.join("\r\n",
                    "@echo off",
                    "set \"FAKE_CLAUDE_MODE=" + mode + "\"",
                    "set \"FAKE_CLAUDE_RECORD=" + recordDir + "\"",
                    "set \"FAKE_CLAUDE_STDOUT=" + stdout + "\"",
                    "\"" + java + "\" -cp \"" + classes + "\" harness.claude.FakeClaudeMain %*",
                    ""));
            return script;
        }
        Path script = recordDir.resolve("fake-claude.sh");
        Files.writeString(script, String.join("\n",
                "#!/bin/sh",
                "export FAKE_CLAUDE_MODE='" + mode + "'",
                "export FAKE_CLAUDE_RECORD='" + recordDir + "'",
                "export FAKE_CLAUDE_STDOUT='" + stdout + "'",
                "exec '" + java + "' -cp '" + classes + "' harness.claude.FakeClaudeMain \"$@\"",
                ""));
        script.toFile().setExecutable(true);
        return script;
    }
}
