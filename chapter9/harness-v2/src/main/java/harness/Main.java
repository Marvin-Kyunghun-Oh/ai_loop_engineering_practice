package harness;

import java.nio.file.Files;
import java.nio.file.Path;

/**
 * 하네스 진입점.
 *
 * <pre>
 * ./gradlew run --args="../projects/&lt;project&gt;"
 * </pre>
 *
 * 지금은 인자만 검사한다. 메인 루프는 DESIGN 8절 5단계에서 연결한다.
 */
public final class Main {

    private Main() {
    }

    public static void main(String[] args) {
        if (args.length != 1) {
            System.err.println("사용법: harness-v2 <대상 프로젝트 경로>");
            System.exit(2);
        }

        Path projectDir = Path.of(args[0]).toAbsolutePath().normalize();
        if (!Files.isDirectory(projectDir)) {
            System.err.println("대상 프로젝트 폴더가 없다: " + projectDir);
            System.exit(2);
        }

        System.out.println("대상 프로젝트: " + projectDir);
        System.out.println("메인 루프는 아직 구현되지 않았다.");
    }
}
