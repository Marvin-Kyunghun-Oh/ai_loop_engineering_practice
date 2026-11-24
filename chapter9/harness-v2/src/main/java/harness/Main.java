package harness;

import harness.claude.ClaudeExecutable;
import harness.claude.ClaudeRunner;
import harness.claude.ProcessClaudeRunner;
import harness.config.ConfigException;
import harness.config.ConfigLoader;
import harness.config.HarnessConfig;
import harness.prompt.PromptException;
import harness.prompt.PromptRenderer;
import harness.state.ProjectFiles;
import java.io.PrintStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Clock;

/**
 * 하네스 진입점.
 *
 * <pre>
 * build/install/harness-v2/bin/harness-v2 ../projects/&lt;project&gt;   (./gradlew installDist 후, Windows는 harness-v2.bat)
 * </pre>
 *
 * 종료 코드: 0 = DONE 또는 최대 반복 도달, 1 = HALT, 2 = 시작 전 오류(인자, harness.yml, 프롬프트, claude 실행 파일)
 */
public final class Main {

    private static final int EXIT_STARTUP_ERROR = 2;

    private Main() {
    }

    public static void main(String[] args) {
        if (args.length != 1) {
            System.err.println("사용법: harness-v2 <대상 프로젝트 경로>");
            System.exit(EXIT_STARTUP_ERROR);
        }

        Path projectDir = Path.of(args[0]).toAbsolutePath().normalize();
        if (!Files.isDirectory(projectDir)) {
            System.err.println("대상 프로젝트 폴더가 없다: " + projectDir);
            System.exit(EXIT_STARTUP_ERROR);
        }

        System.exit(run(projectDir, System.out));
    }

    /** 스모크 테스트가 같은 조립을 쓰도록 콘솔을 받는다. */
    static int run(Path projectDir, PrintStream console) {
        ProjectFiles files = new ProjectFiles(projectDir);
        Clock clock = Clock.systemDefaultZone();

        HarnessConfig config;
        PromptRenderer prompts;
        ClaudeRunner runner;
        try {
            config = ConfigLoader.load(files.harnessYml());
            prompts = new PromptRenderer(config, clock);
            // 비용을 쓰기 전에 템플릿 오류(모르는 변수 등)를 찾는다.
            prompts.checkTemplates();
            runner = new ProcessClaudeRunner(ClaudeExecutable.resolve(config.claude().path()));
        } catch (ConfigException | PromptException | IllegalStateException e) {
            System.err.println("시작하지 못했다: " + e.getMessage());
            return EXIT_STARTUP_ERROR;
        }

        return new Harness(config, files, runner, prompts, clock, console).run();
    }
}
