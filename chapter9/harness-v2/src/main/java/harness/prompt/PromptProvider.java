package harness.prompt;

import harness.policy.Role;

/**
 * 역할별 프롬프트 본문을 만든다.
 *
 * <p>8절 7단계에서 {@code PromptRenderer}가 이 인터페이스를 구현한다.
 * 프롬프트 파일을 읽어 {@code {{변수}}}를 치환하는 방식이다.
 * 그 전까지, 그리고 테스트에서는 람다로 대신한다.
 */
@FunctionalInterface
public interface PromptProvider {

    String promptFor(Role role, int cycle);
}
