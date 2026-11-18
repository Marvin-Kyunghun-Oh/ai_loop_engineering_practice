package todo;

import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.util.Arrays;

/** CLI 진입점. 인자 파싱과 출력만 담당하고 로직은 TodoList에 위임한다. */
public class Main {

    private static final String USAGE = """
            사용법:
              add <제목>   할 일 추가
              list         목록 보기
              start <id>   진행 시작
              done <id>    완료 처리""";

    private static final String ANSI_RESET = "\u001B[0m";

    public static void main(String[] args) {
        // 터미널에 직접 출력할 때만 색을 쓴다(파이프/리다이렉트, NO_COLOR 설정 시 제외).
        // gradle run은 출력을 파이프로 연결해 console()이 null이므로 -Dtodo.color=true로 강제할 수 있다.
        boolean forced = Boolean.getBoolean("todo.color");
        boolean color = (forced || System.console() != null) && System.getenv("NO_COLOR") == null;
        // 기본 인코딩(Windows는 MS949)과 무관하게 항상 UTF-8로 출력한다.
        PrintStream out = new PrintStream(System.out, true, StandardCharsets.UTF_8);
        PrintStream err = new PrintStream(System.err, true, StandardCharsets.UTF_8);
        System.exit(run(args, Path.of("todos.json"), out, err, color));
    }

    /** 색 없이 실행한다. */
    static int run(String[] args, Path file, PrintStream out, PrintStream err) {
        return run(args, file, out, err, false);
    }

    /** 테스트와 분리를 위해 경로/출력 스트림을 주입받는다. 종료 코드를 반환한다. */
    static int run(String[] args, Path file, PrintStream out, PrintStream err, boolean color) {
        if (args.length == 0) {
            err.println(USAGE);
            return 1;
        }
        try {
            TodoStore store = new TodoStore(file);
            TodoList list = store.load();
            String command = args[0];
            switch (command) {
                case "add" -> {
                    if (args.length < 2) {
                        err.println("제목을 입력하세요.\n" + USAGE);
                        return 1;
                    }
                    Todo t = list.add(String.join(" ", Arrays.copyOfRange(args, 1, args.length)));
                    store.save(list);
                    out.println("추가됨: " + format(t));
                }
                case "list" -> {
                    if (list.list().isEmpty()) {
                        out.println("할 일이 없습니다.");
                    }
                    list.list().forEach(t -> out.println(formatListLine(t, color)));
                }
                case "start" -> {
                    Todo t = list.start(parseId(args));
                    store.save(list);
                    out.println("시작됨: " + format(t));
                }
                case "done" -> {
                    Todo t = list.done(parseId(args));
                    store.save(list);
                    out.println("완료됨: " + format(t));
                }
                default -> {
                    err.println("알 수 없는 명령: " + command + "\n" + USAGE);
                    return 1;
                }
            }
            return 0;
        } catch (IllegalArgumentException | IllegalStateException e) {
            err.println("오류: " + e.getMessage());
            return 1;
        }
    }

    private static int parseId(String[] args) {
        if (args.length < 2) {
            throw new IllegalArgumentException("id를 입력하세요.");
        }
        try {
            return Integer.parseInt(args[1]);
        } catch (NumberFormatException e) {
            throw new IllegalArgumentException("id는 숫자여야 합니다: " + args[1]);
        }
    }

    /** list용 한 줄: 상태 기호 + id + 제목. 예) "[=] 2 운동" */
    static String formatListLine(Todo t, boolean color) {
        String line = "%s %d %s".formatted(t.status().marker(), t.id(), t.title());
        return color ? t.status().ansiColor() + line + ANSI_RESET : line;
    }

    private static String format(Todo t) {
        return "[%d] (%s) %s".formatted(t.id(), t.status().label(), t.title());
    }
}
