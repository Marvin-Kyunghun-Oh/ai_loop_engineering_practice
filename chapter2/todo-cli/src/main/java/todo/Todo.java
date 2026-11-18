package todo;

/** 불변 할 일 항목. */
public record Todo(int id, String title, Status status) {

    /** 상태만 바꾼 새 항목을 반환한다. */
    public Todo withStatus(Status newStatus) {
        return new Todo(id, title, newStatus);
    }
}
