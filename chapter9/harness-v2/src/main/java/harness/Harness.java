package harness;

import harness.claude.AgentRequest;
import harness.claude.AgentResult;
import harness.claude.ClaudeRunner;
import harness.config.HarnessConfig;
import harness.config.HarnessConfig.Limits;
import harness.cost.CostLedger;
import harness.decision.DecisionResolver;
import harness.journal.JournalWriter;
import harness.policy.Role;
import harness.policy.ToolPolicy;
import harness.prompt.PromptProvider;
import harness.state.HaltNotice;
import harness.state.ProjectFiles;
import harness.state.Timestamps;
import java.io.PrintStream;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Clock;
import java.util.Optional;

/**
 * 메인 루프 (DESIGN 6절). planner → generator → evaluator를 사이클 단위로 돌린다.
 *
 * <p>판단(계획·구현·채점)은 에이전트가 한다. 하네스는 순서, 비용 기록, JOURNAL, 예산 차단, 실패 처리를 맡는다.
 *
 * <p>아직 연결하지 않은 것 (DESIGN 8절)
 * <ul>
 *   <li>9단계 TaskArchiver, reviews.csv: 사이클 시작의 아카이브, evaluator 판정을 JOURNAL에 덧붙이기</li>
 *   <li>10단계 Bootstrap: PRD가 없을 때의 대화형 planner. 지금은 PRD가 없으면 종료한다</li>
 * </ul>
 */
public final class Harness {

    public static final int EXIT_OK = 0;
    public static final int EXIT_HALT = 1;

    private static final String RESUME_AFTER_CHECK = "원인을 확인하고 이 파일을 지운 뒤 다시 실행한다";

    private final HarnessConfig config;
    private final ProjectFiles files;
    private final ClaudeRunner runner;
    private final PromptProvider prompts;
    private final ToolPolicy toolPolicy;
    private final JournalWriter journal;
    private final DecisionResolver decisions;
    private final Clock clock;
    private final PrintStream console;

    /** {@link #run()}을 시작할 때 USAGE.csv에서 복원한다. */
    private CostLedger ledger;

    /** ERROR·TIMEOUT이 연속된 횟수. 다른 결과가 나오면 0으로 돌아간다. */
    private int consecutiveErrors;

    /** 직전에 상한에 걸린 항목 ID(planner면 "planner"). 같은 항목에서 다시 걸리면 HALT한다. 사이클을 마치면 지운다. */
    private String lastLimitKey;

    public Harness(HarnessConfig config, ProjectFiles files, ClaudeRunner runner, PromptProvider prompts,
                   Clock clock, PrintStream console) {
        this.config = config;
        this.files = files;
        this.runner = runner;
        this.prompts = prompts;
        this.toolPolicy = new ToolPolicy(config.permissions());
        this.journal = new JournalWriter(files.journal(), clock);
        this.decisions = new DecisionResolver(files);
        this.clock = clock;
        this.console = console;
    }

    /** @return {@link #EXIT_OK}(DONE 또는 최대 반복 도달) 또는 {@link #EXIT_HALT} */
    public int run() {
        files.createDirectories();
        log("작업 디렉터리: " + files.root());

        if (files.isHalted()) {
            // v1은 이 상태에서 planner를 한 번 더 돌린 뒤에야 멈췄다.
            log("docs/HALT가 있다. 내용을 확인하고 파일을 지운 뒤 다시 실행한다.");
            return EXIT_HALT;
        }
        if (!Files.exists(files.prd())) {
            log("docs/PRD.md가 없다. (대화형 부트스트랩은 아직 구현되지 않았다: DESIGN 8절 10단계)");
            return EXIT_HALT;
        }

        Limits limits = config.limits();
        ledger = CostLedger.load(files.usageCsv(), limits.maxTotalUsd(), clock);
        log("누적 비용 " + usd(ledger.total()) + " / 상한 " + usd(limits.maxTotalUsd()));

        int completed = files.readCycleCount();
        if (completed > 0) {
            log("이전 실행에서 " + completed + " 사이클까지 진행했다. 이어서 시작한다.");
        }

        for (int attempt = 1; attempt <= limits.maxIterations(); attempt++) {
            // 중단된 사이클은 카운터를 올리지 않으므로 같은 번호로 다시 돈다 (DESIGN 6절).
            int cycle = files.readCycleCount() + 1;
            CycleEnd end = runCycle(cycle);

            switch (end) {
                case COMPLETED -> {
                    files.saveCycleCount(cycle);
                    log("=== 사이클 " + cycle + " 종료 ===");
                }
                case ABORTED -> log("=== 사이클 " + cycle + " 중단: 같은 번호로 다시 시작한다 ===");
                case DONE -> {
                    files.saveCycleCount(cycle);
                    log("planner가 DONE을 남겼다. 종료.");
                    return EXIT_OK;
                }
                case HALTED_BY_AGENT -> {
                    files.saveCycleCount(cycle);
                    log("에이전트가 HALT를 남겼다. docs/HALT를 확인한다.");
                    return EXIT_HALT;
                }
                case HALTED_BY_HARNESS -> {
                    log("하네스가 HALT했다. docs/HALT를 확인한다.");
                    return EXIT_HALT;
                }
            }
        }

        log("최대 반복 횟수(" + limits.maxIterations() + ")에 도달했다. 종료.");
        return EXIT_OK;
    }

    // ---- 사이클 ----

    /** 사이클이 어떻게 끝났는지. 카운터 저장 여부가 달라진다. */
    private enum CycleEnd {
        /** 세 역할을 모두 마침 → 카운터 저장 */
        COMPLETED,
        /** 상한 도달·실행 오류로 중단 → 카운터 유지, 같은 번호로 재시도 */
        ABORTED,
        /** planner가 DONE을 남김 → 카운터 저장, 종료 */
        DONE,
        /** 에이전트가 HALT를 남김 → 카운터 저장, 종료 (v1과 같음) */
        HALTED_BY_AGENT,
        /** 하네스가 HALT를 씀(예산, 오류 연속, CURRENT 누락 등) → 카운터 유지, 종료 */
        HALTED_BY_HARNESS
    }

    /** 에이전트 1회 실행 후 다음 행동. */
    private enum Next {
        CONTINUE, ABORT_CYCLE, HALT
    }

    private CycleEnd runCycle(int cycle) {
        log("=== 사이클 " + cycle + " 시작 ===");

        // 매 사이클 planner가 PRD와 코드의 간극을 다시 판정하게 한다 (v1과 같음).
        files.deleteDone();
        // 지난 사이클의 CURRENT가 남아 있으면, planner가 새로 쓰지 않아도 generator가 옛 항목으로 돈다.
        files.deleteCurrent();

        // TODO(9단계): TaskArchiver로 끝난 마일스톤을 아카이브한다.

        Next next = runAgent(Role.PLANNER, cycle, null);
        if (next != Next.CONTINUE) {
            return toCycleEnd(next);
        }
        if (files.isDone()) {
            return CycleEnd.DONE;
        }
        if (files.isHalted()) {
            return CycleEnd.HALTED_BY_AGENT;
        }

        Optional<String> current = files.readCurrent();
        if (current.isEmpty()) {
            halt(new HaltNotice("CURRENT 누락",
                    "planner가 docs/CURRENT에 이번 사이클 항목 ID를 쓰지 않았다",
                    cycle, "planner (실행 후)", RESUME_AFTER_CHECK));
            return CycleEnd.HALTED_BY_HARNESS;
        }
        String taskId = current.get();
        if (!ProjectFiles.isValidTaskId(taskId)) {
            halt(new HaltNotice("CURRENT 형식 오류",
                    "docs/CURRENT의 \"" + taskId + "\"가 항목 ID 형식(T 뒤에 숫자, 그 뒤 소문자)이 아니다",
                    cycle, "planner (실행 후)", RESUME_AFTER_CHECK));
            return CycleEnd.HALTED_BY_HARNESS;
        }
        log("이번 사이클 항목: " + taskId);

        next = runAgent(Role.GENERATOR, cycle, taskId);
        if (next != Next.CONTINUE) {
            return toCycleEnd(next);
        }

        next = runAgent(Role.EVALUATOR, cycle, taskId);
        if (next != Next.CONTINUE) {
            return toCycleEnd(next);
        }

        // TODO(9단계): REVIEW 판정을 .harness/reviews.csv에 저장한다.
        // 합의 불발 3회면 DecisionResolver가 HALT를 쓴다. 에이전트가 쓴 HALT와 같이 카운터를 저장한다(v1과 같음).
        decisions.resolve(cycle).forEach(this::log);

        if (files.isHalted()) {
            return CycleEnd.HALTED_BY_AGENT;
        }
        lastLimitKey = null;
        return CycleEnd.COMPLETED;
    }

    private static CycleEnd toCycleEnd(Next next) {
        return switch (next) {
            case ABORT_CYCLE -> CycleEnd.ABORTED;
            case HALT -> CycleEnd.HALTED_BY_HARNESS;
            case CONTINUE -> throw new IllegalArgumentException("CONTINUE는 사이클 종료가 아니다");
        };
    }

    // ---- 에이전트 1회 ----

    /** @param taskId 이번 사이클 항목. planner 실행 때는 아직 모르므로 null */
    private Next runAgent(Role role, int cycle, String taskId) {
        Limits limits = config.limits();
        BigDecimal maxAgentUsd = limits.maxAgentUsd();

        if (!ledger.canAfford(maxAgentUsd)) {
            halt(new HaltNotice("예산 소진",
                    "누적 " + usd(ledger.total()) + " + 에이전트 1회 상한 " + usd(maxAgentUsd)
                            + " > 상한 " + usd(limits.maxTotalUsd()),
                    cycle, role.id() + " (실행 전)",
                    "이 파일을 지우고 harness.yml의 limits.max_total_usd를 올린다"));
            return Next.HALT;
        }

        String model = config.models().forRole(role);
        Path rawLog = files.newRawLogFile(cycle, role);
        AgentRequest request = new AgentRequest(
                role,
                prompts.promptFor(role, cycle),
                model,
                toolPolicy.allowedTools(role),
                toolPolicy.disallowedTools(role),
                toolPolicy.acceptEdits(role),
                maxAgentUsd,
                limits.maxTurnsFor(role),
                limits.agentTimeout(),
                files.root(),
                rawLog);

        log("--- " + role.id() + " 시작 (model=" + model + ") ---");
        AgentResult result = runner.run(request);

        // 오류로 끝났어도 비용과 JOURNAL은 남긴다.
        ledger.record(cycle, role, model, result);
        journal.append(cycle, role, result, null);   // TODO(9단계): evaluator면 REVIEW 판정을 덧붙인다
        log("--- " + role.id() + " 종료: " + result.outcome()
                + " · " + (result.costKnown() ? usd(result.costUsd()) : "$?")
                + " · 누적 " + usd(ledger.total()) + " / " + usd(limits.maxTotalUsd()) + " ---");

        return decideNext(role, cycle, taskId, result, rawLog);
    }

    /** 결과별 처리 (DESIGN 6절 runAgent, B1, 0012). */
    private Next decideNext(Role role, int cycle, String taskId, AgentResult result, Path rawLog) {
        String where = role.id();
        String rawLogText = "원본 로그: " + files.root().relativize(rawLog);

        return switch (result.outcome()) {
            case SUCCESS -> {
                consecutiveErrors = 0;
                yield Next.CONTINUE;
            }
            case BUDGET_LIMIT, TURN_LIMIT -> {
                consecutiveErrors = 0;
                String key = taskId != null ? taskId : role.id();
                if (key.equals(lastLimitKey)) {
                    halt(new HaltNotice("상한 도달 반복",
                            key + "에서 상한 도달이 2회 연속이다 (" + result.subtype() + ": " + result.summary()
                                    + "). " + rawLogText,
                            cycle, where,
                            "항목을 더 작게 나누거나 harness.yml의 limits.max_agent_usd·max_turns를 조정한 뒤 이 파일을 지운다"));
                    yield Next.HALT;
                }
                lastLimitKey = key;
                yield Next.ABORT_CYCLE;
            }
            case INVALID_RESULT -> {
                halt(new HaltNotice("결과 JSON 형식 오류",
                        result.summary() + ". " + rawLogText,
                        cycle, where,
                        "claude CLI 버전과 결과 JSON 필드를 확인하고 하네스를 고친 뒤 이 파일을 지운다"));
                yield Next.HALT;
            }
            case ERROR, TIMEOUT -> {
                consecutiveErrors++;
                int max = config.limits().maxConsecutiveErrors();
                if (consecutiveErrors >= max) {
                    halt(new HaltNotice("실행 오류 " + consecutiveErrors + "회 연속",
                            result.outcome() + ": " + result.summary() + ". " + rawLogText,
                            cycle, where, RESUME_AFTER_CHECK));
                    yield Next.HALT;
                }
                yield Next.ABORT_CYCLE;
            }
        };
    }

    // ---- 도우미 ----

    private void halt(HaltNotice notice) {
        files.writeHalt(notice);
        log("HALT: " + notice.reason() + " - " + notice.detail());
    }

    private void log(String message) {
        console.println("[" + Timestamps.now(clock) + "] " + message);
    }

    private static String usd(BigDecimal amount) {
        return "$" + amount.setScale(2, RoundingMode.HALF_UP).toPlainString();
    }
}
