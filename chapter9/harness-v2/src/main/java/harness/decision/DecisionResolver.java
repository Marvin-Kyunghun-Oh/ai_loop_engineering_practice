package harness.decision;

import harness.policy.Role;
import harness.state.HaltNotice;
import harness.state.ProjectFiles;
import harness.state.TextFiles;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.stream.Stream;

/**
 * 블라인드 결정 합의 (DESIGN 5.7). v1 {@code resolve_decisions}({@code run.py:118-149})를 그대로 옮겼다.
 *
 * <p>{@code docs/decisions/}의 주제마다 다음 세 파일을 본다.
 * <ul>
 *   <li>{@code {주제}.md}: 주제와 후보. 하네스가 합의 결과와 재시도 안내를 여기에 덧붙인다</li>
 *   <li>{@code {주제}.planner.md}, {@code {주제}.evaluator.md}: 각자 독립적으로 쓴 선택. 첫 줄은 {@code 선택: {라벨}}</li>
 * </ul>
 *
 * <p>두 선택이 모두 있으면 비교한다.
 * <ul>
 *   <li>같으면 {@code 합의: {라벨} (시도 N회)}를 추가한다.</li>
 *   <li>다르면 {@code 합의 불발} 안내를 추가해 다시 하게 한다. {@value #MAX_TRIES}회째에도 다르면 HALT한다.</li>
 *   <li>판정한 뒤에는 두 선택 파일을 지운다. 다음 시도도 블라인드로 시작하게 하기 위해서다.</li>
 *   <li>한쪽만 있거나 첫 줄 형식이 틀리면 아직 기록하지 않은 것으로 보고 기다린다.</li>
 * </ul>
 */
public final class DecisionResolver {

    public static final int MAX_TRIES = 3;

    static final String CHOICE_PREFIX = "선택:";
    static final String FAILED_MARK = "합의 불발";
    static final String AGREED_PREFIX = "합의:";

    private static final String RETRY_GUIDE =
            "합의 불발. 후보를 처음부터 다시 나열하고 장단점을 비교한 뒤 결정하라.";

    private final ProjectFiles files;

    public DecisionResolver(ProjectFiles files) {
        this.files = files;
    }

    /**
     * 모든 주제를 판정한다.
     *
     * @param cycle HALT를 쓸 때 적는 사이클 번호
     * @return 콘솔에 보여 줄 메시지. 판정할 것이 없으면 빈 목록
     */
    public List<String> resolve(int cycle) {
        Path dir = files.decisionsDir();
        if (!Files.isDirectory(dir)) {
            return List.of();
        }

        List<String> messages = new ArrayList<>();
        for (String topic : listTopics(dir)) {
            resolveTopic(dir, topic, cycle, messages);
            if (files.isHalted()) {
                break;   // v1은 HALT를 쓰고도 다음 주제를 계속 봤지만, HALT가 있으면 사람이 먼저 봐야 한다
            }
        }
        return messages;
    }

    private void resolveTopic(Path dir, String topic, int cycle, List<String> messages) {
        Path topicFile = dir.resolve(topic + ".md");
        Path plannerFile = dir.resolve(topic + ".planner.md");
        Path evaluatorFile = dir.resolve(topic + ".evaluator.md");

        Optional<String> plannerChoice = readChoice(plannerFile);
        Optional<String> evaluatorChoice = readChoice(evaluatorFile);
        if (plannerChoice.isEmpty() || evaluatorChoice.isEmpty()) {
            return;   // 아직 한쪽이 기록하지 않았다
        }

        String text = TextFiles.read(topicFile);
        int tries = countOccurrences(text, FAILED_MARK) + 1;

        if (plannerChoice.get().equals(evaluatorChoice.get())) {
            TextFiles.write(topicFile, text + "\n합의: " + plannerChoice.get() + " (시도 " + tries + "회)\n");
            messages.add("결정 합의: " + topic + " → " + plannerChoice.get());
        } else if (tries >= MAX_TRIES) {
            files.writeHalt(new HaltNotice(
                    "결정 합의 " + MAX_TRIES + "회 불발: " + topic,
                    "planner와 evaluator의 선택이 달랐다.\n\n"
                            + "[planner]\n" + TextFiles.read(plannerFile).strip() + "\n\n"
                            + "[evaluator]\n" + TextFiles.read(evaluatorFile).strip(),
                    cycle, null,
                    "docs/decisions/" + topic + ".md에 사람이 결정을 적고 이 파일을 지운다"));
            messages.add("결정 합의 불발로 HALT: " + topic);
        } else {
            TextFiles.write(topicFile, text + "\n" + RETRY_GUIDE + "\n");
            messages.add("결정 합의 불발(" + tries + "회): " + topic + " - 재시도");
        }

        // 선택 파일을 지워 다음 시도도 블라인드로 시작한다.
        TextFiles.deleteIfExists(plannerFile);
        TextFiles.deleteIfExists(evaluatorFile);
    }

    /**
     * 주제 {@code topic}의 선택 파일 경로. 프롬프트가 에이전트에게 알려 줄 때 쓴다.
     *
     * @param role {@link Role#PLANNER} 또는 {@link Role#EVALUATOR}
     */
    public static Path choiceFile(Path decisionsDir, String topic, Role role) {
        return decisionsDir.resolve(topic + "." + role.id() + ".md");
    }

    /**
     * 아직 {@code role}의 선택이 기록되지 않은 주제를 이름순으로 돌려준다. 이미 합의된 주제는 뺀다.
     *
     * <p>에이전트가 {@code docs/decisions/}를 스스로 열어 보지 않으면 결정 절차가 시작되지 않는다
     * (loop-check c7, c8의 evaluator). 그래서 하네스가 프롬프트에 이 목록을 넣어 준다.
     * 상대편의 선택 내용은 알려 주지 않는다. 블라인드를 지키기 위해 주제 이름만 쓴다.
     *
     * @param role {@link Role#PLANNER} 또는 {@link Role#EVALUATOR}. 다른 역할은 선택하지 않으므로 빈 목록
     */
    public static List<String> topicsAwaitingChoice(Path decisionsDir, Role role) {
        if ((role != Role.PLANNER && role != Role.EVALUATOR) || !Files.isDirectory(decisionsDir)) {
            return List.of();
        }
        return listTopics(decisionsDir).stream()
                .filter(topic -> !isAgreed(decisionsDir.resolve(topic + ".md")))
                .filter(topic -> readChoice(choiceFile(decisionsDir, topic, role)).isEmpty())
                .toList();
    }

    /** 주제 파일에 {@code 합의: {라벨}} 줄이 있으면 이미 정해진 주제다. "합의 불발" 줄은 해당하지 않는다. */
    private static boolean isAgreed(Path topicFile) {
        return TextFiles.read(topicFile).lines().anyMatch(line -> line.strip().startsWith(AGREED_PREFIX));
    }

    /** {@code {주제}.md} 중 선택 파일({@code .planner.md}, {@code .evaluator.md})이 아닌 것의 주제 이름. 이름순. */
    private static List<String> listTopics(Path dir) {
        try (Stream<Path> entries = Files.list(dir)) {
            return entries
                    .map(path -> path.getFileName().toString())
                    .filter(name -> name.endsWith(".md"))
                    .filter(name -> !name.endsWith(".planner.md") && !name.endsWith(".evaluator.md"))
                    .map(name -> name.substring(0, name.length() - ".md".length()))
                    .sorted()
                    .toList();
        } catch (IOException e) {
            throw new UncheckedIOException("결정 폴더를 읽지 못했다: " + dir, e);
        }
    }

    /** 선택 파일의 첫 줄 {@code 선택: {라벨}}에서 라벨을 읽는다. 파일이 없거나 형식이 어긋나면 empty(미기록 취급). */
    static Optional<String> readChoice(Path file) {
        if (!Files.exists(file)) {
            return Optional.empty();
        }
        String first = TextFiles.read(file).strip().lines().findFirst().orElse("");
        if (!first.startsWith(CHOICE_PREFIX)) {
            return Optional.empty();
        }
        String label = first.substring(CHOICE_PREFIX.length()).strip();
        return label.isEmpty() ? Optional.empty() : Optional.of(label);   // 라벨이 비면 v1과 달리 미기록 취급
    }

    private static int countOccurrences(String text, String word) {
        int count = 0;
        for (int from = text.indexOf(word); from >= 0; from = text.indexOf(word, from + word.length())) {
            count++;
        }
        return count;
    }
}
