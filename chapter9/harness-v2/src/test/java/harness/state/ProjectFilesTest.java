package harness.state;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import harness.policy.Role;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

class ProjectFilesTest {

    @TempDir
    Path dir;

    ProjectFiles files;

    @BeforeEach
    void setUp() {
        files = new ProjectFiles(dir);
        files.createDirectories();
    }

    @Test
    @DisplayName("사이클 번호: 파일이 없으면 0, 저장한 값을 다시 읽는다")
    void cycleCount() {
        assertEquals(0, files.readCycleCount());

        files.saveCycleCount(12);

        assertEquals(12, files.readCycleCount());
    }

    @Test
    @DisplayName("사이클 번호가 숫자가 아니면 0으로 되돌리지 않고 예외")
    void brokenCycleCount() throws IOException {
        Files.writeString(files.cycleCount(), "twelve");

        IllegalStateException e = assertThrows(IllegalStateException.class, files::readCycleCount);
        assertTrue(e.getMessage().contains("twelve"), e.getMessage());
    }

    @Test
    @DisplayName("CURRENT: 없음·빈 파일 → empty, 앞뒤 공백과 빈 줄은 무시")
    void readCurrent() throws IOException {
        assertEquals(Optional.empty(), files.readCurrent());

        Files.writeString(files.current(), "  \n");
        assertEquals(Optional.empty(), files.readCurrent());

        Files.writeString(files.current(), "\n  T9a  \n");
        assertEquals(Optional.of("T9a"), files.readCurrent());

        files.deleteCurrent();
        assertFalse(Files.exists(files.current()));
    }

    @ParameterizedTest(name = "올바른 ID: {0}")
    @ValueSource(strings = {"T1", "T9a", "T8rs", "T12"})
    void validTaskIds(String id) {
        assertTrue(ProjectFiles.isValidTaskId(id));
    }

    @ParameterizedTest(name = "틀린 ID: \"{0}\"")
    @ValueSource(strings = {"", "T", "t9", "T9A", "9a", "T9a ", "T9a, T9b", "Ta9"})
    void invalidTaskIds(String id) {
        assertFalse(ProjectFiles.isValidTaskId(id));
    }

    @Test
    @DisplayName("HALT는 네 줄 형식으로 쓴다 (4.7)")
    void writeHalt() throws IOException {
        files.writeHalt(new HaltNotice("예산 소진", "누적 $34.10 + 에이전트 1회 상한 $5.00 > 상한 $38.00",
                15, "generator (실행 전)", "이 파일을 지우고 harness.yml의 limits.max_total_usd를 올린다"));

        assertTrue(files.isHalted());
        assertEquals("""
                사유: 예산 소진
                상세: 누적 $34.10 + 에이전트 1회 상한 $5.00 > 상한 $38.00
                사이클: 15 / 역할: generator (실행 전)
                재개: 이 파일을 지우고 harness.yml의 limits.max_total_usd를 올린다
                """, Files.readString(files.halt()));
    }

    @Test
    @DisplayName("HALT에 역할이 없으면 사이클만 쓴다")
    void writeHaltWithoutRole() throws IOException {
        files.writeHalt(new HaltNotice("CURRENT 누락", "planner가 CURRENT를 쓰지 않았다", 3, null, "확인 후 이 파일을 지운다"));

        assertTrue(Files.readString(files.halt()).contains("사이클: 3\n"));
    }

    @Test
    @DisplayName("DONE을 지운다")
    void deleteDone() throws IOException {
        Files.writeString(files.done(), "");
        assertTrue(files.isDone());

        files.deleteDone();

        assertFalse(files.isDone());
    }

    @Test
    @DisplayName("같은 사이클을 다시 돌면 원본 로그를 덮어쓰지 않고 번호를 붙인다")
    void rawLogFileDoesNotOverwrite() throws IOException {
        Path first = files.newRawLogFile(12, Role.GENERATOR);
        assertEquals("c12-generator.json", first.getFileName().toString());
        Files.writeString(first, "{}");

        Path second = files.newRawLogFile(12, Role.GENERATOR);
        assertEquals("c12-generator-2.json", second.getFileName().toString());
        Files.writeString(second, "{}");

        assertEquals("c12-generator-3.json", files.newRawLogFile(12, Role.GENERATOR).getFileName().toString());
        assertEquals("c12-evaluator.json", files.newRawLogFile(12, Role.EVALUATOR).getFileName().toString());
    }

    @Test
    @DisplayName("원본 로그는 docs/ 밖 .harness/logs/에 둔다")
    void logsAreOutsideDocs() {
        assertFalse(files.logsDir().startsWith(files.docs()));
        assertEquals(dir.toAbsolutePath().normalize().resolve(".harness/logs"), files.logsDir());
    }
}
