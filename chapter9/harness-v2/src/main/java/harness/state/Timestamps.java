package harness.state;

import java.time.Clock;
import java.time.OffsetDateTime;
import java.time.format.DateTimeFormatter;
import java.time.temporal.ChronoUnit;

/** JOURNAL·USAGE.csv·콘솔에 쓰는 시각. 예: {@code 2026-11-24T12:26:46+09:00} */
public final class Timestamps {

    private Timestamps() {
    }

    public static String now(Clock clock) {
        return OffsetDateTime.now(clock)
                .truncatedTo(ChronoUnit.SECONDS)
                .format(DateTimeFormatter.ISO_OFFSET_DATE_TIME);
    }
}
