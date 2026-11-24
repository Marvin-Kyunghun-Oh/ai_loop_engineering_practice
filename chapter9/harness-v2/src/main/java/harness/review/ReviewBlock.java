package harness.review;

/**
 * REVIEW.md 맨 위의 기계 판독 블록 (DESIGN 4.2).
 *
 * @param verdict     {@code 판정:} 값. 예: {@code PASS 11/12}
 * @param keyDecision {@code 핵심 결정:} 값. 없으면 {@code -}
 * @param taskId      {@code 평가 대상:} 줄의 항목 ID. 줄이 없으면 null
 * @param cycle       {@code 평가 대상:} 줄의 사이클 번호. 줄이 없으면 null
 */
public record ReviewBlock(String verdict, String keyDecision, String taskId, Integer cycle) {
}
