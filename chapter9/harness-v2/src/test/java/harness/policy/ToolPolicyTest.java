package harness.policy;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import harness.config.HarnessConfig.Permissions;
import java.util.List;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/** 역할별 목록이 DESIGN 5.5 표와 harness.yml의 permissions와 일치하는지. */
class ToolPolicyTest {

    private final ToolPolicy policy = new ToolPolicy(new Permissions(
            List.of("Bash(./gradlew build:*)", "Bash(./gradlew test:*)"),
            List.of("Bash(./gradlew test:*)")));

    @Test
    @DisplayName("planner: docs/만 편집, Bash 없음")
    void planner() {
        assertEquals(List.of("Read", "Glob", "Grep", "Edit(docs/**)", "Write(docs/**)"),
                policy.allowedTools(Role.PLANNER));
        assertFalse(policy.acceptEdits(Role.PLANNER));
    }

    @Test
    @DisplayName("generator: 전체 편집 + generator_bash, acceptEdits")
    void generator() {
        assertEquals(List.of("Read", "Write", "Edit", "Glob", "Grep",
                        "Bash(./gradlew build:*)", "Bash(./gradlew test:*)"),
                policy.allowedTools(Role.GENERATOR));
        assertTrue(policy.acceptEdits(Role.GENERATOR));
    }

    @Test
    @DisplayName("evaluator: docs/만 편집 + evaluator_bash")
    void evaluator() {
        assertEquals(List.of("Read", "Glob", "Grep", "Edit(docs/**)", "Write(docs/**)", "Bash(./gradlew test:*)"),
                policy.allowedTools(Role.EVALUATOR));
        assertFalse(policy.acceptEdits(Role.EVALUATOR));
    }

    @Test
    @DisplayName("Bash 패턴이 있는 역할은 금지 목록이 비어 있다 (금지가 허용 패턴보다 우선하므로)")
    void noDisallowWhenPatternsExist() {
        assertEquals(List.of(), policy.disallowedTools(Role.GENERATOR));
        assertEquals(List.of(), policy.disallowedTools(Role.EVALUATOR));
    }

    @Test
    @DisplayName("Bash 패턴이 없는 역할은 Bash 자체를 뺀다 (읽기 전용 명령도 막기 위해)")
    void disallowBashWhenNoPatterns() {
        assertEquals(List.of("Bash"), policy.disallowedTools(Role.PLANNER));

        ToolPolicy noEvaluatorBash = new ToolPolicy(new Permissions(List.of("Bash(./gradlew test:*)"), List.of()));
        assertEquals(List.of("Bash"), noEvaluatorBash.disallowedTools(Role.EVALUATOR));
        assertEquals(List.of("Read", "Glob", "Grep", "Edit(docs/**)", "Write(docs/**)"),
                noEvaluatorBash.allowedTools(Role.EVALUATOR));
    }
}
