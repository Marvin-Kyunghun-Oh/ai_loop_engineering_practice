package harness.config;

import com.fasterxml.jackson.annotation.JsonProperty;
import harness.policy.Role;
import java.math.BigDecimal;
import java.time.Duration;
import java.util.List;

/**
 * 대상 프로젝트의 {@code harness.yml} (DESIGN 3절).
 *
 * <p>값은 래퍼 타입(Integer, BigDecimal)으로 받는다. YAML에 키가 없으면 null이 되어 "없음"을 구분할 수 있다.
 * {@link ConfigLoader}가 검증을 마친 뒤에는 {@code limits.max_turns}를 빼고 null이 없다.
 */
public record HarnessConfig(
        @JsonProperty("claude") Claude claude,
        @JsonProperty("models") Models models,
        @JsonProperty("limits") Limits limits,
        @JsonProperty("commands") Commands commands,
        @JsonProperty("permissions") Permissions permissions) {

    /** @param path claude 실행 파일. Windows에서 {@code claude}면 claude.cmd를 찾는다 (DESIGN 5.3) */
    public record Claude(
            @JsonProperty("path") String path) {
    }

    /** 역할별 모델 (0006). */
    public record Models(
            @JsonProperty("planner") String planner,
            @JsonProperty("generator") String generator,
            @JsonProperty("evaluator") String evaluator) {

        public String forRole(Role role) {
            return switch (role) {
                case PLANNER -> planner;
                case GENERATOR -> generator;
                case EVALUATOR -> evaluator;
            };
        }
    }

    /**
     * @param maxIterations        한 번 실행에서 시도할 사이클 수
     * @param maxTotalUsd          누적 비용 상한 (0007)
     * @param maxAgentUsd          에이전트 1회 상한. {@code --max-budget-usd}로 넘긴다
     * @param maxTurns             선택. 없으면 null (턴 상한 없음)
     * @param agentTimeoutMin      에이전트 1회 시간 상한(분) (B2)
     * @param backlogPerMilestone  마일스톤 끝에 처리할 BACKLOG 결함 수 (0010)
     * @param maxConsecutiveErrors 실행 오류가 연속 이 횟수면 HALT (B1)
     */
    public record Limits(
            @JsonProperty("max_iterations") Integer maxIterations,
            @JsonProperty("max_total_usd") BigDecimal maxTotalUsd,
            @JsonProperty("max_agent_usd") BigDecimal maxAgentUsd,
            @JsonProperty("max_turns") MaxTurns maxTurns,
            @JsonProperty("agent_timeout_min") Integer agentTimeoutMin,
            @JsonProperty("backlog_per_milestone") Integer backlogPerMilestone,
            @JsonProperty("max_consecutive_errors") Integer maxConsecutiveErrors) {

        /** 역할의 턴 상한. 설정하지 않았으면 null. */
        public Integer maxTurnsFor(Role role) {
            return maxTurns == null ? null : maxTurns.forRole(role);
        }

        public Duration agentTimeout() {
            return Duration.ofMinutes(agentTimeoutMin);
        }
    }

    /** 역할별 턴 상한. 각 값은 선택이다. */
    public record MaxTurns(
            @JsonProperty("planner") Integer planner,
            @JsonProperty("generator") Integer generator,
            @JsonProperty("evaluator") Integer evaluator) {

        public Integer forRole(Role role) {
            return switch (role) {
                case PLANNER -> planner;
                case GENERATOR -> generator;
                case EVALUATOR -> evaluator;
            };
        }
    }

    /** 프롬프트의 {@code {{commands.*}}}로 치환한다 (D3). */
    public record Commands(
            @JsonProperty("test") String test,
            @JsonProperty("test_path") String testPath,
            @JsonProperty("build") String build,
            @JsonProperty("add_dependency") String addDependency) {
    }

    /** 역할별 Bash 허용 패턴 (0008). 예: {@code Bash(./gradlew test:*)} */
    public record Permissions(
            @JsonProperty("generator_bash") List<String> generatorBash,
            @JsonProperty("evaluator_bash") List<String> evaluatorBash) {
    }
}
