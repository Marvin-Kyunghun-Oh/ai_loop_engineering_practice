package harness.claude;

import harness.policy.Role;
import java.math.BigDecimal;
import java.nio.file.Path;
import java.time.Duration;
import java.util.List;

/**
 * 에이전트 1회 실행 요청 (DESIGN 5.1). {@link ClaudeRunner}가 {@code claude -p} 인자로 바꾼다.
 *
 * @param maxBudgetUsd {@code --max-budget-usd}
 * @param maxTurns     {@code --max-turns}. 없으면 null
 * @param timeout      이 시간을 넘기면 프로세스 트리를 끝내고 TIMEOUT (B2)
 * @param workDir      대상 프로젝트 폴더. 에이전트는 여기서 일한다
 * @param rawLogFile   표준 출력(결과 JSON) 원본을 저장할 파일 (D2)
 */
public record AgentRequest(
        Role role,
        String prompt,
        String model,
        List<String> allowedTools,
        List<String> disallowedTools,
        boolean acceptEdits,
        BigDecimal maxBudgetUsd,
        Integer maxTurns,
        Duration timeout,
        Path workDir,
        Path rawLogFile) {

    public AgentRequest {
        allowedTools = List.copyOf(allowedTools);
        disallowedTools = List.copyOf(disallowedTools);
    }
}
