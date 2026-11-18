package todo;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/** 할 일 목록을 조작하는 순수 로직. 파일/콘솔 접근은 하지 않는다. */
public class TodoList {

    private final List<Todo> items;

    public TodoList() {
        this(List.of());
    }

    public TodoList(List<Todo> initial) {
        this.items = new ArrayList<>(initial);
    }

    /** 새 항목을 추가한다. id는 현재 최대 id + 1이다. */
    public Todo add(String title) {
        if (title == null || title.isBlank()) {
            throw new IllegalArgumentException("제목이 비어 있습니다.");
        }
        int nextId = items.stream().mapToInt(Todo::id).max().orElse(0) + 1;
        Todo todo = new Todo(nextId, title.strip(), Status.TODO);
        items.add(todo);
        return todo;
    }

    /** 항목을 진행 중으로 바꾼다. TODO 상태에서만 가능하다. */
    public Todo start(int id) {
        int index = indexOf(id);
        Todo current = items.get(index);
        if (current.status() != Status.TODO) {
            throw new IllegalStateException(
                    "이미 '" + current.status().label() + "' 상태라 시작할 수 없습니다: " + id);
        }
        return replace(index, current.withStatus(Status.IN_PROGRESS));
    }

    /** 항목을 완료로 바꾼다. 이미 완료된 항목은 오류. */
    public Todo done(int id) {
        int index = indexOf(id);
        Todo current = items.get(index);
        if (current.status() == Status.DONE) {
            throw new IllegalStateException("이미 완료된 항목입니다: " + id);
        }
        return replace(index, current.withStatus(Status.DONE));
    }

    /** 추가된 순서대로의 읽기 전용 목록. */
    public List<Todo> list() {
        return Collections.unmodifiableList(items);
    }

    private int indexOf(int id) {
        for (int i = 0; i < items.size(); i++) {
            if (items.get(i).id() == id) {
                return i;
            }
        }
        throw new IllegalArgumentException("존재하지 않는 id입니다: " + id);
    }

    private Todo replace(int index, Todo updated) {
        items.set(index, updated);
        return updated;
    }
}
