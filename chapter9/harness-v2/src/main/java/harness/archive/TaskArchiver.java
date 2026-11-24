package harness.archive;

import harness.review.ReviewRecord;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * 끝난 마일스톤의 작업 지시를 TASKS.md에서 archive로 옮긴다 (0005, DESIGN 4.4, 5.8).
 *
 * <p>입력은 TASKS.md 문자열과 항목별 판정, 출력은 새 TASKS.md 문자열과 archive에 추가할 내용이다.
 * 파일 입출력은 호출하는 쪽({@code Harness})이 한다.
 *
 * <p><b>아카이브 조건</b>: 마일스톤 섹션({@code ## M{n}. 제목})이 다음을 모두 만족할 때만 옮긴다.
 * <ul>
 *   <li>섹션 안의 항목이 전부 {@code - [x]}이고 항목 ID가 있다.</li>
 *   <li>그 뒤의 섹션에 항목이 1개 이상 있다. 일이 다음 마일스톤으로 넘어간 것이 확실할 때만 옮긴다(마지막 마일스톤은 옮기지 않는다).</li>
 * </ul>
 *
 * <p><b>동작</b>: 항목의 상세 줄(항목 줄과 그 아래 들여쓴 줄 전체)을 archive로 옮기고, TASKS.md에는 요약 한 줄만 남긴다.
 * <pre>
 * - [x] T8s. 버리기 깊이 태그별 분리 — PASS 11/12 · 결정: 깊이 태그별 · 상세: archive/TASKS-M2.md#T8s
 * </pre>
 * 이미 요약 줄이 된 항목은 다시 옮기지 않는다. 그래서 같은 입력에 여러 번 불러도 결과가 같다.
 */
public final class TaskArchiver {

    /** TASKS.md 요약 줄에서 archive를 가리키는 표지. 이 문자열이 든 한 줄짜리 항목을 이미 옮긴 것으로 본다. */
    static final String DETAIL_MARK = "상세: archive/";

    private static final Pattern MILESTONE_HEADER = Pattern.compile("^## M(\\d+)\\.\\s*(.*?)\\s*$");
    private static final Pattern ANY_HEADER = Pattern.compile("^## .*$");
    private static final Pattern ITEM_LINE = Pattern.compile("^- \\[([ xX])\\]\\s*(.*)$");
    private static final Pattern ITEM_ID = Pattern.compile("^(T\\d+[a-z]*)\\.\\s*(.*)$");

    private TaskArchiver() {
    }

    /**
     * 옮긴 마일스톤 하나.
     *
     * @param number archive 파일 이름에 쓰는 마일스톤 번호
     * @param title  마일스톤 제목
     * @param body   옮긴 항목의 상세. 항목 사이는 빈 줄 하나로 구분하고 줄바꿈으로 끝난다
     */
    public record ArchivedMilestone(int number, String title, String body) {

        public String fileName() {
            return archiveFileName(number);
        }

        /** archive 파일에 쓸 내용. {@code ## M2. 제목} 제목 아래에 항목 상세가 온다. */
        public String toArchiveText() {
            return "## M" + number + ". " + title + "\n\n" + body;
        }
    }

    /**
     * @param tasksText 새 TASKS.md. 옮길 것이 없으면 입력과 같다
     * @param archived  archive에 추가할 마일스톤들. 옮길 것이 없으면 빈 목록
     */
    public record Result(String tasksText, List<ArchivedMilestone> archived) {
    }

    public static String archiveFileName(int milestone) {
        return "TASKS-M" + milestone + ".md";
    }

    /** @param reviews 항목 ID별 가장 최근 판정. 없는 항목은 요약 줄에 {@code -}로 쓴다 */
    public static Result archive(String tasksText, Map<String, ReviewRecord> reviews) {
        List<String> lines = tasksText.lines().toList();
        List<Section> sections = parseSections(lines);

        // 줄 번호 → 그 줄부터 시작하는, 요약 줄로 바꿀 항목
        Map<Integer, Replacement> replaced = new HashMap<>();
        List<ArchivedMilestone> archived = new ArrayList<>();

        for (int k = 0; k < sections.size(); k++) {
            Section section = sections.get(k);
            if (!isArchivable(sections, k)) {
                continue;
            }
            List<String> blocks = new ArrayList<>();
            for (Item item : section.items()) {
                if (item.isSummary()) {
                    continue;
                }
                blocks.add(String.join("\n", lines.subList(item.start(), item.end())));
                replaced.put(item.start(), new Replacement(item, section.number()));
            }
            archived.add(new ArchivedMilestone(section.number(), section.title(),
                    String.join("\n\n", blocks) + "\n"));
        }

        if (archived.isEmpty()) {
            return new Result(tasksText, List.of());
        }

        String lineSeparator = tasksText.contains("\r\n") ? "\r\n" : "\n";
        List<String> out = new ArrayList<>();
        int i = 0;
        while (i < lines.size()) {
            Replacement replacement = replaced.get(i);
            if (replacement == null) {
                out.add(lines.get(i));
                i++;
            } else {
                Item item = replacement.item();
                out.add(summaryLine(item, replacement.milestone(), reviews.get(item.id())));
                i = item.end();
            }
        }
        String joined = String.join(lineSeparator, out);
        if (tasksText.endsWith("\n")) {
            joined += lineSeparator;
        }
        return new Result(joined, archived);
    }

    private static String summaryLine(Item item, int milestone, ReviewRecord review) {
        String verdict = review == null ? "-" : review.verdict();
        String decision = review == null ? "-" : review.keyDecision();
        return "- [x] " + item.id() + ". " + item.title()
                + " — " + verdict
                + " · 결정: " + decision
                + " · " + DETAIL_MARK + archiveFileName(milestone) + "#" + item.id();
    }

    // ---- 조건 ----

    private static boolean isArchivable(List<Section> sections, int index) {
        Section section = sections.get(index);
        if (section.number() == null || section.items().isEmpty()) {
            return false;
        }
        boolean allDone = section.items().stream().allMatch(item -> item.checked() && item.id() != null);
        boolean hasWork = section.items().stream().anyMatch(item -> !item.isSummary());
        if (!allDone || !hasWork) {
            return false;
        }
        for (int later = index + 1; later < sections.size(); later++) {
            if (!sections.get(later).items().isEmpty()) {
                return true;
            }
        }
        return false;
    }

    // ---- 파싱 ----

    private record Replacement(Item item, int milestone) {
    }

    /**
     * @param number 마일스톤 번호. {@code ## M{n}.} 형식이 아닌 {@code ##} 제목이면 null (옮기지 않는다)
     */
    private record Section(Integer number, String title, List<Item> items) {
    }

    /**
     * @param start   항목 줄의 번호(0부터)
     * @param end     항목 상세의 끝(이 줄은 포함하지 않는다). 뒤의 빈 줄은 뺀다
     * @param id      항목 ID. 없으면 null
     * @param title   ID 뒤의 제목
     * @param summary 이미 요약 줄이 된 항목인지
     */
    private record Item(int start, int end, boolean checked, String id, String title, boolean summary) {

        boolean isSummary() {
            return summary;
        }
    }

    private static List<Section> parseSections(List<String> lines) {
        List<Section> sections = new ArrayList<>();
        List<Integer> sectionStarts = new ArrayList<>();   // 각 섹션 본문이 시작하는 줄
        List<Integer> sectionEnds = new ArrayList<>();

        for (int i = 0; i < lines.size(); i++) {
            if (!ANY_HEADER.matcher(lines.get(i)).matches()) {
                continue;
            }
            if (!sectionEnds.isEmpty()) {
                sectionEnds.set(sectionEnds.size() - 1, i);
            }
            Matcher milestone = MILESTONE_HEADER.matcher(lines.get(i));
            if (milestone.matches()) {
                sections.add(new Section(Integer.valueOf(milestone.group(1)), milestone.group(2), new ArrayList<>()));
            } else {
                sections.add(new Section(null, lines.get(i).substring(3).strip(), new ArrayList<>()));
            }
            sectionStarts.add(i + 1);
            sectionEnds.add(lines.size());
        }

        for (int s = 0; s < sections.size(); s++) {
            collectItems(lines, sectionStarts.get(s), sectionEnds.get(s), sections.get(s).items());
        }
        return sections;
    }

    private static void collectItems(List<String> lines, int from, int to, List<Item> items) {
        List<Integer> starts = new ArrayList<>();
        for (int i = from; i < to; i++) {
            if (ITEM_LINE.matcher(lines.get(i)).matches()) {
                starts.add(i);
            }
        }
        for (int n = 0; n < starts.size(); n++) {
            int start = starts.get(n);
            int limit = n + 1 < starts.size() ? starts.get(n + 1) : to;
            int end = limit;
            while (end > start + 1 && lines.get(end - 1).isBlank()) {
                end--;
            }

            Matcher line = ITEM_LINE.matcher(lines.get(start));
            line.matches();
            boolean checked = !line.group(1).equals(" ");
            Matcher id = ITEM_ID.matcher(line.group(2));
            boolean hasId = id.matches();
            boolean summary = end == start + 1 && lines.get(start).contains(DETAIL_MARK);
            items.add(new Item(start, end, checked, hasId ? id.group(1) : null,
                    hasId ? id.group(2) : line.group(2), summary));
        }
    }
}
