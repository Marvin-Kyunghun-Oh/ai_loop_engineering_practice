package harness.claude;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

/**
 * {@link ProcessClaudeRunnerTest}가 claude 대신 실행하는 프로그램.
 * 테스트가 만든 래퍼 스크립트(.cmd / .sh)가 환경 변수로 동작을 정해 이 클래스를 실행한다.
 *
 * <ul>
 *   <li>받은 인자, 표준 입력, 작업 폴더, PID를 {@code FAKE_CLAUDE_RECORD} 폴더에 기록한다.</li>
 *   <li>{@code FAKE_CLAUDE_MODE}: success(파일 내용을 표준 출력으로), sleep(오래 멈춤), garbage(JSON 아님, 종료 코드 3)</li>
 * </ul>
 */
public final class FakeClaudeMain {

    private FakeClaudeMain() {
    }

    public static void main(String[] args) throws Exception {
        Path record = Path.of(System.getenv("FAKE_CLAUDE_RECORD"));
        Files.writeString(record.resolve("pid.txt"), Long.toString(ProcessHandle.current().pid()));
        Files.writeString(record.resolve("args.txt"), String.join("\n", args), StandardCharsets.UTF_8);
        Files.writeString(record.resolve("cwd.txt"), Path.of("").toAbsolutePath().toString(), StandardCharsets.UTF_8);
        if (!"interactive".equals(System.getenv("FAKE_CLAUDE_MODE"))) {
            Files.write(record.resolve("stdin.txt"), System.in.readAllBytes());   // 대화형은 표준 입력을 읽지 않는다
        }

        switch (System.getenv("FAKE_CLAUDE_MODE")) {
            case "success" -> {
                System.out.write(Files.readAllBytes(Path.of(System.getenv("FAKE_CLAUDE_STDOUT"))));
                System.out.flush();
            }
            case "interactive" -> { }   // 인자만 기록하고 바로 끝낸다
            case "sleep" -> Thread.sleep(120_000);
            case "garbage" -> {
                System.out.print("not json");
                System.out.flush();
                System.exit(3);
            }
            default -> throw new IllegalArgumentException("모르는 모드");
        }
    }
}
