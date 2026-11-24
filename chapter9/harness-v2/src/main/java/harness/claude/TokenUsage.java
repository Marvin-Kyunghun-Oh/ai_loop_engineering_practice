package harness.claude;

/**
 * 결과 JSON {@code usage}의 토큰 4종. 분석용이며 상한 판단에는 쓰지 않는다 (0007).
 *
 * <p>캐시 읽기 토큰은 양이 많지만 일반 입력보다 훨씬 싸다. 합계가 아니라 종류별로 본다.
 */
public record TokenUsage(
        long input,
        long cacheCreation,
        long cacheRead,
        long output) {

    public static final TokenUsage ZERO = new TokenUsage(0, 0, 0, 0);
}
