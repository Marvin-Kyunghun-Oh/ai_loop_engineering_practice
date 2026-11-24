package harness.claude;

/**
 * {@code claude} CLI 실행기 (DESIGN 5.1).
 *
 * <p>실제 구현은 {@code ProcessClaudeRunner}(8절 6단계)다.
 * 테스트에서는 가짜 실행기가 미리 정한 결과를 돌려준다. 그래서 크레딧 없이 루프 전체를 검증할 수 있다 (D4).
 */
public interface ClaudeRunner {

    /** 대화형이 아닌 실행({@code claude -p}). 실패해도 예외 대신 ERROR·TIMEOUT 결과를 돌려준다. */
    AgentResult run(AgentRequest request);

    /** 부트스트랩 전용 대화형 실행. 사용자가 대화를 마칠 때까지 기다린다. */
    void runInteractive(AgentRequest request);
}
