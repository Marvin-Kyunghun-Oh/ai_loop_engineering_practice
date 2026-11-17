import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.TimeUnit;

// 실행: java QuoteTest.java  (quote-cli 디렉터리에서)
class QuoteTest {
    static int passed = 0;
    static int failed = 0;

    public static void main(String[] args) throws Exception {
        System.setOut(new java.io.PrintStream(System.out, true, StandardCharsets.UTF_8));
        List<String> quotes = loadQuotes();

        check("quotes.json에 명언이 1개 이상 있다", !quotes.isEmpty());

        // 1) 인수 없이 실행: 명언이 정확히 한 줄 출력되고, quotes.json에 있는 명언이어야 한다
        List<String> lines = run();
        check("인수 없이 실행하면 한 줄만 출력된다 (출력 " + lines.size() + "줄)", lines.size() == 1);
        check("출력된 명언이 quotes.json에 존재한다",
                lines.size() == 1 && quotes.contains(lines.get(0)));

        // 2) --list: 전체 항목이 번호와 함께 순서대로 출력되어야 한다
        for (String flag : new String[] {"--list", "-list"}) {
            List<String> out = run(flag);
            check(flag + ": 줄 수가 전체 명언 수(" + quotes.size() + ")와 같다 (출력 " + out.size() + "줄)",
                    out.size() == quotes.size());
            boolean all = out.size() == quotes.size();
            for (int i = 0; all && i < quotes.size(); i++) {
                all = out.get(i).equals((i + 1) + ". " + quotes.get(i));
            }
            check(flag + ": 모든 항목이 '번호. 명언' 형식으로 순서대로 출력된다", all);
        }

        // 3) 알 수 없는 인수: 비정상 종료(종료 코드 2)하고 명언을 출력하지 않아야 한다
        List<String> bad = run(2, "--lst");
        check("알 수 없는 인수는 종료 코드 2로 끝나고 사용법만 출력한다",
                bad.stream().noneMatch(quotes::contains));

        System.out.println();
        System.out.println("결과: " + passed + " 통과, " + failed + " 실패");
        if (failed > 0) System.exit(1);
    }

    static void check(String name, boolean ok) {
        System.out.println((ok ? "[PASS] " : "[FAIL] ") + name);
        if (ok) passed++; else failed++;
    }

    // 정상 종료(코드 0)를 기대하는 실행
    static List<String> run(String... args) throws IOException, InterruptedException {
        return run(0, args);
    }

    // Quote.java를 별도 프로세스로 실행하고 출력(stdout+stderr)을 줄 단위로 반환한다.
    // 종료 코드가 expectedExit와 다르면 실패로 기록하고, 30초 안에 끝나지 않으면 강제 종료한다.
    static List<String> run(int expectedExit, String... args) throws IOException, InterruptedException {
        List<String> cmd = new ArrayList<>();
        cmd.add(Path.of(System.getProperty("java.home"), "bin", "java").toString());
        cmd.add("-Dfile.encoding=UTF-8");
        cmd.add("Quote.java");
        cmd.addAll(List.of(args));
        String label = "Quote.java " + String.join(" ", args);

        // 파이프를 읽다가 멈추지 않도록 출력은 임시 파일로 받는다.
        Path outFile = Files.createTempFile("quote-test", ".out");
        String out;
        try {
            Process p = new ProcessBuilder(cmd).redirectErrorStream(true)
                    .redirectOutput(outFile.toFile()).start();
            if (!p.waitFor(30, TimeUnit.SECONDS)) {
                p.destroyForcibly();
                check(label + ": 30초 안에 종료된다", false);
                return new ArrayList<>();
            }
            check(label + ": 종료 코드 " + expectedExit + " (실제 " + p.exitValue() + ")",
                    p.exitValue() == expectedExit);
            out = Files.readString(outFile, StandardCharsets.UTF_8);
        } finally {
            Files.deleteIfExists(outFile);
        }
        List<String> lines = new ArrayList<>();
        for (String l : out.split("\\R")) {
            if (!l.isEmpty()) lines.add(l);
        }
        return lines;
    }

    // 문자열 배열 형태의 quotes.json 파싱
    static List<String> loadQuotes() throws IOException {
        String json = Files.readString(Path.of("quotes.json"), StandardCharsets.UTF_8);
        List<String> result = new ArrayList<>();
        StringBuilder sb = null;
        for (int i = 0; i < json.length(); i++) {
            char c = json.charAt(i);
            if (sb == null) {
                if (c == '"') sb = new StringBuilder();
            } else if (c == '\\') {
                sb.append(json.charAt(++i));
            } else if (c == '"') {
                result.add(sb.toString());
                sb = null;
            } else {
                sb.append(c);
            }
        }
        return result;
    }
}
