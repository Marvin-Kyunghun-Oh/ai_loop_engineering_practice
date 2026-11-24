package harness.state;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;

/** 하네스가 쓰는 텍스트 파일 입출력. 모두 UTF-8이고, 실패하면 {@link UncheckedIOException}을 던진다. */
public final class TextFiles {

    private TextFiles() {
    }

    /**
     * 파일 끝에 한 줄을 붙인다. 파일이 없으면 만든다.
     * 기존 내용이 줄바꿈으로 끝나지 않으면 줄바꿈을 먼저 넣는다. 사람이나 에이전트가 손으로 고친 파일도 줄이 붙지 않게 하기 위해서다.
     */
    public static void appendLine(Path file, String line) {
        try {
            Files.createDirectories(file.toAbsolutePath().getParent());
            String prefix = needsNewlineBeforeAppend(file) ? "\n" : "";
            Files.writeString(file, prefix + line + "\n", StandardCharsets.UTF_8,
                    StandardOpenOption.CREATE, StandardOpenOption.APPEND);
        } catch (IOException e) {
            throw new UncheckedIOException("파일에 쓰지 못했다: " + file, e);
        }
    }

    public static String read(Path file) {
        try {
            return Files.readString(file, StandardCharsets.UTF_8);
        } catch (IOException e) {
            throw new UncheckedIOException("파일을 읽지 못했다: " + file, e);
        }
    }

    public static void write(Path file, String content) {
        try {
            Files.createDirectories(file.toAbsolutePath().getParent());
            Files.writeString(file, content, StandardCharsets.UTF_8);
        } catch (IOException e) {
            throw new UncheckedIOException("파일에 쓰지 못했다: " + file, e);
        }
    }

    public static void deleteIfExists(Path file) {
        try {
            Files.deleteIfExists(file);
        } catch (IOException e) {
            throw new UncheckedIOException("파일을 지우지 못했다: " + file, e);
        }
    }

    private static boolean needsNewlineBeforeAppend(Path file) throws IOException {
        if (!Files.exists(file) || Files.size(file) == 0) {
            return false;
        }
        byte[] bytes = Files.readAllBytes(file);
        return bytes[bytes.length - 1] != '\n';
    }
}
