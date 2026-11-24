package harness.review;

/** {@code .harness/reviews.csv}의 한 줄. 항목 하나를 평가한 결과다. */
public record ReviewRecord(String taskId, int cycle, String verdict, String keyDecision) {
}
