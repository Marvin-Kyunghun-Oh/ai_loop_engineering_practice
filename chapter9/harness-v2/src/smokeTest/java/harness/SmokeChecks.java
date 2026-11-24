package harness;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import harness.cost.CostLedger;
import harness.review.ReviewBlock;
import harness.review.ReviewParser;
import harness.review.ReviewRecord;
import harness.review.ReviewStore;
import harness.state.ProjectFiles;
import harness.state.TextFiles;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.math.BigDecimal;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Clock;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.regex.Pattern;
import java.util.stream.Collectors;
import java.util.stream.Stream;

/**
 * 스모크 테스트가 끝난 프로젝트 폴더에서 하네스와 프롬프트 사이의 배관을 검사한다 (DESIGN 7.1).
 * 에이전트가 만든 코드의 품질은 검사하지 않는다.
 *
 * <p>검사는 하나가 실패해도 멈추지 않고 모두 돌려서 한 번에 보고한다. 원인이 하네스인지 모델인지는 사람이 원본 로그로 가린다.
 */
final class SmokeChecks {

    private static final ObjectMapper JSON = new ObjectMapper();
    private static final Pattern JOURNAL_LINE = Pattern.compile(
            "^- \\S+ \\[c\\d+] (planner|generator|evaluator): .+ · (\\$\\d+\\.\\d{2}|\\$\\?) · \\S+( · .+)?$");
    private static final Pattern TASKS_MILESTONE = Pattern.compile("(?m)^## M\\d+\\. .+$");
    private static final Pattern TASKS_ITEM = Pattern.compile("(?m)^- \\[[ xX]] T\\d+[a-z]*\\. .+$");
    /** harness.yml의 허용 Bash 패턴(접두어). 이 명령이 거부되면 허용 목록이 제대로 안 먹은 것이다. */
    private static final List<String> ALLOWED_COMMAND_PREFIXES =
            List.of("python3 -m unittest", "python3 -m compileall");

    private SmokeChecks() {
    }

    record Check(String name, boolean ok, String detail) {
    }

    record Report(List<Check> checks, List<String> info) {

        boolean allPassed() {
            return checks.stream().allMatch(Check::ok);
        }

        String toMarkdown() {
            StringBuilder out = new StringBuilder("# 스모크 테스트 리포트\n\n## 검사\n\n");
            for (Check check : checks) {
                out.append(check.ok() ? "- [PASS] " : "- [FAIL] ").append(check.name());
                if (!check.detail().isBlank()) {
                    out.append(" — ").append(check.detail());
                }
                out.append('\n');
            }
            out.append("\n## 참고 (판정하지 않음)\n\n");
            info.forEach(line -> out.append("- ").append(line).append('\n'));
            return out.toString();
        }
    }

    static Report inspect(Path projectDir, int exitCode) {
        ProjectFiles files = new ProjectFiles(projectDir);
        List<Check> checks = new ArrayList<>();
        List<String> info = new ArrayList<>();
        List<Path> rawLogs = rawLogs(files);

        checks.add(checkExit(files, exitCode, info));
        checks.add(checkAllRolesRan(rawLogs));
        checks.add(checkCurrent(files));
        checks.add(checkTasks(files));
        checks.add(checkReview(files));
        checks.add(checkUsage(files, rawLogs, info));
        checks.add(checkJournal(files));
        checks.add(checkRawLogs(rawLogs, info));
        checks.add(checkPrompts(files));
        checks.add(checkPermissionDenials(rawLogs, info));
        return new Report(checks, info);
    }

    // ---- 검사 ----

    /** 루프가 DONE, 상한(예산), 또는 max_iterations로 정상 종료했다. */
    private static Check checkExit(ProjectFiles files, int exitCode, List<String> info) {
        String name = "루프가 DONE, 상한, 또는 max_iterations로 정상 종료했다";
        info.add("종료 코드 " + exitCode + ", DONE " + (Files.exists(files.done()) ? "있음" : "없음")
                + ", 완료한 사이클 " + files.readCycleCount());
        if (exitCode == Harness.EXIT_OK) {
            return new Check(name, true, "종료 코드 0");
        }
        if (files.isHalted()) {
            String halt = TextFiles.read(files.halt());
            boolean budget = halt.startsWith("사유: 예산 소진");
            return new Check(name, budget, budget ? "예산 상한으로 멈춤" : "HALT: " + halt.strip().replace("\n", " / "));
        }
        return new Check(name, false, "종료 코드 " + exitCode + ", HALT 파일 없음");
    }

    private static Check checkAllRolesRan(List<Path> rawLogs) {
        String name = "한 사이클 이상 planner, generator, evaluator가 모두 실행됐다";
        List<String> missing = Stream.of("planner", "generator", "evaluator")
                .filter(role -> rawLogs.stream().noneMatch(log -> log.getFileName().toString().contains("-" + role)))
                .toList();
        return new Check(name, missing.isEmpty(), missing.isEmpty() ? "" : "실행 기록이 없는 역할: " + missing);
    }

    /** 4.1: planner가 docs/CURRENT를 항목 ID 한 줄로 썼다. DONE으로 끝난 마지막 사이클에는 없을 수 있다. */
    private static Check checkCurrent(ProjectFiles files) {
        String name = "docs/CURRENT가 4.1 형식이다 (없으면 DONE으로 끝난 것)";
        Optional<String> current = files.readCurrent();
        if (current.isEmpty()) {
            return new Check(name, true, "파일 없음");
        }
        boolean valid = ProjectFiles.isValidTaskId(current.get());
        return new Check(name, valid, "\"" + current.get() + "\"");
    }

    /** TaskArchiver가 읽는 형식: ## M{n}. 제목, - [ ] T{n}. 제목 */
    private static Check checkTasks(ProjectFiles files) {
        String name = "TASKS.md가 마일스톤 제목(## M1. ...)과 항목(- [ ] T1. ...) 형식이다";
        if (!Files.exists(files.tasks())) {
            return new Check(name, false, "TASKS.md가 없다");
        }
        String text = TextFiles.read(files.tasks());
        long milestones = TASKS_MILESTONE.matcher(text).results().count();
        long items = TASKS_ITEM.matcher(text).results().count();
        return new Check(name, milestones >= 1 && items >= 1, "마일스톤 " + milestones + "개, 항목 " + items + "개");
    }

    /** 4.2: evaluator가 REVIEW.md 맨 위에 판정 블록과 평가 대상 줄을 썼고, 하네스가 reviews.csv에 저장했다. */
    private static Check checkReview(ProjectFiles files) {
        String name = "REVIEW.md 맨 위가 4.2 블록(판정, 평가 대상)이고 reviews.csv에 저장됐다";
        if (!Files.exists(files.review())) {
            return new Check(name, false, "REVIEW.md가 없다");
        }
        Optional<ReviewBlock> block = ReviewParser.parse(TextFiles.read(files.review()));
        if (block.isEmpty()) {
            return new Check(name, false, "'판정:' 줄을 읽지 못했다. 첫 줄: "
                    + TextFiles.read(files.review()).lines().findFirst().orElse("(빈 파일)"));
        }
        ReviewBlock b = block.get();
        if (b.taskId() == null) {
            return new Check(name, false, "판정 '" + b.verdict() + "'은 읽었지만 '평가 대상:' 줄이 없다");
        }
        Map<String, ReviewRecord> saved = new ReviewStore(files.reviewsCsv()).loadLatest();
        boolean stored = saved.containsKey(b.taskId());
        return new Check(name, stored, "판정 '" + b.verdict() + "', 핵심 결정 '" + b.keyDecision() + "', "
                + b.taskId() + " 사이클 " + b.cycle() + (stored ? ", reviews.csv에 있음" : ", reviews.csv에 없음"));
    }

    /** 4.5: USAGE.csv가 읽히고, 에이전트 실행 수만큼 줄이 있다. */
    private static Check checkUsage(ProjectFiles files, List<Path> rawLogs, List<String> info) {
        String name = "USAGE.csv가 4.5 형식이고 실행 수와 줄 수가 같다";
        if (!Files.exists(files.usageCsv())) {
            return new Check(name, false, "USAGE.csv가 없다");
        }
        try {
            BigDecimal total = CostLedger.load(files.usageCsv(), new BigDecimal("1000"), Clock.systemDefaultZone())
                    .total();
            long rows = TextFiles.read(files.usageCsv()).lines().skip(1).filter(l -> !l.isBlank()).count();
            info.add("USAGE.csv 비용 합계 $" + total.toPlainString() + " (0007 비용 보정에 쓴다. 실행 " + rows + "회)");
            return new Check(name, rows == rawLogs.size(), "줄 " + rows + "개, 원본 로그 " + rawLogs.size() + "개");
        } catch (IllegalStateException e) {
            return new Check(name, false, e.getMessage());
        }
    }

    /** 4.6: JOURNAL의 모든 줄이 하네스 형식이다(에이전트가 직접 쓴 줄이 없다). */
    private static Check checkJournal(ProjectFiles files) {
        String name = "JOURNAL.md의 모든 줄이 4.6 형식이다";
        if (!Files.exists(files.journal())) {
            return new Check(name, false, "JOURNAL.md가 없다");
        }
        List<String> bad = TextFiles.read(files.journal()).lines()
                .filter(line -> !line.isBlank())
                .filter(line -> !JOURNAL_LINE.matcher(line).matches())
                .toList();
        return new Check(name, bad.isEmpty(), bad.isEmpty() ? "" : "형식이 다른 줄: " + bad);
    }

    private static Check checkRawLogs(List<Path> rawLogs, List<String> info) {
        String name = "원본 로그(.harness/logs/*.json)가 모두 결과 JSON이다";
        List<String> bad = new ArrayList<>();
        for (Path log : rawLogs) {
            JsonNode json = parse(log);
            if (json == null || !"result".equals(json.path("type").asText())) {
                bad.add(log.getFileName().toString());
            } else {
                info.add(log.getFileName() + ": subtype=" + json.path("subtype").asText()
                        + ", 비용 $" + json.path("total_cost_usd").asText("?")
                        + ", 턴 " + json.path("num_turns").asText("?")
                        + ", 요약: " + oneLine(json.path("result").asText("(없음)")));
            }
        }
        return new Check(name, bad.isEmpty() && !rawLogs.isEmpty(),
                rawLogs.isEmpty() ? "원본 로그가 없다" : bad.isEmpty() ? rawLogs.size() + "개" : "결과 JSON이 아님: " + bad);
    }

    /** 프롬프트에 치환되지 않은 {{...}}가 남지 않았다. 넘긴 프롬프트는 로그 옆의 *.prompt.md에 있다. */
    private static Check checkPrompts(ProjectFiles files) {
        String name = "프롬프트에 치환되지 않은 {{...}}가 없다";
        List<Path> prompts = listFiles(files.logsDir(), ".prompt.md");
        List<String> bad = prompts.stream()
                .filter(path -> TextFiles.read(path).contains("{{"))
                .map(path -> path.getFileName().toString())
                .toList();
        return new Check(name, bad.isEmpty() && !prompts.isEmpty(),
                prompts.isEmpty() ? "프롬프트 기록이 없다" : bad.isEmpty() ? prompts.size() + "개 확인" : "남은 파일: " + bad);
    }

    /**
     * 허용 목록의 명령은 거부되지 않았다. 거부된 명령은 모두 참고로 적는다.
     * (허용 목록 밖 명령이 막혔는지는 에이전트가 그런 명령을 시도했을 때만 알 수 있다. 시도하지 않았다면 기록이 없다.)
     */
    private static Check checkPermissionDenials(List<Path> rawLogs, List<String> info) {
        String name = "허용 목록의 명령이 거부되지 않았다 (permission_denials)";
        List<String> allowedButDenied = new ArrayList<>();
        int denials = 0;
        for (Path log : rawLogs) {
            JsonNode json = parse(log);
            if (json == null) {
                continue;
            }
            for (JsonNode denial : json.path("permission_denials")) {
                denials++;
                String tool = denial.path("tool_name").asText("?");
                String command = denial.path("tool_input").path("command").asText("");
                String line = log.getFileName() + ": " + tool + (command.isEmpty() ? "" : " `" + command + "`");
                info.add("거부됨 " + line);
                if ("Bash".equals(tool) && ALLOWED_COMMAND_PREFIXES.stream().anyMatch(command::startsWith)) {
                    allowedButDenied.add(line);
                }
            }
        }
        if (denials == 0) {
            info.add("거부된 명령 없음. 허용 목록 밖 명령을 시도하지 않았으면 이 경로는 확인되지 않은 것이다");
        }
        return new Check(name, allowedButDenied.isEmpty(),
                allowedButDenied.isEmpty() ? "거부 " + denials + "건" : "허용 명령이 거부됨: " + allowedButDenied);
    }

    // ---- 도우미 ----

    /** c{N}-{role}.json, c{N}-{role}-2.json (프롬프트 기록 .prompt.md는 제외) */
    private static List<Path> rawLogs(ProjectFiles files) {
        return listFiles(files.logsDir(), ".json");
    }

    private static List<Path> listFiles(Path dir, String suffix) {
        if (!Files.isDirectory(dir)) {
            return List.of();
        }
        try (Stream<Path> entries = Files.list(dir)) {
            return entries.filter(path -> path.getFileName().toString().endsWith(suffix)).sorted().toList();
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    private static JsonNode parse(Path file) {
        try {
            return JSON.readTree(Files.readString(file));
        } catch (IOException e) {
            return null;
        }
    }

    private static String oneLine(String text) {
        String line = text.strip().lines().collect(Collectors.joining(" "));
        return line.length() > 120 ? line.substring(0, 120) + "…" : line;
    }
}
