package harness.prompt;

import harness.config.HarnessConfig;
import harness.decision.DecisionResolver;
import harness.policy.Role;
import harness.state.ProjectFiles;
import harness.state.Timestamps;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.time.Clock;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

/**
 * 프롬프트 파일({@code src/main/resources/prompts/*.md})의 {@code {{변수}}}를 치환한다 (DESIGN 5.6, D3).
 *
 * <p>모르는 변수가 있으면 예외를 던진다. 치환되지 않은 {@code {{...}}}가 에이전트에게 그대로 가는 일을 막는다.
 *
 * <p>변수 목록
 * <ul>
 *   <li>{@code commands.test}, {@code commands.test_path}, {@code commands.build}, {@code commands.add_dependency}</li>
 *   <li>{@code limits.backlog_per_milestone}</li>
 *   <li>{@code cycle.number}: 사이클 번호</li>
 *   <li>{@code cycle.now}: 프롬프트를 만든 시각(에이전트 실행 직전). 에이전트가 문서에 날짜를 적을 때 쓴다</li>
 *   <li>{@code decisions.awaiting_choice}: 이 역할의 선택이 아직 없는 결정 주제 목록(0017). 역할 프롬프트에만 있다. 없으면 "없음"</li>
 * </ul>
 */
public final class PromptRenderer implements PromptProvider {

    /** {@code {{a.b}}}. 이름 앞뒤 공백은 허용한다. */
    private static final Pattern VARIABLE = Pattern.compile("\\{\\{([^{}]*)}}");

    private static final String RESOURCE_DIR = "/prompts/";

    private final HarnessConfig config;
    private final ProjectFiles files;
    private final Clock clock;

    public PromptRenderer(HarnessConfig config, ProjectFiles files, Clock clock) {
        this.config = config;
        this.files = files;
        this.clock = clock;
    }

    @Override
    public String promptFor(Role role, int cycle) {
        String fileName = role.id() + ".md";
        Map<String, String> variables = variables(cycle);
        variables.put("decisions.awaiting_choice", awaitingChoice(role));
        return render(fileName, loadTemplate(fileName), variables);
    }

    @Override
    public String bootstrapPrompt() {
        return render("planner_bootstrap.md", loadTemplate("planner_bootstrap.md"), variables(0));
    }

    /**
     * 세 역할과 부트스트랩의 프롬프트를 한 번씩 만들어 본다. 하네스 시작 때 불러, 비용을 쓰기 전에 템플릿 오류를 찾는다.
     *
     * @throws PromptException 프롬프트 파일이 없거나 모르는 변수가 있을 때
     */
    public void checkTemplates() {
        for (Role role : Role.values()) {
            promptFor(role, 1);
        }
        bootstrapPrompt();
    }

    /** 템플릿의 변수를 모두 치환한다. 모르는 변수는 모아서 한 번에 알려 준다. */
    static String render(String templateName, String template, Map<String, String> variables) {
        List<String> unknown = new ArrayList<>();
        StringBuilder result = new StringBuilder();
        Matcher matcher = VARIABLE.matcher(template);
        while (matcher.find()) {
            String name = matcher.group(1).strip();
            String value = variables.get(name);
            if (value == null) {
                unknown.add(name);
                value = matcher.group();
            }
            // 값에 $나 \가 있어도 그대로 넣는다.
            matcher.appendReplacement(result, Matcher.quoteReplacement(value));
        }
        matcher.appendTail(result);

        if (!unknown.isEmpty()) {
            throw new PromptException(templateName + "에 모르는 변수가 있다: " + String.join(", ", unknown)
                    + " (사용할 수 있는 변수: " + String.join(", ", variables.keySet()) + ")");
        }
        // "{{" 뒤에 짝이 되는 "}}"가 없는 경우. 위 패턴에 걸리지 않으므로 따로 검사한다.
        String withoutVariables = VARIABLE.matcher(template).replaceAll("");
        if (withoutVariables.contains("{{")) {
            throw new PromptException(templateName + "에 닫히지 않은 {{가 있다");
        }
        return result.toString();
    }

    /**
     * 이 역할이 아직 선택하지 않은 결정 주제를 프롬프트에 넣을 줄로 만든다. 없으면 "없음".
     * 에이전트가 {@code docs/decisions/}를 열어 보지 않아 절차를 놓치는 일을 막는다(0017).
     */
    private String awaitingChoice(Role role) {
        Path decisionsDir = files.decisionsDir();
        List<String> topics = DecisionResolver.topicsAwaitingChoice(decisionsDir, role);
        if (topics.isEmpty()) {
            return "없음";
        }
        return topics.stream()
                .map(topic -> "- " + topic + ": docs/decisions/" + topic + ".md를 읽고 docs/decisions/"
                        + DecisionResolver.choiceFile(decisionsDir, topic, role).getFileName() + "에 선택을 기록한다")
                .collect(Collectors.joining(System.lineSeparator()));
    }

    private Map<String, String> variables(int cycle) {
        HarnessConfig.Commands commands = config.commands();
        Map<String, String> variables = new LinkedHashMap<>();
        variables.put("commands.test", commands.test());
        variables.put("commands.test_path", commands.testPath());
        variables.put("commands.build", commands.build());
        variables.put("commands.add_dependency", commands.addDependency());
        variables.put("limits.backlog_per_milestone", String.valueOf(config.limits().backlogPerMilestone()));
        variables.put("cycle.number", String.valueOf(cycle));
        variables.put("cycle.now", Timestamps.now(clock));
        return variables;
    }

    static String loadTemplate(String fileName) {
        String resource = RESOURCE_DIR + fileName;
        try (InputStream in = PromptRenderer.class.getResourceAsStream(resource)) {
            if (in == null) {
                throw new PromptException("프롬프트 파일이 없다: " + resource);
            }
            return new String(in.readAllBytes(), StandardCharsets.UTF_8);
        } catch (IOException e) {
            throw new PromptException("프롬프트 파일을 읽지 못했다: " + resource, e);
        }
    }
}
