package todo;

/** 할 일의 진행 상태. */
public enum Status {
    TODO("할 일", "[]", "\u001B[33m"),         // 노랑
    IN_PROGRESS("진행 중", "[=]", "\u001B[36m"), // 청록
    DONE("완료", "[O]", "\u001B[32m");          // 초록

    private final String label;
    private final String marker;
    private final String ansiColor;

    Status(String label, String marker, String ansiColor) {
        this.label = label;
        this.marker = marker;
        this.ansiColor = ansiColor;
    }

    /** 상태를 나타내는 ANSI 색상 이스케이프 시퀀스. */
    public String ansiColor() {
        return ansiColor;
    }

    public String label() {
        return label;
    }

    /** list 출력에 쓰는 표시 기호. */
    public String marker() {
        return marker;
    }
}
