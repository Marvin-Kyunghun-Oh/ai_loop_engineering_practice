package harness.decision;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import harness.state.ProjectFiles;
import harness.state.TextFiles;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class DecisionResolverTest {

    @TempDir
    Path projectDir;

    ProjectFiles files;
    DecisionResolver resolver;

    @BeforeEach
    void setUp() {
        files = new ProjectFiles(projectDir);
        files.createDirectories();
        resolver = new DecisionResolver(files);
    }

    @Test
    @DisplayName("decisions 폴더가 없으면 아무것도 하지 않는다")
    void noDirectory() {
        assertEquals(List.of(), resolver.resolve(1));
        assertFalse(files.isHalted());
    }

    @Test
    @DisplayName("선택이 같으면 합의를 적고 선택 파일을 지운다")
    void agree() {
        topic("db", "후보 A, B");
        choice("db.planner.md", "선택: A\n근거 1");
        choice("db.evaluator.md", "선택: A\n근거 2");

        List<String> messages = resolver.resolve(3);

        assertEquals(List.of("결정 합의: db → A"), messages);
        assertTrue(read("db.md").endsWith("\n합의: A (시도 1회)\n"), read("db.md"));
        assertFalse(exists("db.planner.md"));
        assertFalse(exists("db.evaluator.md"));
        assertFalse(files.isHalted());
    }

    @Test
    @DisplayName("선택이 다르면 재시도 안내를 적고 선택 파일을 지운다 (불발 1회)")
    void disagreeFirstTime() {
        topic("db", "후보 A, B");
        choice("db.planner.md", "선택: A");
        choice("db.evaluator.md", "선택: B");

        List<String> messages = resolver.resolve(3);

        assertEquals(List.of("결정 합의 불발(1회): db - 재시도"), messages);
        assertTrue(read("db.md").contains("합의 불발. 후보를 처음부터 다시 나열"), read("db.md"));
        assertFalse(exists("db.planner.md"));
        assertFalse(exists("db.evaluator.md"));
        assertFalse(files.isHalted());
    }

    @Test
    @DisplayName("불발 2회 뒤 다시 같아지면 시도 3회째로 합의한다")
    void agreeAfterTwoFailures() {
        topic("db", "후보 A, B");
        disagree("db");
        resolver.resolve(1);
        disagree("db");
        resolver.resolve(2);
        choice("db.planner.md", "선택: B");
        choice("db.evaluator.md", "선택: B");

        resolver.resolve(3);

        assertTrue(read("db.md").endsWith("\n합의: B (시도 3회)\n"), read("db.md"));
        assertFalse(files.isHalted());
    }

    @Test
    @DisplayName("3회째에도 다르면 HALT하고 두 선택을 담는다")
    void haltAfterThreeFailures() {
        topic("db", "후보 A, B");
        disagree("db");
        resolver.resolve(1);
        disagree("db");
        resolver.resolve(2);
        choice("db.planner.md", "선택: A\n단순해서");
        choice("db.evaluator.md", "선택: B\n확장성 때문에");

        List<String> messages = resolver.resolve(3);

        assertEquals(List.of("결정 합의 불발로 HALT: db"), messages);
        String halt = TextFiles.read(files.halt());
        assertTrue(halt.startsWith("사유: 결정 합의 3회 불발: db\n"), halt);
        assertTrue(halt.contains("[planner]\n선택: A\n단순해서"), halt);
        assertTrue(halt.contains("[evaluator]\n선택: B\n확장성 때문에"), halt);
        assertTrue(halt.contains("사이클: 3\n"), halt);
        assertFalse(exists("db.planner.md"));
    }

    @Test
    @DisplayName("한쪽만 기록했으면 기다린다 (파일을 그대로 둔다)")
    void waitsForOtherSide() {
        topic("db", "후보 A, B");
        choice("db.planner.md", "선택: A");

        assertEquals(List.of(), resolver.resolve(1));

        assertTrue(exists("db.planner.md"));
        assertEquals("후보 A, B", read("db.md"));
    }

    @Test
    @DisplayName("첫 줄 형식이 틀리면 미기록으로 취급한다")
    void malformedChoiceIsUnrecorded() {
        topic("db", "후보 A, B");
        choice("db.planner.md", "A를 고른다\n선택: A");
        choice("db.evaluator.md", "선택: A");

        assertEquals(List.of(), resolver.resolve(1));
        assertTrue(exists("db.evaluator.md"));
    }

    @Test
    @DisplayName("라벨이 비어 있으면 미기록으로 취급한다")
    void blankLabelIsUnrecorded() {
        topic("db", "후보 A, B");
        choice("db.planner.md", "선택:   ");
        choice("db.evaluator.md", "선택:   ");

        assertEquals(List.of(), resolver.resolve(1));
    }

    @Test
    @DisplayName("선택 파일만 있고 주제 파일이 없으면 주제로 보지 않는다")
    void choiceFilesWithoutTopic() {
        choice("db.planner.md", "선택: A");
        choice("db.evaluator.md", "선택: A");

        assertEquals(List.of(), resolver.resolve(1));
        assertTrue(exists("db.planner.md"));
    }

    @Test
    @DisplayName("주제 여러 개는 각각 판정한다")
    void multipleTopics() {
        topic("auth", "후보 A, B");
        topic("db", "후보 A, B");
        choice("auth.planner.md", "선택: A");
        choice("auth.evaluator.md", "선택: A");
        choice("db.planner.md", "선택: A");
        choice("db.evaluator.md", "선택: B");

        List<String> messages = resolver.resolve(1);

        assertEquals(List.of("결정 합의: auth → A", "결정 합의 불발(1회): db - 재시도"), messages);
    }

    // ---- 도우미 ----

    private void topic(String name, String text) {
        TextFiles.write(files.decisionsDir().resolve(name + ".md"), text);
    }

    private void choice(String fileName, String text) {
        TextFiles.write(files.decisionsDir().resolve(fileName), text + "\n");
    }

    private void disagree(String name) {
        choice(name + ".planner.md", "선택: A");
        choice(name + ".evaluator.md", "선택: B");
    }

    private String read(String fileName) {
        return TextFiles.read(files.decisionsDir().resolve(fileName));
    }

    private boolean exists(String fileName) {
        return Files.exists(files.decisionsDir().resolve(fileName));
    }
}
