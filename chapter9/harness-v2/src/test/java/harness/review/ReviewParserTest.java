package harness.review;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.Optional;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

class ReviewParserTest {

    private static final String FULL = """
            판정: PASS 11/12
            핵심 결정: 버리기 깊이는 태그별로 센다
            메모:
            - [결함] html_to_text가 짝 없는 끝 태그에서 깊이를 음수로 만들 수 있다
            - [보강] 블록 태그 목록을 테스트 리터럴로 고정

            평가 대상: T8r · 사이클 35 · 2026-11-24T12:26:46+09:00

            ## 평가 표
            """;

    @Test
    @DisplayName("4.2 블록의 판정, 핵심 결정, 평가 대상을 읽는다")
    void fullBlock() {
        ReviewBlock block = ReviewParser.parse(FULL).orElseThrow();

        assertEquals("PASS 11/12", block.verdict());
        assertEquals("버리기 깊이는 태그별로 센다", block.keyDecision());
        assertEquals("T8r", block.taskId());
        assertEquals(35, block.cycle());
    }

    @Test
    @DisplayName("판정 값은 PASS, 조건부, FAIL")
    void verdictKinds() {
        assertEquals("조건부 7/12", ReviewParser.parse("판정: 조건부 7/12\n").orElseThrow().verdict());
        assertEquals("FAIL 3/15", ReviewParser.parse("판정: FAIL 3/15\n").orElseThrow().verdict());
    }

    @Test
    @DisplayName("핵심 결정이 없거나 비어 있으면 -")
    void keyDecisionDefault() {
        assertEquals("-", ReviewParser.parse("판정: PASS 9/9\n").orElseThrow().keyDecision());
        assertEquals("-", ReviewParser.parse("판정: PASS 9/9\n핵심 결정:\n").orElseThrow().keyDecision());
        assertEquals("-", ReviewParser.parse("판정: PASS 9/9\n핵심 결정: -\n").orElseThrow().keyDecision());
    }

    @Test
    @DisplayName("평가 대상 줄이 없으면 항목 ID와 사이클은 null")
    void noTarget() {
        ReviewBlock block = ReviewParser.parse("판정: PASS 9/9\n").orElseThrow();

        assertNull(block.taskId());
        assertNull(block.cycle());
    }

    @Test
    @DisplayName("맨 위에 제목이 있어도 앞쪽 20줄 안이면 읽는다")
    void titleBeforeBlock() {
        assertTrue(ReviewParser.parse("# REVIEW\n\n판정: PASS 9/9\n").isPresent());
    }

    @Test
    @DisplayName("판정 줄이 없거나 값이 이상하면 읽지 못한 것이다")
    void unreadable() {
        assertEquals(Optional.empty(), ReviewParser.parse(""));
        assertEquals(Optional.empty(), ReviewParser.parse("# REVIEW\n- 평가 대상: T1\n"));
        assertEquals(Optional.empty(), ReviewParser.parse("판정: 합격 9/9\n"));
        assertEquals(Optional.empty(), ReviewParser.parse("판정:\n"));
    }

    @Test
    @DisplayName("20줄 밖의 판정 줄은 본문으로 보고 무시한다")
    void beyondScanLimit() {
        String text = "x\n".repeat(ReviewParser.SCAN_LINES) + "판정: PASS 1/1\n";

        assertEquals(Optional.empty(), ReviewParser.parse(text));
    }
}
