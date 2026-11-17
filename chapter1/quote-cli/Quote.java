import java.io.IOException;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Random;

public class Quote {
    private static final Path QUOTES_FILE = Path.of("quotes.json");

    public static void main(String[] args) throws IOException {
        PrintStream out = new PrintStream(System.out, true, StandardCharsets.UTF_8);
        boolean list = false;
        for (String a : args) {
            if (a.equals("--list") || a.equals("-list")) {
                list = true;
            } else {
                PrintStream err = new PrintStream(System.err, true, StandardCharsets.UTF_8);
                err.println("알 수 없는 인수: " + a);
                err.println("사용법: java Quote.java [--list]");
                System.exit(2);
            }
        }

        List<String> quotes = loadQuotes();
        if (quotes.isEmpty()) {
            out.println("명언이 없습니다.");
            return;
        }
        if (list) {
            for (int i = 0; i < quotes.size(); i++) {
                out.println((i + 1) + ". " + quotes.get(i));
            }
        } else {
            out.println(quotes.get(new Random().nextInt(quotes.size())));
        }
    }

    // quotes.json은 문자열 배열(["...", "..."])이므로 외부 라이브러리 없이 간단히 파싱한다.
    private static List<String> loadQuotes() throws IOException {
        String json = Files.readString(QUOTES_FILE, StandardCharsets.UTF_8);
        List<String> result = new ArrayList<>();
        StringBuilder sb = null;
        for (int i = 0; i < json.length(); i++) {
            char c = json.charAt(i);
            if (sb == null) {
                if (c == '"') sb = new StringBuilder();
            } else if (c == '\\') {
                char n = json.charAt(++i);
                switch (n) {
                    case 'n' -> sb.append('\n');
                    case 't' -> sb.append('\t');
                    case 'u' -> {
                        sb.append((char) Integer.parseInt(json.substring(i + 1, i + 5), 16));
                        i += 4;
                    }
                    default -> sb.append(n);
                }
            } else if (c == '"') {
                result.add(sb.toString());
                sb = null;
            } else {
                sb.append(c);
            }
        }
        return result;
    }
}
