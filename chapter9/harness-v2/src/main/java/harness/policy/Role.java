package harness.policy;

/** 에이전트 역할. {@link #id()}는 파일 이름·CSV·JOURNAL에 쓰는 소문자 이름이다. */
public enum Role {
    PLANNER("planner"),
    GENERATOR("generator"),
    EVALUATOR("evaluator");

    private final String id;

    Role(String id) {
        this.id = id;
    }

    public String id() {
        return id;
    }
}
