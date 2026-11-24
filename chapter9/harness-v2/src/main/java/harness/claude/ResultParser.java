package harness.claude;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Objects;

/**
 * {@code claude -p --output-format json}의 표준 출력을 {@link AgentResult}로 바꾼다 (DESIGN 5.1).
 *
 * <p>판정 순서
 * <ol>
 *   <li>출력이 비었거나 JSON 객체가 아니면 → ERROR</li>
 *   <li>필수 필드({@code type}, {@code subtype}, {@code is_error}, {@code total_cost_usd}, {@code usage})가
 *       없거나 null이면 → INVALID_RESULT. 비용을 0으로 채우지 않는다 (0007, 0012)</li>
 *   <li>{@code type}이 {@code result}가 아니면 → INVALID_RESULT</li>
 *   <li>{@code api_error_status}가 null이 아니면 → ERROR</li>
 *   <li>{@code subtype}으로 분류: success(+is_error false) → SUCCESS,
 *       error_max_budget_usd → BUDGET_LIMIT, error_max_turns → TURN_LIMIT, 그 밖 → ERROR</li>
 * </ol>
 *
 * <p>토큰은 {@code modelUsage}의 모델별 값을 합산한다. 없으면 {@code usage}를 쓴다.
 * 예산 상한에 걸린 실행은 {@code usage}가 0으로 나오기 때문이다 (0012).
 *
 * <p>모르는 필드는 무시한다. CLI는 버전마다 필드를 더하기 때문이다.
 */
public final class ResultParser {

    private static final ObjectMapper MAPPER = new ObjectMapper()
            .disable(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES)
            // 0.00271608 같은 비용을 double을 거치지 않고 BigDecimal로 읽는다.
            .enable(DeserializationFeature.USE_BIG_DECIMAL_FOR_FLOATS);

    public AgentResult parse(String stdout) {
        if (stdout == null || stdout.isBlank()) {
            return AgentResult.failure(Outcome.ERROR, "결과 JSON 없음");
        }

        ResultJson json;
        try {
            JsonNode tree = MAPPER.readTree(stdout);
            if (!tree.isObject()) {
                return AgentResult.failure(Outcome.ERROR, "결과 JSON 파싱 실패: JSON 객체가 아니다");
            }
            json = MAPPER.treeToValue(tree, ResultJson.class);
        } catch (JsonProcessingException e) {
            return AgentResult.failure(Outcome.ERROR, "결과 JSON 파싱 실패: " + e.getOriginalMessage());
        }

        List<String> errors = json.errors() == null
                ? List.of()
                : json.errors().stream().filter(Objects::nonNull).toList();
        TokenUsage usage = tokenUsage(json);

        Verdict verdict = judge(json, errors);

        return new AgentResult(
                verdict.outcome(),
                json.subtype(),
                json.totalCostUsd(),   // 다른 필드가 빠져도 비용을 알면 살린다
                usage,
                json.numTurns(),
                json.durationMs(),
                verdict.summary(),
                errors);
    }

    private Verdict judge(ResultJson json, List<String> errors) {
        List<String> missing = missingRequiredFields(json);
        if (!missing.isEmpty()) {
            return new Verdict(Outcome.INVALID_RESULT, "결과 JSON 필수 필드 누락: " + String.join(", ", missing));
        }
        if (!"result".equals(json.type())) {
            return new Verdict(Outcome.INVALID_RESULT, "결과 JSON의 type이 result가 아니다: " + json.type());
        }

        String summary = summarize(json.result(), errors);

        if (json.hasApiError()) {
            String fallback = "API 오류 (status " + json.apiErrorStatus() + ")";
            return new Verdict(Outcome.ERROR, summary.isEmpty() ? fallback : summary);
        }

        Outcome outcome = switch (json.subtype()) {
            case "success" -> json.isError() ? Outcome.ERROR : Outcome.SUCCESS;
            case "error_max_budget_usd" -> Outcome.BUDGET_LIMIT;
            case "error_max_turns" -> Outcome.TURN_LIMIT;
            default -> Outcome.ERROR;
        };
        return new Verdict(outcome, summary);
    }

    private static List<String> missingRequiredFields(ResultJson json) {
        List<String> missing = new ArrayList<>();
        if (json.type() == null) {
            missing.add("type");
        }
        if (json.subtype() == null) {
            missing.add("subtype");
        }
        if (json.isError() == null) {
            missing.add("is_error");
        }
        if (json.totalCostUsd() == null) {
            missing.add("total_cost_usd");
        }
        if (json.usage() == null) {
            missing.add("usage");
        }
        return missing;
    }

    /** {@code modelUsage}의 모델별 토큰 합. 비어 있으면 {@code usage}, 그것도 없으면 0. */
    private static TokenUsage tokenUsage(ResultJson json) {
        if (json.modelUsage() != null && !json.modelUsage().isEmpty()) {
            long input = 0;
            long cacheCreation = 0;
            long cacheRead = 0;
            long output = 0;
            for (ModelUsageJson model : json.modelUsage().values()) {
                input += model.inputTokens();
                cacheCreation += model.cacheCreationInputTokens();
                cacheRead += model.cacheReadInputTokens();
                output += model.outputTokens();
            }
            return new TokenUsage(input, cacheCreation, cacheRead, output);
        }
        if (json.usage() != null) {
            return json.usage().toTokenUsage();
        }
        return TokenUsage.ZERO;
    }

    /** {@code result}의 첫 번째 내용 있는 줄. 없으면 {@code errors[0]}. 둘 다 없으면 빈 문자열. */
    private static String summarize(String result, List<String> errors) {
        if (result != null) {
            String firstLine = result.lines()
                    .map(String::strip)
                    .filter(line -> !line.isEmpty())
                    .findFirst()
                    .orElse("");
            if (!firstLine.isEmpty()) {
                return firstLine;
            }
        }
        if (!errors.isEmpty()) {
            return errors.getFirst();
        }
        return "";
    }

    private record Verdict(Outcome outcome, String summary) {
    }

    // ---- 결과 JSON의 모양 (필요한 필드만) ----

    /** 결과 JSON 최상위. 래퍼 타입(Boolean, BigDecimal)은 "없음"을 null로 구분하기 위해서다. */
    @JsonIgnoreProperties(ignoreUnknown = true)
    record ResultJson(
            @JsonProperty("type") String type,
            @JsonProperty("subtype") String subtype,
            @JsonProperty("is_error") Boolean isError,
            @JsonProperty("total_cost_usd") BigDecimal totalCostUsd,
            @JsonProperty("usage") UsageJson usage,
            @JsonProperty("modelUsage") Map<String, ModelUsageJson> modelUsage,
            @JsonProperty("num_turns") int numTurns,
            @JsonProperty("duration_ms") long durationMs,
            @JsonProperty("result") String result,
            @JsonProperty("errors") List<String> errors,
            @JsonProperty("api_error_status") JsonNode apiErrorStatus) {

        boolean hasApiError() {
            return apiErrorStatus != null && !apiErrorStatus.isNull();
        }
    }

    /** {@code usage}. 토큰은 분석용이라 빠진 항목은 0으로 둔다. */
    @JsonIgnoreProperties(ignoreUnknown = true)
    record UsageJson(
            @JsonProperty("input_tokens") long inputTokens,
            @JsonProperty("cache_creation_input_tokens") long cacheCreationInputTokens,
            @JsonProperty("cache_read_input_tokens") long cacheReadInputTokens,
            @JsonProperty("output_tokens") long outputTokens) {

        TokenUsage toTokenUsage() {
            return new TokenUsage(inputTokens, cacheCreationInputTokens, cacheReadInputTokens, outputTokens);
        }
    }

    /** {@code modelUsage.{모델}}. 이름이 camelCase인 점이 {@code usage}와 다르다. */
    @JsonIgnoreProperties(ignoreUnknown = true)
    record ModelUsageJson(
            @JsonProperty("inputTokens") long inputTokens,
            @JsonProperty("cacheCreationInputTokens") long cacheCreationInputTokens,
            @JsonProperty("cacheReadInputTokens") long cacheReadInputTokens,
            @JsonProperty("outputTokens") long outputTokens) {
    }
}
