package todo;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.reflect.TypeToken;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.lang.reflect.Type;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

/** todos.json 파일 읽기/쓰기를 담당한다. */
public class TodoStore {

    private static final Type LIST_TYPE = new TypeToken<List<TodoDto>>() {}.getType();

    /** Gson이 record를 직접 다루지 않도록 쓰는 단순 전송 객체. */
    private static class TodoDto {
        int id;
        String title;
        Status status;
    }

    private final Path path;
    private final Gson gson = new GsonBuilder().setPrettyPrinting().create();

    public TodoStore(Path path) {
        this.path = path;
    }

    /** 파일이 없으면 빈 목록을 반환한다. */
    public TodoList load() {
        if (!Files.exists(path)) {
            return new TodoList();
        }
        try {
            String json = Files.readString(path, StandardCharsets.UTF_8);
            List<TodoDto> dtos = gson.fromJson(json, LIST_TYPE);
            if (dtos == null) {
                return new TodoList();
            }
            return new TodoList(dtos.stream()
                    .map(d -> new Todo(d.id, d.title, d.status))
                    .toList());
        } catch (IOException e) {
            throw new UncheckedIOException("파일을 읽을 수 없습니다: " + path, e);
        }
    }

    public void save(TodoList list) {
        List<TodoDto> dtos = list.list().stream().map(t -> {
            TodoDto d = new TodoDto();
            d.id = t.id();
            d.title = t.title();
            d.status = t.status();
            return d;
        }).toList();
        try {
            Files.writeString(path, gson.toJson(dtos, LIST_TYPE), StandardCharsets.UTF_8);
        } catch (IOException e) {
            throw new UncheckedIOException("파일을 쓸 수 없습니다: " + path, e);
        }
    }
}
