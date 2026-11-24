package harness.config;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import harness.policy.Role;
import java.io.IOException;
import java.io.InputStream;
import java.io.UncheckedIOException;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.List;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class ConfigLoaderTest {

    /** {@code src/test/resources/config/harness.yml}. 각 테스트가 일부를 바꿔 쓴다. */
    static final String VALID_YAML = readResource("/config/harness.yml");

    @TempDir
    Path dir;

    @Test
    @DisplayName("정상 설정을 읽는다")
    void loadsValidConfig() {
        HarnessConfig config = load(VALID_YAML);

        assertEquals("claude", config.claude().path());
        assertEquals("opus", config.models().forRole(Role.PLANNER));
        assertEquals("sonnet", config.models().forRole(Role.EVALUATOR));
        assertEquals(50, config.limits().maxIterations());
        assertEquals(0, new BigDecimal("38").compareTo(config.limits().maxTotalUsd()));
        assertEquals(0, new BigDecimal("5").compareTo(config.limits().maxAgentUsd()));
        assertNull(config.limits().maxTurns());
        assertNull(config.limits().maxTurnsFor(Role.GENERATOR));
        assertEquals(Duration.ofMinutes(30), config.limits().agentTimeout());
        assertEquals(2, config.limits().backlogPerMilestone());
        assertEquals(2, config.limits().maxConsecutiveErrors());
        assertEquals("./gradlew test --tests {path}", config.commands().testPath());
        assertEquals(4, config.permissions().generatorBash().size());
        assertEquals(List.of("Bash(./gradlew test:*)"), config.permissions().evaluatorBash());
    }

    @Test
    @DisplayName("소수 금액은 BigDecimal로 정확히 읽는다")
    void readsDecimalExactly() {
        HarnessConfig config = load(VALID_YAML
                .replace("max_total_usd: 38", "max_total_usd: 1")
                .replace("max_agent_usd: 5", "max_agent_usd: 0.1"));

        assertEquals(new BigDecimal("0.1"), config.limits().maxAgentUsd());
    }

    @Test
    @DisplayName("max_turns는 역할별로 일부만 줄 수 있다")
    void partialMaxTurns() {
        HarnessConfig config = load(VALID_YAML.replace("max_turns: null", "max_turns: { generator: 40 }"));

        assertEquals(40, config.limits().maxTurnsFor(Role.GENERATOR));
        assertNull(config.limits().maxTurnsFor(Role.PLANNER));
    }

    @Test
    @DisplayName("max_turns 키 자체를 빼도 된다")
    void maxTurnsKeyCanBeOmitted() {
        HarnessConfig config = load(VALID_YAML.replace("  max_turns: null\n", ""));

        assertNull(config.limits().maxTurns());
    }

    @Test
    @DisplayName("필수 키가 없으면 키 이름을 알려 준다")
    void missingRequiredKey() {
        ConfigException e = assertThrows(ConfigException.class,
                () -> load(VALID_YAML.replace("  max_total_usd: 38\n", "")));

        assertTrue(e.getMessage().contains("limits.max_total_usd가 없다"), e.getMessage());
    }

    @Test
    @DisplayName("섹션이 통째로 없으면 섹션 이름을 알려 준다")
    void missingSection() {
        String withoutModels = VALID_YAML.replace(
                "models:\n  planner: opus\n  generator: sonnet\n  evaluator: sonnet\n", "");

        ConfigException e = assertThrows(ConfigException.class, () -> load(withoutModels));

        assertTrue(e.getMessage().contains("models가 없다"), e.getMessage());
    }

    @Test
    @DisplayName("음수와 0은 거부한다")
    void negativeValues() {
        ConfigException e = assertThrows(ConfigException.class, () -> load(VALID_YAML
                .replace("max_iterations: 50", "max_iterations: 0")
                .replace("max_agent_usd: 5", "max_agent_usd: -1")));

        assertTrue(e.getMessage().contains("limits.max_iterations는 1 이상"), e.getMessage());
        assertTrue(e.getMessage().contains("limits.max_agent_usd는 0보다 커야"), e.getMessage());
    }

    @Test
    @DisplayName("1회 상한이 누적 상한보다 크면 거부한다")
    void agentLimitAboveTotal() {
        ConfigException e = assertThrows(ConfigException.class,
                () -> load(VALID_YAML.replace("max_agent_usd: 5", "max_agent_usd: 40")));

        assertTrue(e.getMessage().contains("limits.max_agent_usd(40)가 limits.max_total_usd(38)보다 크다"),
                e.getMessage());
    }

    @Test
    @DisplayName("모르는 키는 위치와 함께 거부한다 (오타 방지)")
    void unknownKey() {
        ConfigException e = assertThrows(ConfigException.class,
                () -> load(VALID_YAML.replace("max_iterations: 50", "max_iteration: 50")));

        assertTrue(e.getMessage().contains("모르는 키"), e.getMessage());
        assertTrue(e.getMessage().contains("limits.max_iteration"), e.getMessage());
    }

    @Test
    @DisplayName("숫자 자리에 문자가 오면 위치와 함께 거부한다")
    void wrongType() {
        ConfigException e = assertThrows(ConfigException.class,
                () -> load(VALID_YAML.replace("max_iterations: 50", "max_iterations: many")));

        assertTrue(e.getMessage().contains("limits.max_iterations"), e.getMessage());
    }

    @Test
    @DisplayName("test_path에 {path}가 없으면 거부한다")
    void testPathWithoutPlaceholder() {
        ConfigException e = assertThrows(ConfigException.class,
                () -> load(VALID_YAML.replace("--tests {path}", "--tests")));

        assertTrue(e.getMessage().contains("{path}"), e.getMessage());
    }

    @Test
    @DisplayName("Bash 허용 패턴 형식이 틀리면 거부한다")
    void badBashPattern() {
        ConfigException e = assertThrows(ConfigException.class,
                () -> load(VALID_YAML.replace("\"Bash(git diff:*)\"", "\"git diff\"")));

        assertTrue(e.getMessage().contains("permissions.generator_bash[3]"), e.getMessage());
    }

    @Test
    @DisplayName("허용 목록은 비어 있어도 된다")
    void emptyBashListIsAllowed() {
        HarnessConfig config = load(VALID_YAML.replace(
                "  evaluator_bash:\n    - \"Bash(./gradlew test:*)\"\n", "  evaluator_bash: []\n"));

        assertEquals(List.of(), config.permissions().evaluatorBash());
    }

    @Test
    @DisplayName("파일이 없으면 거부한다")
    void fileMissing() {
        ConfigException e = assertThrows(ConfigException.class,
                () -> ConfigLoader.load(dir.resolve(ConfigLoader.FILE_NAME)));

        assertTrue(e.getMessage().contains("harness.yml이 없다"), e.getMessage());
    }

    @Test
    @DisplayName("빈 파일은 거부한다")
    void emptyFile() {
        ConfigException e = assertThrows(ConfigException.class, () -> load(""));

        assertTrue(e.getMessage().contains("비어 있다"), e.getMessage());
    }

    // ---- 도우미 ----

    private HarnessConfig load(String yaml) {
        Path file = dir.resolve(ConfigLoader.FILE_NAME);
        try {
            Files.writeString(file, yaml, StandardCharsets.UTF_8);
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
        return ConfigLoader.load(file);
    }

    static String readResource(String path) {
        try (InputStream in = ConfigLoaderTest.class.getResourceAsStream(path)) {
            if (in == null) {
                throw new IllegalStateException("리소스가 없다: " + path);
            }
            // Windows에서 git(core.autocrlf=true)이 CRLF로 체크아웃해도 테스트의 "\n" 치환이 맞도록 LF로 통일한다.
            return new String(in.readAllBytes(), StandardCharsets.UTF_8).replace("\r\n", "\n");
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }
}
