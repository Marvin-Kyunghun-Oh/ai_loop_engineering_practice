package harness;

import static org.junit.jupiter.api.Assertions.assertTrue;

import harness.state.TextFiles;
import java.io.IOException;
import java.io.OutputStream;
import java.io.PrintStream;
import java.io.UncheckedIOException;
import java.net.URISyntaxException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Comparator;
import java.util.stream.Stream;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;

/**
 * 실제 {@code claude}로 샘플 프로젝트를 돌려 하네스와 프롬프트 사이의 배관을 확인한다 (DESIGN 7.1, 0011).
 *
 * <p><b>비용이 든다.</b> 세 역할 모두 haiku이고 상한은 {@code harness.yml}의 {@code max_total_usd: 1}이다.
 * 평소에는 건너뛴다. 실행하려면 환경 변수를 켠다.
 * <pre>
 * $env:HARNESS_SMOKE = "1"; ./gradlew smokeTest
 * </pre>
 *
 * <p>샘플 프로젝트를 {@code build/smoke-run/}에 복사해서 돌린다(원본은 건드리지 않는다). 실행이 끝나면 그 폴더에
 * {@code docs/}, {@code .harness/logs/}가 남고, 리포트는 {@code build/smoke-run/REPORT.md}에 저장한다.
 * 검사 항목은 {@link SmokeChecks}에 있다. 에이전트가 만든 코드의 품질은 검사하지 않는다.
 */
@EnabledIfEnvironmentVariable(named = "HARNESS_SMOKE", matches = "1")
class SmokeTest {

    private static final Path RUN_DIR = Path.of("build", "smoke-run").toAbsolutePath();

    @Test
    @DisplayName("샘플 프로젝트를 실제 claude로 돌리고 배관을 검사한다")
    void sampleProject() throws Exception {
        prepareRunDirectory();

        // 하네스 콘솔 출력을 화면과 파일에 함께 남긴다.
        Path consoleLog = RUN_DIR.resolve("console.log");
        int exit;
        try (PrintStream fileOut = new PrintStream(Files.newOutputStream(consoleLog), true, StandardCharsets.UTF_8)) {
            PrintStream tee = new PrintStream(new Tee(System.out, fileOut), true, StandardCharsets.UTF_8);
            exit = Main.run(RUN_DIR, tee);
        }

        SmokeChecks.Report report = SmokeChecks.inspect(RUN_DIR, exit);
        String text = report.toMarkdown();
        TextFiles.write(RUN_DIR.resolve("REPORT.md"), text);
        System.out.println();
        System.out.println(text);

        assertTrue(report.allPassed(), "실패한 검사가 있다. " + RUN_DIR.resolve("REPORT.md") + " 와 .harness/logs/ 를 본다");
    }

    private static void prepareRunDirectory() throws IOException, URISyntaxException {
        if (Files.exists(RUN_DIR)) {
            try (Stream<Path> paths = Files.walk(RUN_DIR)) {
                for (Path path : (Iterable<Path>) paths.sorted(Comparator.reverseOrder())::iterator) {
                    Files.delete(path);
                }
            }
        }
        Path sample = Path.of(SmokeTest.class.getResource("/sample-project").toURI());
        copyTree(sample, RUN_DIR);
    }

    static void copyTree(Path from, Path to) throws IOException {
        try (Stream<Path> paths = Files.walk(from)) {
            for (Path source : (Iterable<Path>) paths::iterator) {
                Path target = to.resolve(from.relativize(source).toString());
                if (Files.isDirectory(source)) {
                    Files.createDirectories(target);
                } else {
                    Files.copy(source, target);
                }
            }
        } catch (UncheckedIOException e) {
            throw e.getCause();
        }
    }

    /** 두 스트림에 같은 바이트를 쓴다. */
    private static final class Tee extends OutputStream {
        private final OutputStream first;
        private final OutputStream second;

        Tee(OutputStream first, OutputStream second) {
            this.first = first;
            this.second = second;
        }

        @Override
        public void write(int b) throws IOException {
            first.write(b);
            second.write(b);
        }

        @Override
        public void write(byte[] b, int off, int len) throws IOException {
            first.write(b, off, len);
            second.write(b, off, len);
        }

        @Override
        public void flush() throws IOException {
            first.flush();
            second.flush();
        }
    }
}
