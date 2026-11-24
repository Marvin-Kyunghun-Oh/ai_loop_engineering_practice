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
}
