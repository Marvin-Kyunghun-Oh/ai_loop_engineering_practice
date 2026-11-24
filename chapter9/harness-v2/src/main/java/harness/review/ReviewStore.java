package harness.review;

import harness.state.TextFiles;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 항목별 판정과 핵심 결정을 {@code .harness/reviews.csv}에 쌓는다 (DESIGN 4.4).
 * 아카이브 때 TASKS.md 요약 줄을 만드는 데 쓴다. REVIEW.md는 사이클마다 덮어쓰이기 때문에 따로 남겨야 한다.
 *
 * <pre>
 * task_id,cycle,verdict,key_decision
 * T8s,35,PASS 11/12,깊이 태그별
 * </pre>
 *
 * 같은 항목을 다시 평가하면 줄이 하나 더 생기고, 읽을 때는 마지막 줄이 이긴다.
 * 쉼표나 큰따옴표가 든 값은 큰따옴표로 감싼다. 깨진 줄이 있으면 예외를 던진다(USAGE.csv와 같은 이유로, 조용히 건너뛰지 않는다).
 */
public final class ReviewStore {

    static final String HEADER = "task_id,cycle,verdict,key_decision";
    private static final int COLUMN_COUNT = 4;

    private final Path csv;

    public ReviewStore(Path csv) {
        this.csv = csv;
    }

    public void save(ReviewRecord record) {
        if (!Files.exists(csv)) {
            TextFiles.appendLine(csv, HEADER);
        }
        TextFiles.appendLine(csv, String.join(",",
                quote(record.taskId()),
                String.valueOf(record.cycle()),
                quote(record.verdict()),
                quote(record.keyDecision())));
    }

    /** 항목 ID별 가장 최근 기록. 파일이 없으면 빈 맵. */
    public Map<String, ReviewRecord> loadLatest() {
        Map<String, ReviewRecord> latest = new LinkedHashMap<>();
        if (!Files.exists(csv)) {
            return latest;
        }
        List<String> lines = TextFiles.read(csv).lines().toList();
        if (lines.isEmpty() || !lines.get(0).equals(HEADER)) {
            throw new IllegalStateException("reviews.csv 머리줄이 다르다: " + csv);
        }
        for (int i = 1; i < lines.size(); i++) {
            if (lines.get(i).isBlank()) {
                continue;
            }
            List<String> columns = split(lines.get(i));
            if (columns.size() != COLUMN_COUNT) {
                throw new IllegalStateException("reviews.csv " + (i + 1) + "번째 줄의 칸 수가 " + columns.size()
                        + "개다 (기대 " + COLUMN_COUNT + "개): " + csv);
            }
            int cycle;
            try {
                cycle = Integer.parseInt(columns.get(1));
            } catch (NumberFormatException e) {
                throw new IllegalStateException("reviews.csv " + (i + 1) + "번째 줄의 cycle을 읽을 수 없다: \""
                        + columns.get(1) + "\" (" + csv + ")");
            }
            ReviewRecord record = new ReviewRecord(columns.get(0), cycle, columns.get(2), columns.get(3));
            latest.put(record.taskId(), record);
        }
        return latest;
    }

    static String quote(String value) {
        if (value.contains(",") || value.contains("\"")) {
            return "\"" + value.replace("\"", "\"\"") + "\"";
        }
        return value;
    }

    /** 큰따옴표로 감싼 칸을 지원하는 한 줄 분리. */
    static List<String> split(String line) {
        List<String> columns = new ArrayList<>();
        StringBuilder current = new StringBuilder();
        boolean inQuotes = false;
        for (int i = 0; i < line.length(); i++) {
            char c = line.charAt(i);
            if (inQuotes) {
                if (c == '"' && i + 1 < line.length() && line.charAt(i + 1) == '"') {
                    current.append('"');
                    i++;
                } else if (c == '"') {
                    inQuotes = false;
                } else {
                    current.append(c);
                }
            } else if (c == '"') {
                inQuotes = true;
            } else if (c == ',') {
                columns.add(current.toString());
                current.setLength(0);
            } else {
                current.append(c);
            }
        }
        columns.add(current.toString());
        return columns;
    }
}
