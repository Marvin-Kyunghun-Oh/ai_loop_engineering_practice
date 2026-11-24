package harness.review;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import harness.state.TextFiles;
import java.nio.file.Path;
import java.util.List;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class ReviewStoreTest {

    @TempDir
    Path dir;

    @Test
    @DisplayName("파일이 없으면 빈 맵")
    void missingFile() {
        assertTrue(new ReviewStore(dir.resolve("reviews.csv")).loadLatest().isEmpty());
    }

    @Test
    @DisplayName("저장하면 머리줄과 한 줄이 생기고 다시 읽을 수 있다")
    void saveAndLoad() {
        Path csv = dir.resolve(".harness/reviews.csv");
        ReviewStore store = new ReviewStore(csv);

        store.save(new ReviewRecord("T8s", 35, "PASS 11/12", "깊이 태그별"));

        assertEquals(List.of("task_id,cycle,verdict,key_decision", "T8s,35,PASS 11/12,깊이 태그별"),
                TextFiles.read(csv).lines().toList());
        assertEquals(new ReviewRecord("T8s", 35, "PASS 11/12", "깊이 태그별"), store.loadLatest().get("T8s"));
    }

    @Test
    @DisplayName("쉼표와 큰따옴표가 든 값도 그대로 돌아온다")
    void quoting() {
        ReviewStore store = new ReviewStore(dir.resolve("reviews.csv"));
        String decision = "태그, 속성은 \"소문자\"로 비교";

        store.save(new ReviewRecord("T1", 1, "PASS 9/9", decision));

        assertEquals(decision, store.loadLatest().get("T1").keyDecision());
    }

    @Test
    @DisplayName("같은 항목을 다시 평가하면 마지막 줄이 이긴다")
    void lastWins() {
        ReviewStore store = new ReviewStore(dir.resolve("reviews.csv"));
        store.save(new ReviewRecord("T1", 1, "FAIL 4/12", "-"));
        store.save(new ReviewRecord("T2", 2, "PASS 12/12", "-"));
        store.save(new ReviewRecord("T1", 3, "PASS 10/12", "재작업"));

        assertEquals(2, store.loadLatest().size());
        assertEquals("PASS 10/12", store.loadLatest().get("T1").verdict());
        assertEquals(3, store.loadLatest().get("T1").cycle());
    }

    @Test
    @DisplayName("깨진 파일은 조용히 건너뛰지 않고 예외")
    void corrupted() {
        Path csv = dir.resolve("reviews.csv");

        TextFiles.write(csv, "다른,머리줄\n");
        assertThrows(IllegalStateException.class, () -> new ReviewStore(csv).loadLatest());

        TextFiles.write(csv, "task_id,cycle,verdict,key_decision\nT1,1,PASS\n");
        assertThrows(IllegalStateException.class, () -> new ReviewStore(csv).loadLatest());

        TextFiles.write(csv, "task_id,cycle,verdict,key_decision\nT1,x,PASS 1/1,-\n");
        assertThrows(IllegalStateException.class, () -> new ReviewStore(csv).loadLatest());
    }
}
