package harness.prompt;

import harness.policy.Role;

/**
 * 역할별 프롬프트 본문을 만든다.
 *
 * <p>실제 구현은 {@link PromptRenderer}다. 프롬프트 파일을 읽어 {@code {{변수}}}를 치환한다.
 * {@code Harness} 테스트에서는 람다로 대신한다.
 */
@FunctionalInterface
public interface PromptProvider {

    String promptFor(Role role, int cycle);

    /** 대화형 부트스트랩(PRD 작성)의 시스템 프롬프트. {@link PromptRenderer}만 구현한다. */
    default String bootstrapPrompt() {
        throw new UnsupportedOperationException("부트스트랩 프롬프트를 제공하지 않는다");
    }
}
