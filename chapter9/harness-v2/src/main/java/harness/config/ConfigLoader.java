package harness.config;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.JsonMappingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.exc.UnrecognizedPropertyException;
import com.fasterxml.jackson.dataformat.yaml.YAMLFactory;
import harness.config.HarnessConfig.Claude;
import harness.config.HarnessConfig.Commands;
import harness.config.HarnessConfig.Limits;
import harness.config.HarnessConfig.MaxTurns;
import harness.config.HarnessConfig.Models;
import harness.config.HarnessConfig.Permissions;
import java.io.IOException;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.stream.Collectors;

/**
 * {@code harness.yml}을 읽고 검증한다 (DESIGN 3절, 0012).
 *
 * <ul>
 *   <li>파일이 없으면 거부한다. 기본값으로 조용히 돌지 않는다.</li>
 *   <li>모르는 키가 있으면 거부한다. 오타가 조용히 무시되는 것을 막는다.</li>
 *   <li>빠진 키, 범위를 벗어난 값은 모두 모아서 한 번에 알려 준다.</li>
 * </ul>
 * 선택 키는 {@code limits.max_turns}뿐이다.
 */
public final class ConfigLoader {

    public static final String FILE_NAME = "harness.yml";

    private static final ObjectMapper YAML = new ObjectMapper(new YAMLFactory())
            .enable(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES);

    private ConfigLoader() {
    }

    public static HarnessConfig load(Path file) {
        if (!Files.isRegularFile(file)) {
            throw new ConfigException(FILE_NAME + "이 없다: " + file);
        }

        String text;
        try {
            text = Files.readString(file, StandardCharsets.UTF_8);
        } catch (IOException e) {
            throw new ConfigException(FILE_NAME + "을 읽지 못했다: " + file, e);
        }
        if (text.isBlank()) {
            throw new ConfigException(FILE_NAME + "이 비어 있다: " + file);
        }

        HarnessConfig config;
        try {
            config = YAML.readValue(text, HarnessConfig.class);
        } catch (UnrecognizedPropertyException e) {
            throw new ConfigException(FILE_NAME + "에 모르는 키가 있다: " + keyPath(e), e);
        } catch (JsonMappingException e) {
            String key = keyPath(e);
            String where = key.isEmpty() ? "" : " (" + key + ")";
            throw new ConfigException(FILE_NAME + " 값 오류" + where + ": " + e.getOriginalMessage(), e);
        } catch (JsonProcessingException e) {
            throw new ConfigException(FILE_NAME + " 문법 오류: " + e.getOriginalMessage(), e);
        }

        if (config == null) {   // 주석만 있거나 "~"만 있는 파일
            throw new ConfigException(FILE_NAME + "이 비어 있다: " + file);
        }

        List<String> problems = validate(config);
        if (!problems.isEmpty()) {
            throw new ConfigException(FILE_NAME + " 검증 실패:\n- " + String.join("\n- ", problems));
        }
        return config;
    }

    /** Jackson 예외의 위치를 {@code limits.max_turns.planner} 형태로 만든다. */
    private static String keyPath(JsonMappingException e) {
        return e.getPath().stream()
                .map(ref -> ref.getFieldName() != null ? ref.getFieldName() : "[" + ref.getIndex() + "]")
                .collect(Collectors.joining("."));
    }

    // ---- 검증 ----

    static List<String> validate(HarnessConfig config) {
        List<String> problems = new ArrayList<>();

        Claude claude = config.claude();
        if (claude == null) {
            problems.add("claude가 없다");
        } else {
            requireText(problems, "claude.path", claude.path());
        }

        Models models = config.models();
        if (models == null) {
            problems.add("models가 없다");
        } else {
            requireText(problems, "models.planner", models.planner());
            requireText(problems, "models.generator", models.generator());
            requireText(problems, "models.evaluator", models.evaluator());
        }

        Limits limits = config.limits();
        if (limits == null) {
            problems.add("limits가 없다");
        } else {
            validateLimits(problems, limits);
        }

        Commands commands = config.commands();
        if (commands == null) {
            problems.add("commands가 없다");
        } else {
            requireText(problems, "commands.test", commands.test());
            requireText(problems, "commands.test_path", commands.testPath());
            requireText(problems, "commands.build", commands.build());
            requireText(problems, "commands.add_dependency", commands.addDependency());
            if (commands.testPath() != null && !commands.testPath().contains("{path}")) {
                problems.add("commands.test_path에 {path} 자리표시자가 없다");
            }
        }

        Permissions permissions = config.permissions();
        if (permissions == null) {
            problems.add("permissions가 없다");
        } else {
            validateBashPatterns(problems, "permissions.generator_bash", permissions.generatorBash());
            validateBashPatterns(problems, "permissions.evaluator_bash", permissions.evaluatorBash());
        }

        return problems;
    }

    private static void validateLimits(List<String> problems, Limits limits) {
        requireAtLeast(problems, "limits.max_iterations", limits.maxIterations(), 1);
        requirePositive(problems, "limits.max_total_usd", limits.maxTotalUsd());
        requirePositive(problems, "limits.max_agent_usd", limits.maxAgentUsd());
        requireAtLeast(problems, "limits.agent_timeout_min", limits.agentTimeoutMin(), 1);
        requireAtLeast(problems, "limits.backlog_per_milestone", limits.backlogPerMilestone(), 0);
        requireAtLeast(problems, "limits.max_consecutive_errors", limits.maxConsecutiveErrors(), 1);

        if (limits.maxTotalUsd() != null && limits.maxAgentUsd() != null
                && limits.maxAgentUsd().compareTo(limits.maxTotalUsd()) > 0) {
            problems.add("limits.max_agent_usd(" + limits.maxAgentUsd()
                    + ")가 limits.max_total_usd(" + limits.maxTotalUsd() + ")보다 크다");
        }

        MaxTurns maxTurns = limits.maxTurns();   // 선택 키
        if (maxTurns != null) {
            optionalAtLeast(problems, "limits.max_turns.planner", maxTurns.planner(), 1);
            optionalAtLeast(problems, "limits.max_turns.generator", maxTurns.generator(), 1);
            optionalAtLeast(problems, "limits.max_turns.evaluator", maxTurns.evaluator(), 1);
        }
    }

    /** 0008의 허용 패턴 형식 {@code Bash(명령:*)}. 목록은 비어 있어도 된다. */
    private static void validateBashPatterns(List<String> problems, String key, List<String> patterns) {
        if (patterns == null) {
            problems.add(key + "가 없다 (허용할 명령이 없으면 [] 로 쓴다)");
            return;
        }
        for (int i = 0; i < patterns.size(); i++) {
            String pattern = patterns.get(i);
            if (pattern == null || !pattern.startsWith("Bash(") || !pattern.endsWith(")")) {
                problems.add(key + "[" + i + "]가 Bash(...) 형식이 아니다: " + pattern);
            }
        }
    }

    private static void requireText(List<String> problems, String key, String value) {
        if (value == null || value.isBlank()) {
            problems.add(key + "가 없다");
        }
    }

    private static void requireAtLeast(List<String> problems, String key, Integer value, int min) {
        if (value == null) {
            problems.add(key + "가 없다");
        } else if (value < min) {
            problems.add(key + "는 " + min + " 이상이어야 한다: " + value);
        }
    }

    private static void optionalAtLeast(List<String> problems, String key, Integer value, int min) {
        if (value != null && value < min) {
            problems.add(key + "는 " + min + " 이상이어야 한다: " + value);
        }
    }

    private static void requirePositive(List<String> problems, String key, BigDecimal value) {
        if (value == null) {
            problems.add(key + "가 없다");
        } else if (value.signum() <= 0) {
            problems.add(key + "는 0보다 커야 한다: " + value);
        }
    }
}
