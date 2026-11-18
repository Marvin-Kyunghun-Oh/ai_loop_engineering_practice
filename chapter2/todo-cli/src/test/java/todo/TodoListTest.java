package todo;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.List;
import org.junit.jupiter.api.Test;

class TodoListTest {

    @Test
    void add_는_id를_증가시키고_TODO_상태로_만든다() {
        TodoList list = new TodoList();
        Todo a = list.add("우유 사기");
        Todo b = list.add("운동");

        assertEquals(1, a.id());
        assertEquals(2, b.id());
        assertEquals(Status.TODO, a.status());
        assertEquals("우유 사기", a.title());
    }

    @Test
    void add_는_빈_제목을_거부한다() {
        TodoList list = new TodoList();
        assertThrows(IllegalArgumentException.class, () -> list.add("  "));
        assertThrows(IllegalArgumentException.class, () -> list.add(null));
    }

    @Test
    void start_는_TODO를_진행중으로_바꾼다() {
        TodoList list = new TodoList();
        list.add("작업");
        assertEquals(Status.IN_PROGRESS, list.start(1).status());
    }

    @Test
    void start_는_없는_id와_이미_시작된_항목을_거부한다() {
        TodoList list = new TodoList();
        list.add("작업");
        list.start(1);

        assertThrows(IllegalArgumentException.class, () -> list.start(99));
        assertThrows(IllegalStateException.class, () -> list.start(1));
    }

    @Test
    void done_은_TODO와_진행중_모두_완료로_바꾼다() {
        TodoList list = new TodoList();
        list.add("a");
        list.add("b");
        list.start(2);

        assertEquals(Status.DONE, list.done(1).status());
        assertEquals(Status.DONE, list.done(2).status());
    }

    @Test
    void done_은_없는_id와_이미_완료된_항목을_거부한다() {
        TodoList list = new TodoList();
        list.add("a");
        list.done(1);

        assertThrows(IllegalArgumentException.class, () -> list.done(99));
        assertThrows(IllegalStateException.class, () -> list.done(1));
        assertThrows(IllegalStateException.class, () -> list.start(1));
    }

    @Test
    void list_는_추가_순서를_유지하고_빈_목록도_처리한다() {
        TodoList list = new TodoList();
        assertTrue(list.list().isEmpty());

        list.add("첫째");
        list.add("둘째");
        assertEquals(List.of("첫째", "둘째"), list.list().stream().map(Todo::title).toList());
    }

    @Test
    void list_는_읽기_전용이다() {
        TodoList list = new TodoList();
        list.add("a");
        assertThrows(UnsupportedOperationException.class, () -> list.list().clear());
    }

    @Test
    void 저장된_목록에서_복원하면_id가_이어진다() {
        TodoList list = new TodoList(List.of(new Todo(5, "기존", Status.DONE)));
        assertEquals(6, list.add("새 항목").id());
    }
}
