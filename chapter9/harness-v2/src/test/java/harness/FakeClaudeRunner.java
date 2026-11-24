package harness;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.junit.jupiter.api.Assertions.fail;

import harness.claude.AgentRequest;
import harness.claude.AgentResult;
import harness.claude.ClaudeRunner;
import harness.policy.Role;
import harness.state.ProjectFiles;
import harness.state.TextFiles;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.List;
import java.util.function.Consumer;

/**
 * 실제 claude 대신 미리 정한 순서대로 결과를 돌려주는 실행기 (D4).
 *
 * <pre>
 * runner.expect(Role.PLANNER, files -&gt; write(files.current(), "T1"), success("0.5", "T1 선정"))
 *       .expect(Role.GENERATOR, success("1.0", "T1 완료"));
 * </pre>
 * 정한 것과 다른 역할이 호출되거나, 정한 것보다 많이 호출되면 테스트가 실패한다.
 */
final class FakeClaudeRunner implements ClaudeRunner {

    /** 한 번의 호출: 기대하는 역할, 에이전트가 남길 파일(부수 효과), 돌려줄 결과 */
    private record Step(Role role, Consumer<ProjectFiles> sideEffect, AgentResult result) {
    }

    private final ProjectFiles files;
    private final Deque<Step> steps = new ArrayDeque<>();
    private final List<AgentRequest> requests = new ArrayList<>();
    private final List<AgentRequest> interactiveRequests = new ArrayList<>();
    private Consumer<ProjectFiles> interactiveSideEffect = ignored -> { };

    FakeClaudeRunner(ProjectFiles files) {
        this.files = files;
    }

    FakeClaudeRunner expect(Role role, AgentResult result) {
        return expect(role, ignored -> { }, result);
    }

    FakeClaudeRunner expect(Role role, Consumer<ProjectFiles> sideEffect, AgentResult result) {
        steps.addLast(new Step(role, sideEffect, result));
        return this;
    }

    @Override
    public AgentResult run(AgentRequest request) {
        requests.add(request);
        Step step = steps.pollFirst();
        if (step == null) {
            fail("예상하지 못한 호출: " + request.role().id() + " (" + requests.size() + "번째)");
        }
        assertEquals(step.role(), request.role(), requests.size() + "번째 호출의 역할");

        step.sideEffect().accept(files);
        TextFiles.write(request.rawLogFile(), "{}");   // 실제 실행기처럼 원본 로그를 남긴다
        return step.result();
    }

    @Override
    public void runInteractive(AgentRequest request) {
        interactiveRequests.add(request);
        interactiveSideEffect.accept(files);
    }

    /** 대화형 실행(부트스트랩)이 끝날 때 남길 파일. 정하지 않으면 아무것도 남기지 않는다. */
    FakeClaudeRunner onInteractive(Consumer<ProjectFiles> sideEffect) {
        this.interactiveSideEffect = sideEffect;
        return this;
    }

    List<AgentRequest> interactiveRequests() {
        return interactiveRequests;
    }

    List<AgentRequest> requests() {
        return requests;
    }

    List<Role> calledRoles() {
        return requests.stream().map(AgentRequest::role).toList();
    }

    void assertAllStepsUsed() {
        assertTrue(steps.isEmpty(), "호출되지 않은 단계가 남았다: " + steps.stream().map(s -> s.role().id()).toList());
    }
}
