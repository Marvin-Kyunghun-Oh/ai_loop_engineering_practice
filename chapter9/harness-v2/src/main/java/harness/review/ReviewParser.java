package harness.review;

import java.util.List;
import java.util.Optional;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * REVIEW.md의 맨 위 블록을 읽는다 (DESIGN 4.2).
 *
 * <pre>
 * 판정: PASS 11/12
 * 핵심 결정: 버리기 깊이는 태그별로 센다
 * 메모:
 * - [결함] ...
 *
 * 평가 대상: T8r · 사이클 35 · 2026-11-24T12:26:46+09:00
 * </pre>
 *
 * 에이전트가 맨 위에 제목을 붙였을 때를 대비해 앞쪽 {@value #SCAN_LINES}줄 안에서 찾는다.
 * {@code 판정:}이 없거나 값이 {@code PASS}·{@code 조건부}·{@code FAIL}로 시작하지 않으면 읽지 못한 것으로 본다.
 */
public final class ReviewParser {

    static final int SCAN_LINES = 20;

    private static final Pattern VERDICT = Pattern.compile("^(PASS|조건부|FAIL)(\\s.*)?$");
    private static final Pattern TARGET =
            Pattern.compile("^평가 대상:\\s*(T\\d+[a-z]*)\\s*·\\s*사이클\\s*(\\d+)\\b.*$");

    private ReviewParser() {
    }

    public static Optional<ReviewBlock> parse(String reviewText) {
        List<String> head = reviewText.lines().limit(SCAN_LINES).map(String::strip).toList();

        String verdict = null;
        String keyDecision = "-";
        String taskId = null;
        Integer cycle = null;

        for (String line : head) {
            if (verdict == null && line.startsWith("판정:")) {
                verdict = line.substring("판정:".length()).strip();
            } else if (line.startsWith("핵심 결정:")) {
                String value = line.substring("핵심 결정:".length()).strip();
                keyDecision = value.isEmpty() ? "-" : value;
            } else if (taskId == null) {
                Matcher target = TARGET.matcher(line);
                if (target.matches()) {
                    taskId = target.group(1);
                    cycle = Integer.valueOf(target.group(2));
                }
            }
        }

        if (verdict == null || !VERDICT.matcher(verdict).matches()) {
            return Optional.empty();
        }
        return Optional.of(new ReviewBlock(verdict, keyDecision, taskId, cycle));
    }
}
