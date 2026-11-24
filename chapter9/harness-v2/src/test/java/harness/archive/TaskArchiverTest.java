package harness.archive;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import harness.archive.TaskArchiver.ArchivedMilestone;
import harness.archive.TaskArchiver.Result;
import harness.review.ReviewRecord;
import java.util.Map;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

class TaskArchiverTest {

    private static final Map<String, ReviewRecord> REVIEWS = Map.of(
            "T1", new ReviewRecord("T1", 1, "PASS 12/12", "설정은 harness.yml 하나"),
            "T2", new ReviewRecord("T2", 2, "조건부 7/12", "-"));

    private static final String TWO_MILESTONES = """
            # TASKS

            - 기준: docs/PLAN.md

            ## M1. 기반

            - [x] T1. 설정 로더
              - 내용
                - Settings를 만든다.
              - acceptance
                - 테스트 통과
              - touch: `src/config.py`

            - [x] T2. 로더 보강 (T1 메모 해소)
              - 내용
                - 오류 메시지를 고친다.
              - touch: `src/config.py`

            ## M2. 수집

            - [ ] T3. 피드 읽기
              - 내용
                - ...
            """;

    @Test
    @DisplayName("끝난 마일스톤 뒤에 항목이 있는 섹션이면 요약 줄만 남기고 상세를 옮긴다")
    void archivesClosedMilestone() {
        Result result = TaskArchiver.archive(TWO_MILESTONES, REVIEWS);

        assertEquals("""
                # TASKS

                - 기준: docs/PLAN.md

                ## M1. 기반

                - [x] T1. 설정 로더 — PASS 12/12 · 결정: 설정은 harness.yml 하나 · 상세: archive/TASKS-M1.md#T1

                - [x] T2. 로더 보강 (T1 메모 해소) — 조건부 7/12 · 결정: - · 상세: archive/TASKS-M1.md#T2

                ## M2. 수집

                - [ ] T3. 피드 읽기
                  - 내용
                    - ...
                """, result.tasksText());

        assertEquals(1, result.archived().size());
        ArchivedMilestone m1 = result.archived().get(0);
        assertEquals(1, m1.number());
        assertEquals("TASKS-M1.md", m1.fileName());
        assertEquals("""
                ## M1. 기반

                - [x] T1. 설정 로더
                  - 내용
                    - Settings를 만든다.
                  - acceptance
                    - 테스트 통과
                  - touch: `src/config.py`

                - [x] T2. 로더 보강 (T1 메모 해소)
                  - 내용
                    - 오류 메시지를 고친다.
                  - touch: `src/config.py`
                """, m1.toArchiveText());
    }

    @Test
    @DisplayName("마지막 마일스톤은 전부 끝나도 옮기지 않는다")
    void lastMilestoneStays() {
        String text = """
                ## M1. 기반

                - [x] T1. 설정 로더
                  - 내용
                """;

        Result result = TaskArchiver.archive(text, REVIEWS);

        assertEquals(text, result.tasksText());
        assertTrue(result.archived().isEmpty());
    }

    @Test
    @DisplayName("다음 섹션이 있어도 항목이 없으면 옮기지 않는다 (M2에 T9a가 추가되던 v1 사례)")
    void nextSectionWithoutItems() {
        String text = """
                ## M1. 기반

                - [x] T1. 설정 로더

                ## M2. 수집

                (아직 항목 없음)
                """;

        assertEquals(text, TaskArchiver.archive(text, REVIEWS).tasksText());
    }

    @Test
    @DisplayName("미완료 항목이 하나라도 있으면 옮기지 않는다")
    void unfinishedItemBlocks() {
        String text = """
                ## M1. 기반

                - [x] T1. 설정 로더
                - [ ] T2. 보강

                ## M2. 수집

                - [ ] T3. 피드
                """;

        assertTrue(TaskArchiver.archive(text, REVIEWS).archived().isEmpty());
    }

    @Test
    @DisplayName("항목 ID가 없는 항목이 있으면 그 섹션은 옮기지 않는다")
    void itemWithoutIdBlocks() {
        String text = """
                ## M1. 기반

                - [x] 설정 로더

                ## M2. 수집

                - [ ] T3. 피드
                """;

        assertTrue(TaskArchiver.archive(text, REVIEWS).archived().isEmpty());
    }

    @Test
    @DisplayName("판정 정보가 없는 항목은 -로 쓴다")
    void missingReview() {
        String text = """
                ## M1. 기반

                - [x] T7. 판정 없는 항목
                  - 내용

                ## M2. 수집

                - [ ] T8. 다음
                """;

        Result result = TaskArchiver.archive(text, Map.of());

        assertTrue(result.tasksText().contains(
                "- [x] T7. 판정 없는 항목 — - · 결정: - · 상세: archive/TASKS-M1.md#T7"), result.tasksText());
    }

    @Test
    @DisplayName("이미 요약 줄이 된 항목은 다시 옮기지 않는다 (같은 입력에 두 번 불러도 같다)")
    void idempotent() {
        Result first = TaskArchiver.archive(TWO_MILESTONES, REVIEWS);

        Result second = TaskArchiver.archive(first.tasksText(), REVIEWS);

        assertEquals(first.tasksText(), second.tasksText());
        assertTrue(second.archived().isEmpty());
    }

    @Test
    @DisplayName("요약 줄 사이에 새 완료 항목이 생기면 그 항목만 옮긴다")
    void newItemInArchivedMilestone() {
        String text = """
                ## M1. 기반

                - [x] T1. 설정 로더 — PASS 12/12 · 결정: - · 상세: archive/TASKS-M1.md#T1

                - [x] T9. 뒤늦게 추가된 항목
                  - 내용

                ## M2. 수집

                - [ ] T3. 피드
                """;

        Result result = TaskArchiver.archive(text, Map.of());

        assertEquals(1, result.archived().size());
        assertTrue(result.archived().get(0).body().startsWith("- [x] T9. 뒤늦게 추가된 항목\n  - 내용\n"));
        assertTrue(result.tasksText().contains(
                "- [x] T1. 설정 로더 — PASS 12/12 · 결정: - · 상세: archive/TASKS-M1.md#T1\n"));
    }

    @Test
    @DisplayName("마일스톤이 여럿 끝났으면 각각 자기 파일로 옮긴다")
    void severalMilestones() {
        String text = """
                ## M1. 기반

                - [x] T1. 가

                ## M2. 수집

                - [x] T2. 나

                ## M3. 화면

                - [ ] T3. 다
                """;

        Result result = TaskArchiver.archive(text, REVIEWS);

        assertEquals(2, result.archived().size());
        assertEquals("TASKS-M1.md", result.archived().get(0).fileName());
        assertEquals("TASKS-M2.md", result.archived().get(1).fileName());
        assertTrue(result.tasksText().contains("상세: archive/TASKS-M2.md#T2"), result.tasksText());
    }

    @Test
    @DisplayName("CRLF와 끝 줄바꿈 유무를 유지한다")
    void keepsLineSeparators() {
        String text = "## M1. 기반\r\n\r\n- [x] T1. 가\r\n  - 내용\r\n\r\n## M2. 수집\r\n\r\n- [ ] T2. 나";

        String out = TaskArchiver.archive(text, Map.of()).tasksText();

        assertEquals("## M1. 기반\r\n\r\n- [x] T1. 가 — - · 결정: - · 상세: archive/TASKS-M1.md#T1\r\n\r\n"
                + "## M2. 수집\r\n\r\n- [ ] T2. 나", out);
    }

    @Test
    @DisplayName("마일스톤이 아닌 ## 제목은 옮기지 않고 구분자로만 쓴다")
    void nonMilestoneHeader() {
        String text = """
                ## M1. 기반

                - [x] T1. 가

                ## 메모

                - [x] T2. 나

                ## M2. 수집

                - [ ] T3. 다
                """;

        Result result = TaskArchiver.archive(text, Map.of());

        assertEquals(1, result.archived().size());
        assertEquals(1, result.archived().get(0).number());
        assertTrue(result.tasksText().contains("- [x] T2. 나\n"), "## 메모 섹션의 항목은 그대로");
    }
}
