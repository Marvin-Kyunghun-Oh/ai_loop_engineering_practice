package harness.policy;

import harness.config.HarnessConfig.Permissions;
import java.util.ArrayList;
import java.util.List;

/**
 * 역할별 허용·금지 도구 (0008, DESIGN 5.5).
 *
 * <table>
 *   <tr><th>역할</th><th>allowedTools</th><th>비고</th></tr>
 *   <tr><td>planner</td><td>Read Glob Grep Edit(docs/**) Write(docs/**)</td><td>Bash 없음 (v1과 같음)</td></tr>
 *   <tr><td>generator</td><td>Read Write Edit Glob Grep + permissions.generator_bash</td><td>acceptEdits</td></tr>
 *   <tr><td>evaluator</td><td>Read Glob Grep Edit(docs/**) Write(docs/**) + permissions.evaluator_bash</td><td></td></tr>
 * </table>
 *
 * <p>금지 목록: Bash 허용 패턴이 없는 역할만 {@code --disallowedTools Bash}를 받는다.
 * 2026-11-24 실제 확인 결과(DESIGN 9절, 0008)는 다음과 같다.
 * <ul>
 *   <li>{@code --disallowedTools Bash}는 {@code Bash(echo:*)} 허용보다 우선한다. 같이 주면 허용 명령도 막힌다.</li>
 *   <li>허용 목록만 주면 목록 밖의 쓰기 명령(touch)은 거부되고 결과 JSON의 {@code permission_denials}에 남는다.</li>
 *   <li>단, 읽기 전용 명령(whoami)은 허용 목록과 무관하게 통과한다. 그래서 Bash가 아예 없어야 하는 역할은
 *       금지 목록으로 Bash 자체를 뺀다.</li>
 * </ul>
 */
public final class ToolPolicy {

    private static final List<String> DOCS_ONLY_EDIT =
            List.of("Read", "Glob", "Grep", "Edit(docs/**)", "Write(docs/**)");
    private static final List<String> FULL_EDIT =
            List.of("Read", "Write", "Edit", "Glob", "Grep");
    private static final List<String> BASH = List.of("Bash");

    private final Permissions permissions;

    public ToolPolicy(Permissions permissions) {
        this.permissions = permissions;
    }

    public List<String> allowedTools(Role role) {
        return switch (role) {
            case PLANNER -> DOCS_ONLY_EDIT;
            case GENERATOR -> concat(FULL_EDIT, bashPatterns(role));
            case EVALUATOR -> concat(DOCS_ONLY_EDIT, bashPatterns(role));
        };
    }

    /** 역할에 열어 줄 Bash 패턴. planner는 항상 없다. */
    private List<String> bashPatterns(Role role) {
        return switch (role) {
            case PLANNER -> List.of();
            case GENERATOR -> permissions.generatorBash();
            case EVALUATOR -> permissions.evaluatorBash();
        };
    }

    public List<String> disallowedTools(Role role) {
        return bashPatterns(role).isEmpty() ? BASH : List.of();
    }

    /** 편집을 묻지 않고 승인할지. generator만 그렇다. */
    public boolean acceptEdits(Role role) {
        return role == Role.GENERATOR;
    }

    private static List<String> concat(List<String> base, List<String> extra) {
        List<String> all = new ArrayList<>(base);
        all.addAll(extra);
        return List.copyOf(all);
    }
}
