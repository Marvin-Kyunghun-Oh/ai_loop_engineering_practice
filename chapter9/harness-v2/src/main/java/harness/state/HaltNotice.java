package harness.state;

/**
 * 하네스가 쓰는 {@code docs/HALT}의 내용 (DESIGN 4.7). 모든 HALT는 네 줄을 쓴다.
 *
 * <pre>
 * 사유: 예산 소진
 * 상세: 누적 $34.10 + 에이전트 1회 상한 $5.00 &gt; 상한 $38.00
 * 사이클: 15 / 역할: generator (실행 전)
 * 재개: 이 파일을 지우고 harness.yml의 limits.max_total_usd를 올린다
 * </pre>
 *
 * @param where 역할 정보. 없으면 null. 예: {@code generator (실행 전)}
 */
public record HaltNotice(String reason, String detail, int cycle, String where, String resume) {

    public String toText() {
        String cycleLine = "사이클: " + cycle + (where == null ? "" : " / 역할: " + where);
        return "사유: " + reason + "\n"
                + "상세: " + detail + "\n"
                + cycleLine + "\n"
                + "재개: " + resume + "\n";
    }
}
