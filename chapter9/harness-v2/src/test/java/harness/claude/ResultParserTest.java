package harness.claude;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.io.IOException;
import java.io.InputStream;
import java.io.UncheckedIOException;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.util.List;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

class ResultParserTest {

    private final ResultParser parser = new ResultParser();
    private final ObjectMapper mapper = new ObjectMapper();

    @Nested
    @DisplayName("실제 CLI 출력 샘플")
    class Samples {

        @Test
        @DisplayName("success.json → SUCCESS, 비용·토큰·요약")
        void success() {
            AgentResult result = parser.parse(readSample("success.json"));

            assertEquals(Outcome.SUCCESS, result.outcome());
            assertEquals("success", result.subtype());
            assertEquals(new BigDecimal("0.00271608"), result.costUsd());
            assertEquals(new TokenUsage(2, 12718, 15028, 44), result.usage());
            assertEquals(1, result.numTurns());
            assertEquals(1126, result.durationMs());
            assertEquals(
                    "Hi! What can I help you with today? I can work with code in this directory "
                            + "(it isn't a git repository yet), run commands, or help with files.",
                    result.summary());
            assertEquals(List.of(), result.errors());
        }

        @Test
        @DisplayName("error-max-budget-usd.json → BUDGET_LIMIT, result가 null이면 errors[0]이 요약")
        void budgetLimit() {
            AgentResult result = parser.parse(readSample("error-max-budget-usd.json"));

            assertEquals(Outcome.BUDGET_LIMIT, result.outcome());
            assertEquals("error_max_budget_usd", result.subtype());
            assertEquals(new BigDecimal("0.00196091"), result.costUsd());
            // 이 샘플은 usage가 모두 0이다. modelUsage의 실제 토큰을 써야 한다 (0012).
            assertEquals(new TokenUsage(2, 8324, 17741, 237), result.usage());
            assertEquals(2, result.numTurns());
            assertEquals("Reached maximum budget ($0.001)", result.summary());
            assertEquals(List.of("Reached maximum budget ($0.001)"), result.errors());
        }

        @Test
        @DisplayName("error-max-turns.json → TURN_LIMIT")
        void turnLimit() {
            AgentResult result = parser.parse(readSample("error-max-turns.json"));

            assertEquals(Outcome.TURN_LIMIT, result.outcome());
            assertEquals("error_max_turns", result.subtype());
            assertEquals(new BigDecimal("0.00202051"), result.costUsd());
            assertEquals(new TokenUsage(2, 8307, 17741, 363), result.usage());
            assertEquals("Reached maximum number of turns (1)", result.summary());
        }
    }

    @Nested
    @DisplayName("필수 필드 누락 → INVALID_RESULT (즉시 HALT 대상, 0012)")
    class MissingRequiredField {

        @ParameterizedTest(name = "{0} 없음")
        @ValueSource(strings = {"type", "subtype", "is_error", "total_cost_usd", "usage"})
        void missingFieldIsError(String field) {
            ObjectNode json = successJson();
            json.remove(field);

            AgentResult result = parser.parse(json.toString());

            assertEquals(Outcome.INVALID_RESULT, result.outcome());
            assertTrue(result.summary().contains(field), "요약에 빠진 필드 이름이 있어야 한다: " + result.summary());
        }

        @Test
        @DisplayName("total_cost_usd가 null이어도 누락으로 본다")
        void nullCostIsError() {
            ObjectNode json = successJson();
            json.putNull("total_cost_usd");

            AgentResult result = parser.parse(json.toString());

            assertEquals(Outcome.INVALID_RESULT, result.outcome());
            assertNull(result.costUsd(), "비용을 모르면 0이 아니라 null이어야 한다");
        }

        @Test
        @DisplayName("비용은 있고 다른 필수 필드가 없으면, 비용은 살린다")
        void costIsKeptWhenOtherFieldMissing() {
            ObjectNode json = successJson();
            json.remove("subtype");

            AgentResult result = parser.parse(json.toString());

            assertEquals(Outcome.INVALID_RESULT, result.outcome());
            assertEquals(new BigDecimal("0.00271608"), result.costUsd());
        }
    }

    @Nested
    @DisplayName("JSON 자체가 이상함 → ERROR")
    class BrokenOutput {

        @Test
        @DisplayName("깨진 JSON")
        void brokenJson() {
            AgentResult result = parser.parse("{\"type\": \"result\", ");

            assertEquals(Outcome.ERROR, result.outcome());
            assertNull(result.costUsd());
            assertTrue(result.summary().startsWith("결과 JSON 파싱 실패"), result.summary());
        }

        @Test
        @DisplayName("빈 출력")
        void emptyOutput() {
            AgentResult result = parser.parse("  \n");

            assertEquals(Outcome.ERROR, result.outcome());
            assertEquals("결과 JSON 없음", result.summary());
        }

        @Test
        @DisplayName("null 출력")
        void nullOutput() {
            assertEquals(Outcome.ERROR, parser.parse(null).outcome());
        }

        @Test
        @DisplayName("JSON 배열")
        void notAnObject() {
            assertEquals(Outcome.ERROR, parser.parse("[1, 2]").outcome());
        }
    }

    @Nested
    @DisplayName("판정 규칙 (DESIGN 5.1)")
    class OutcomeRules {

        @Test
        @DisplayName("subtype이 success여도 is_error가 true면 ERROR")
        void successSubtypeWithIsErrorTrue() {
            ObjectNode json = successJson();
            json.put("is_error", true);

            assertEquals(Outcome.ERROR, parser.parse(json.toString()).outcome());
        }

        @Test
        @DisplayName("모르는 error_* subtype → ERROR")
        void unknownErrorSubtype() {
            ObjectNode json = successJson();
            json.put("subtype", "error_during_execution");
            json.put("is_error", true);

            AgentResult result = parser.parse(json.toString());

            assertEquals(Outcome.ERROR, result.outcome());
            assertEquals("error_during_execution", result.subtype());
        }

        @Test
        @DisplayName("api_error_status가 null이 아니면 ERROR")
        void apiErrorStatus() {
            ObjectNode json = successJson();
            json.put("api_error_status", 529);

            assertEquals(Outcome.ERROR, parser.parse(json.toString()).outcome());
        }

        @Test
        @DisplayName("type이 result가 아니면 INVALID_RESULT")
        void typeIsNotResult() {
            ObjectNode json = successJson();
            json.put("type", "assistant");

            assertEquals(Outcome.INVALID_RESULT, parser.parse(json.toString()).outcome());
        }
    }

    @Nested
    @DisplayName("토큰 출처 (0012)")
    class Tokens {

        @Test
        @DisplayName("modelUsage가 여러 모델이면 합산")
        void sumsAllModels() {
            ObjectNode json = successJson();
            ObjectNode other = ((ObjectNode) json.get("modelUsage")).putObject("claude-sonnet-5-5");
            other.put("inputTokens", 10);
            other.put("cacheCreationInputTokens", 20);
            other.put("cacheReadInputTokens", 30);
            other.put("outputTokens", 40);

            assertEquals(new TokenUsage(12, 12738, 15058, 84), parser.parse(json.toString()).usage());
        }

        @Test
        @DisplayName("modelUsage가 없으면 usage를 쓴다")
        void fallsBackToUsage() {
            ObjectNode json = successJson();
            json.remove("modelUsage");

            assertEquals(new TokenUsage(2, 12718, 15028, 44), parser.parse(json.toString()).usage());
        }
    }

    @Nested
    @DisplayName("요약")
    class Summary {

        @Test
        @DisplayName("result가 여러 줄이면 첫 번째 내용 있는 줄만")
        void firstNonBlankLine() {
            ObjectNode json = successJson();
            json.put("result", "\n\nT7b 완료 (258 passed)\n세부 내용은 IMPL.md 참고");

            assertEquals("T7b 완료 (258 passed)", parser.parse(json.toString()).summary());
        }

        @Test
        @DisplayName("result도 errors도 없으면 빈 문자열")
        void nothingToSummarize() {
            ObjectNode json = successJson();
            json.putNull("result");

            assertEquals("", parser.parse(json.toString()).summary());
        }
    }

    // ---- 도우미 ----

    private ObjectNode successJson() {
        try {
            return (ObjectNode) mapper.readTree(readSample("success.json"));
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    private static String readSample(String fileName) {
        String path = "/claude-result/" + fileName;
        try (InputStream in = ResultParserTest.class.getResourceAsStream(path)) {
            if (in == null) {
                throw new IllegalStateException("샘플이 없다: " + path);
            }
            return new String(in.readAllBytes(), StandardCharsets.UTF_8);
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }
}
