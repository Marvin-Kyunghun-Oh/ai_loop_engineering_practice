package harness.state;

import harness.policy.Role;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Optional;
import java.util.regex.Pattern;

/**
 * 대상 프로젝트 안의 파일 위치와, 하네스가 직접 읽고 쓰는 신호 파일(DONE, HALT, CURRENT, .cycle_count).
 * 위치는 DESIGN 2절의 "대상 프로젝트" 구조를 따른다.
 */
public final class ProjectFiles {

    /** 4.1의 항목 ID 형식. 예: {@code T9}, {@code T9a}, {@code T8rs} */
    private static final Pattern TASK_ID = Pattern.compile("^T\\d+[a-z]*$");

    private final Path root;

    public ProjectFiles(Path projectDir) {
        this.root = projectDir.toAbsolutePath().normalize();
    }

    // ---- 위치 ----

    public Path root() {
        return root;
    }

    public Path harnessYml() {
        return root.resolve("harness.yml");
    }

    public Path docs() {
        return root.resolve("docs");
    }

    public Path prd() {
        return docs().resolve("PRD.md");
    }

    public Path tasks() {
        return docs().resolve("TASKS.md");
    }

    public Path review() {
        return docs().resolve("REVIEW.md");
    }

    public Path journal() {
        return docs().resolve("JOURNAL.md");
    }

    public Path backlog() {
        return docs().resolve("BACKLOG.md");
    }

    public Path usageCsv() {
        return docs().resolve("USAGE.csv");
    }

    public Path decisionsDir() {
        return docs().resolve("decisions");
    }

    public Path archiveDir() {
        return docs().resolve("archive");
    }

    public Path current() {
        return docs().resolve("CURRENT");
    }

    public Path done() {
        return docs().resolve("DONE");
    }

    public Path halt() {
        return docs().resolve("HALT");
    }

    public Path cycleCount() {
        return docs().resolve(".cycle_count");
    }

    /** 에이전트가 Glob으로 훑지 않도록 docs/ 밖에 둔다 (DESIGN 2절). */
    public Path harnessDir() {
        return root.resolve(".harness");
    }

    public Path logsDir() {
        return harnessDir().resolve("logs");
    }

    public Path reviewsCsv() {
        return harnessDir().resolve("reviews.csv");
    }

    public void createDirectories() {
        try {
            Files.createDirectories(docs());
            Files.createDirectories(logsDir());
        } catch (IOException e) {
            throw new UncheckedIOException("폴더를 만들지 못했다: " + root, e);
        }
    }

    // ---- 사이클 번호 ----

    /** 정상 완료한 마지막 사이클 번호. 파일이 없으면 0. */
    public int readCycleCount() {
        if (!Files.exists(cycleCount())) {
            return 0;
        }
        String text = TextFiles.read(cycleCount()).strip();
        try {
            return Integer.parseInt(text);
        } catch (NumberFormatException e) {
            // v1은 0으로 되돌렸다. 그러면 사이클 번호가 c1부터 다시 시작해 JOURNAL·로그가 뒤섞인다.
            throw new IllegalStateException(".cycle_count를 숫자로 읽을 수 없다: \"" + text + "\" (" + cycleCount() + ")");
        }
    }

    public void saveCycleCount(int cycle) {
        TextFiles.write(cycleCount(), Integer.toString(cycle));
    }

    // ---- DONE / HALT ----

    public boolean isDone() {
        return Files.exists(done());
    }

    public void deleteDone() {
        TextFiles.deleteIfExists(done());
    }

    public boolean isHalted() {
        return Files.exists(halt());
    }

    public void writeHalt(HaltNotice notice) {
        TextFiles.write(halt(), notice.toText());
    }

    // ---- CURRENT (4.1) ----

    /** CURRENT의 첫 번째 내용 있는 줄. 파일이 없거나 비었으면 empty. 형식 검사는 {@link #isValidTaskId}로 한다. */
    public Optional<String> readCurrent() {
        if (!Files.exists(current())) {
            return Optional.empty();
        }
        return TextFiles.read(current()).lines()
                .map(String::strip)
                .filter(line -> !line.isEmpty())
                .findFirst();
    }

    public void deleteCurrent() {
        TextFiles.deleteIfExists(current());
    }

    public static boolean isValidTaskId(String id) {
        return id != null && TASK_ID.matcher(id).matches();
    }

    // ---- 원본 로그 (D2) ----

    /**
     * 이번 실행의 원본 결과 JSON을 저장할 경로. 예: {@code .harness/logs/c12-generator.json}
     * 중단된 사이클은 같은 번호로 다시 돌기 때문에, 이미 있으면 {@code c12-generator-2.json}처럼 번호를 붙인다.
     */
    public Path newRawLogFile(int cycle, Role role) {
        String base = "c" + cycle + "-" + role.id();
        Path file = logsDir().resolve(base + ".json");
        int attempt = 2;
        while (Files.exists(file)) {
            file = logsDir().resolve(base + "-" + attempt + ".json");
            attempt++;
        }
        return file;
    }
}
