package todo;

import static org.junit.jupiter.api.Assertions.assertEquals;

import java.io.ByteArrayOutputStream;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class MainTest {

    @Test
    void list_는_상태별_기호를_표시한다(@TempDir Path dir) {
        Path file = dir.resolve("todos.json");
        ByteArrayOutputStream buf = new ByteArrayOutputStream();
        PrintStream out = new PrintStream(buf, true, StandardCharsets.UTF_8);

        Main.run(new String[] {"add", "a"}, file, out, out);
        Main.run(new String[] {"add", "b"}, file, out, out);
        Main.run(new String[] {"add", "c"}, file, out, out);
        Main.run(new String[] {"start", "2"}, file, out, out);
        Main.run(new String[] {"done", "3"}, file, out, out);
        buf.reset();

        Main.run(new String[] {"list"}, file, out, out);

        String expected = String.join(System.lineSeparator(), "[] 1 a", "[=] 2 b", "[O] 3 c")
                + System.lineSeparator();
        assertEquals(expected, buf.toString(StandardCharsets.UTF_8));
    }

    @Test
    void list_는_색상을_켜면_상태마다_다른_색을_쓴다(@TempDir Path dir) {
        Path file = dir.resolve("todos.json");
        ByteArrayOutputStream buf = new ByteArrayOutputStream();
        PrintStream out = new PrintStream(buf, true, StandardCharsets.UTF_8);

        Main.run(new String[] {"add", "a"}, file, out, out);
        Main.run(new String[] {"add", "b"}, file, out, out);
        Main.run(new String[] {"add", "c"}, file, out, out);
        Main.run(new String[] {"start", "2"}, file, out, out);
        Main.run(new String[] {"done", "3"}, file, out, out);
        buf.reset();

        Main.run(new String[] {"list"}, file, out, out, true);

        String reset = "\u001B[0m";
        String expected = String.join(System.lineSeparator(),
                "\u001B[33m[] 1 a" + reset,
                "\u001B[36m[=] 2 b" + reset,
                "\u001B[32m[O] 3 c" + reset)
                + System.lineSeparator();
        assertEquals(expected, buf.toString(StandardCharsets.UTF_8));
    }
}
