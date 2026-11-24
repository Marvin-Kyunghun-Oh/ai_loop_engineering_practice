package harness.claude;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Locale;

/**
 * {@code harness.yml}의 {@code claude.path}를 실제로 실행할 경로로 바꾼다 (DESIGN 5.3).
 *
 * <p>v1은 Windows에서 {@code claude}라는 이름만으로 실행하다 실패했다(커밋 0c8e5d8).
 * npm으로 설치하면 실행 파일이 {@code claude.cmd}이고, {@code ProcessBuilder}는 확장자를 붙여 찾지 않기 때문이다.
 * 그래서 Windows에서는 PATH를 직접 뒤져 {@code claude.cmd}, {@code claude.exe}, {@code claude} 순으로 찾는다.
 */
public final class ClaudeExecutable {

    private static final List<String> WINDOWS_EXTENSIONS = List.of(".cmd", ".exe", "");

    private ClaudeExecutable() {
    }

    /** 현재 OS와 PATH 환경 변수로 찾는다. */
    public static String resolve(String configuredPath) {
        boolean windows = System.getProperty("os.name", "").toLowerCase(Locale.ROOT).startsWith("windows");
        return resolve(configuredPath, windows, System.getenv("PATH"));
    }

    /**
     * @param configuredPath {@code claude.path} 값
     * @param windows        Windows인지 (테스트에서 주입)
     * @param pathEnv        PATH 환경 변수 값 (테스트에서 주입)
     */
    static String resolve(String configuredPath, boolean windows, String pathEnv) {
        // 경로를 직접 적었으면 그대로 쓴다.
        if (configuredPath.contains("/") || configuredPath.contains("\\")) {
            return configuredPath;
        }
        // Windows가 아니면 ProcessBuilder가 PATH에서 찾는다.
        if (!windows) {
            return configuredPath;
        }

        boolean hasExtension = configuredPath.contains(".");
        List<String> extensions = hasExtension ? List.of("") : WINDOWS_EXTENSIONS;
        String[] directories = pathEnv == null ? new String[0] : pathEnv.split(";");

        // 셸과 같은 순서로 찾는다. PATH 앞쪽 폴더가 먼저이고, 같은 폴더 안에서는 .cmd → .exe → 확장자 없음 순이다.
        for (String directory : directories) {
            if (directory.isBlank()) {
                continue;
            }
            for (String extension : extensions) {
                Path candidate = Path.of(directory.strip()).resolve(configuredPath + extension);
                if (Files.isRegularFile(candidate)) {
                    return candidate.toAbsolutePath().toString();
                }
            }
        }
        throw new IllegalStateException("PATH에서 " + configuredPath + "를 찾지 못했다. "
                + "harness.yml의 claude.path에 전체 경로를 적는다.");
    }
}
