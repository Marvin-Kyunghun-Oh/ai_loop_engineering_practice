package harness;

import harness.claude.AgentRequest;
import harness.claude.ClaudeRunner;
import harness.config.HarnessConfig;
import harness.policy.Role;
import harness.policy.ToolPolicy;
import harness.prompt.PromptProvider;
import harness.state.ProjectFiles;
import java.nio.file.Files;
import java.util.function.Consumer;

/**
 * PRD가 없을 때 사용자와 대화하며 {@code docs/PRD.md}를 쓰는 대화형 planner 세션 (DESIGN 4.5, v1 {@code bootstrap_prd}).
 *
 * <p>블로킹 호출이다. 사용자가 대화를 마칠 때까지 기다리고, 그래도 PRD가 없으면 실패로 돌려준다.
 * 사이클이 PRD를 기다리며 도는 일은 없다.
 *
 * <p>이 세션의 비용은 결과 JSON이 없어 USAGE.csv와 누적 상한에 잡히지 않는다(DESIGN 4.5).
 */
final class Bootstrap {

    private final HarnessConfig config;
    private final ProjectFiles files;
    private final ClaudeRunner runner;
    private final PromptProvider prompts;
    private final ToolPolicy toolPolicy;
    private final Consumer<String> log;

    Bootstrap(HarnessConfig config, ProjectFiles files, ClaudeRunner runner, PromptProvider prompts,
              Consumer<String> log) {
        this.config = config;
        this.files = files;
        this.runner = runner;
        this.prompts = prompts;
        this.toolPolicy = new ToolPolicy(config.permissions());
        this.log = log;
    }

    /** @return 끝난 뒤 PRD.md가 있으면 true */
    boolean run() {
        if (Files.exists(files.prd())) {
            return true;
        }
        log.accept("docs/PRD.md가 없다. planner를 대화형으로 실행한다.");
        log.accept("사용자와 대화하여 PRD.md를 작성한 뒤 종료한다. (claude 종료: /exit)");

        AgentRequest request = new AgentRequest(
                Role.PLANNER,
                prompts.bootstrapPrompt(),
                config.models().forRole(Role.PLANNER),
                toolPolicy.allowedTools(Role.PLANNER),
                toolPolicy.disallowedTools(Role.PLANNER),
                false,
                config.limits().maxAgentUsd(),    // 대화형에는 적용되지 않는다 (--max-budget-usd는 -p 전용)
                null,
                config.limits().agentTimeout(),   // 대화형에는 적용되지 않는다
                files.root(),
                files.logsDir().resolve("bootstrap.json"));   // 옆에 bootstrap.prompt.md가 남는다
        try {
            runner.runInteractive(request);
        } catch (IllegalStateException e) {
            log.accept("부트스트랩을 실행하지 못했다: " + e.getMessage());
            return false;
        }
        return Files.exists(files.prd());
    }
}
