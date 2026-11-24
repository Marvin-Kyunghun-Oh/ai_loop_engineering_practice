package harness.claude;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/** 실행 파일 찾기 (DESIGN 5.3). OS와 PATH를 주입해 어느 OS에서든 같은 결과를 확인한다. */
class ClaudeExecutableTest {

    @TempDir
    Path first;

    @TempDir
    Path second;

    @Test
    @DisplayName("Windows: 같은 폴더면 claude.cmd가 claude.exe보다 먼저")
    void cmdBeforeExeInSameDirectory() throws IOException {
        Files.createFile(first.resolve("claude.exe"));
        Files.createFile(first.resolve("claude.cmd"));

        assertEquals(first.resolve("claude.cmd").toString(), ClaudeExecutable.resolve("claude", true, pathOf(first)));
    }

    @Test
    @DisplayName("Windows: PATH 앞쪽 폴더가 먼저 (셸과 같은 순서)")
    void earlierPathDirectoryWins() throws IOException {
        Files.createFile(first.resolve("claude.exe"));
        Files.createFile(second.resolve("claude.cmd"));

        assertEquals(first.resolve("claude.exe").toString(),
                ClaudeExecutable.resolve("claude", true, pathOf(first, second)));
    }

    @Test
    @DisplayName("Windows: 확장자를 적었으면 그 이름만 찾는다")
    void explicitExtension() throws IOException {
        Files.createFile(first.resolve("claude.cmd"));
        Files.createFile(second.resolve("claude.exe"));

        assertEquals(second.resolve("claude.exe").toString(),
                ClaudeExecutable.resolve("claude.exe", true, pathOf(first, second)));
    }

    @Test
    @DisplayName("Windows: 못 찾으면 claude.path를 고치라고 알려 준다")
    void notFound() {
        IllegalStateException e = assertThrows(IllegalStateException.class,
                () -> ClaudeExecutable.resolve("claude", true, pathOf(first)));

        assertEquals("PATH에서 claude를 찾지 못했다. harness.yml의 claude.path에 전체 경로를 적는다.", e.getMessage());
    }

    @Test
    @DisplayName("Windows가 아니면 이름 그대로 (ProcessBuilder가 찾는다)")
    void nonWindows() {
        assertEquals("claude", ClaudeExecutable.resolve("claude", false, "/usr/bin"));
    }

    @Test
    @DisplayName("경로를 직접 적었으면 그대로")
    void explicitPath() {
        assertEquals("C:\\tools\\claude.cmd", ClaudeExecutable.resolve("C:\\tools\\claude.cmd", true, ""));
        assertEquals("/opt/claude/bin/claude", ClaudeExecutable.resolve("/opt/claude/bin/claude", false, ""));
    }

    private static String pathOf(Path... directories) {
        StringBuilder path = new StringBuilder();
        for (Path directory : directories) {
            path.append(directory).append(";");
        }
        return path.toString();
    }
}
