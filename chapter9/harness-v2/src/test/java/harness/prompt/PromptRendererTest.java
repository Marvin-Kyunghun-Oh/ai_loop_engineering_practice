package harness.prompt;

import static harness.testing.TestFixtures.FIXED_CLOCK;
import static harness.testing.TestFixtures.FIXED_TIME;
import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import harness.config.ConfigLoader;
import harness.config.HarnessConfig;
import harness.policy.Role;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.EnumSource;

class PromptRendererTest {

    @Nested
    @DisplayName("치환 규칙")
    class Rules {

        @Test
        @DisplayName("{{이름}}을 값으로 바꾸고, 이름 앞뒤 공백은 허용한다")
        void replaces() {
            String result = PromptRenderer.render("t.md", "a {{x.y}} b {{ x.y }} c",
                    Map.of("x.y", "값"));

            assertEquals("a 값 b 값 c", result);
        }

        @Test
        @DisplayName("값에 $나 \\가 있어도 그대로 들어간다")
        void valueWithSpecialCharacters() {
            String result = PromptRenderer.render("t.md", "{{v}}", Map.of("v", "$HOME\\bin $1"));

            assertEquals("$HOME\\bin $1", result);
        }

        @Test
        @DisplayName("중괄호 하나({path}, {주제})는 변수가 아니다")
        void singleBracesAreText() {
            String result = PromptRenderer.render("t.md", "{{cmd}} / docs/decisions/{주제}.md",
                    Map.of("cmd", "./gradlew test --tests {path}"));

            assertEquals("./gradlew test --tests {path} / docs/decisions/{주제}.md", result);
        }

        @Test
        @DisplayName("모르는 변수는 모두 모아 예외로 알린다")
        void unknownVariables() {
            PromptException e = assertThrows(PromptException.class,
                    () -> PromptRenderer.render("planner.md", "{{a}} {{commands.tset}} {{cycle.nmber}}",
                            Map.of("a", "1")));

            assertTrue(e.getMessage().contains("planner.md"), e.getMessage());
            assertTrue(e.getMessage().contains("commands.tset, cycle.nmber"), e.getMessage());
        }

        @Test
        @DisplayName("닫히지 않은 {{는 예외")
        void unclosedBraces() {
            assertThrows(PromptException.class,
                    () -> PromptRenderer.render("t.md", "{{a}} 그리고 {{b", Map.of("a", "1")));
        }

        @Test
        @DisplayName("없는 프롬프트 파일은 예외")
        void missingTemplate() {
            assertThrows(PromptException.class, () -> PromptRenderer.loadTemplate("nope.md"));
        }
    }

    @Nested
    @DisplayName("실제 프롬프트 파일 (src/main/resources/prompts)")
    class BundledPrompts {

        @TempDir
        Path dir;

        private PromptRenderer renderer;

        @BeforeEach
        void setUp() throws IOException {
            Path yml = dir.resolve(ConfigLoader.FILE_NAME);
            Files.writeString(yml, readResource("/config/harness.yml"), StandardCharsets.UTF_8);
            HarnessConfig config = ConfigLoader.load(yml);
            renderer = new PromptRenderer(config, FIXED_CLOCK);
        }

        @Test
        @DisplayName("세 역할 모두 치환에 성공한다 (하네스 시작 때 하는 검사)")
        void checkTemplates() {
            assertDoesNotThrow(() -> renderer.checkTemplates());
        }

        @ParameterizedTest
        @EnumSource(Role.class)
        @DisplayName("치환 후 {{가 남지 않고, 사이클 번호와 시각이 들어간다")
        void noLeftoverVariables(Role role) {
            String prompt = renderer.promptFor(role, 12);

            assertFalse(prompt.contains("{{"), role + " 프롬프트에 {{가 남았다");
            assertTrue(prompt.contains("이번 사이클: 12"), role.id());
            assertTrue(prompt.contains(FIXED_TIME), role.id());
        }

        @Test
        @DisplayName("generator: harness.yml의 명령이 들어간다 (D3)")
        void generatorCommands() {
            String prompt = renderer.promptFor(Role.GENERATOR, 1);

            assertTrue(prompt.contains("`./gradlew test`"), prompt);
            assertTrue(prompt.contains("`./gradlew test --tests {path}`"), prompt);
            assertTrue(prompt.contains("`./gradlew build`"), prompt);
            assertTrue(prompt.contains("build.gradle의 dependencies 블록에 추가한다"), prompt);
        }

        @Test
        @DisplayName("evaluator: 테스트 명령과 REVIEW 평가 대상 줄의 사이클이 들어간다")
        void evaluatorCommands() {
            String prompt = renderer.promptFor(Role.EVALUATOR, 7);

            assertTrue(prompt.contains("`./gradlew test --tests {path}`"), prompt);
            assertTrue(prompt.contains("평가 대상: T8r · 사이클 7 · " + FIXED_TIME), prompt);
        }

        @Test
        @DisplayName("planner: BACKLOG 처리 상한이 harness.yml 값으로 들어간다 (0010)")
        void plannerBacklogLimit() {
            String prompt = renderer.promptFor(Role.PLANNER, 1);

            assertTrue(prompt.contains("**최대 2개**"), prompt);
        }

        @ParameterizedTest
        @EnumSource(Role.class)
        @DisplayName("v1의 uv 명령과 JOURNAL 쓰기 지시가 남아 있지 않다 (D3, 0009)")
        void noV1Leftovers(Role role) {
            String prompt = renderer.promptFor(role, 1);

            assertFalse(prompt.contains("uv run"), role.id());
            assertFalse(prompt.contains("uv add"), role.id());
            assertFalse(prompt.contains("run.py"), role.id());
            assertFalse(prompt.contains("JOURNAL.md 마지막 줄"), role.id());
        }

        @Test
        @DisplayName("planner_bootstrap: 변수 없이 읽히고 JOURNAL 쓰기 지시가 없다")
        void bootstrap() {
            String prompt = renderer.bootstrapPrompt();

            assertTrue(prompt.contains("PRD 부트스트랩"));
            assertFalse(prompt.contains("{{"));
            assertFalse(prompt.contains("JOURNAL.md 마지막 줄"));
        }
    }

    private static String readResource(String name) throws IOException {
        try (InputStream in = PromptRendererTest.class.getResourceAsStream(name)) {
            return new String(in.readAllBytes(), StandardCharsets.UTF_8);
        }
    }
}
