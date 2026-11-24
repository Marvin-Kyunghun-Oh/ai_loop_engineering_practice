package harness.claude;

import harness.state.TextFiles;
import java.io.IOException;
import java.lang.ProcessBuilder.Redirect;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.TimeUnit;

/**
 * {@code claude -p}를 별도 프로세스로 실행한다 (DESIGN 5.2).
 *
 * <ul>
 *   <li><b>프롬프트는 표준 입력으로 넘긴다.</b> Windows의 {@code claude.cmd}는 cmd.exe를 거치는데,
 *       cmd.exe의 명령줄 한도(약 8,000자)를 치환된 프롬프트가 넘을 수 있기 때문이다.
 *       넘긴 프롬프트는 원본 로그 옆에 {@code c1-planner.prompt.md}로 남는다. 치환되지 않은 {@code {{...}}} 확인에 쓴다.</li>
 *   <li>표준 출력(결과 JSON)은 원본 로그 파일로 바로 보낸 뒤 파싱한다 (D2). 표준 에러는 콘솔로 흘린다.</li>
 *   <li>시간을 넘기면 자식 프로세스까지 모두 끝내고 TIMEOUT을 돌려준다 (B2).</li>
 *   <li>종료 코드로 판정하지 않는다. 상한 도달과 오류가 모두 1이기 때문이다. 결과 JSON이 없을 때만 참고로 덧붙인다.</li>
 * </ul>
 */
public final class ProcessClaudeRunner implements ClaudeRunner {

    private final String executable;
    private final ResultParser parser = new ResultParser();

    /** @param executable {@link ClaudeExecutable#resolve}로 찾은 실행 파일 */
    public ProcessClaudeRunner(String executable) {
        this.executable = executable;
    }

    @Override
    public AgentResult run(AgentRequest request) {
        Path rawLog = request.rawLogFile();
        Path promptFile = promptFileFor(rawLog);
        TextFiles.write(promptFile, request.prompt());

        ProcessBuilder builder = new ProcessBuilder(buildCommand(request))
                .directory(request.workDir().toFile())
                .redirectInput(promptFile.toFile())
                .redirectOutput(rawLog.toFile())
                .redirectError(Redirect.INHERIT);

        Process process;
        try {
            process = builder.start();
        } catch (IOException e) {
            return AgentResult.failure(Outcome.ERROR, "claude를 실행하지 못했다: " + e.getMessage());
        }

        try {
            boolean finished = process.waitFor(request.timeout().toMillis(), TimeUnit.MILLISECONDS);
            if (!finished) {
                killProcessTree(process);
                return AgentResult.failure(Outcome.TIMEOUT,
                        "제한 시간 " + describe(request.timeout()) + "을 넘겨 종료했다");
            }
        } catch (InterruptedException e) {
            killProcessTree(process);
            Thread.currentThread().interrupt();
            return AgentResult.failure(Outcome.ERROR, "하네스가 중단되어 claude를 종료했다");
        }

        String stdout = Files.exists(rawLog) ? TextFiles.read(rawLog) : "";
        AgentResult result = parser.parse(stdout);
        if (result.outcome() == Outcome.ERROR && result.subtype() == null) {
            // 결과 JSON이 없거나 깨졌을 때는 종료 코드가 원인을 찾는 단서다.
            return AgentResult.failure(Outcome.ERROR, result.summary() + " (종료 코드 " + process.exitValue() + ")");
        }
        return result;
    }

    @Override
    public void runInteractive(AgentRequest request) {
        throw new UnsupportedOperationException("대화형 부트스트랩은 DESIGN 8절 10단계에서 구현한다");
    }

    /**
     * {@code claude -p --output-format json --model ... --max-budget-usd ... [--max-turns n]
     * [--permission-mode acceptEdits] --allowedTools ... [--disallowedTools ...]}
     *
     * <p>도구 목록은 여러 값을 받는 옵션이라 맨 뒤에 둔다.
     */
    List<String> buildCommand(AgentRequest request) {
        List<String> command = new ArrayList<>();
        command.add(executable);
        command.add("-p");
        command.add("--output-format");
        command.add("json");
        command.add("--model");
        command.add(request.model());
        command.add("--max-budget-usd");
        command.add(request.maxBudgetUsd().toPlainString());
        if (request.maxTurns() != null) {
            command.add("--max-turns");
            command.add(request.maxTurns().toString());
        }
        if (request.acceptEdits()) {
            command.add("--permission-mode");
            command.add("acceptEdits");
        }
        if (!request.allowedTools().isEmpty()) {
            command.add("--allowedTools");
            command.addAll(request.allowedTools());
        }
        if (!request.disallowedTools().isEmpty()) {
            command.add("--disallowedTools");
            command.addAll(request.disallowedTools());
        }
        return command;
    }

    private static String describe(Duration timeout) {
        return timeout.toMinutes() > 0 ? timeout.toMinutes() + "분" : timeout.toSeconds() + "초";
    }

    /** {@code c1-planner.json} → {@code c1-planner.prompt.md} */
    static Path promptFileFor(Path rawLog) {
        String name = rawLog.getFileName().toString();
        String base = name.endsWith(".json") ? name.substring(0, name.length() - ".json".length()) : name;
        return rawLog.resolveSibling(base + ".prompt.md");
    }

    /**
     * 자식 프로세스까지 끝낸다. claude.cmd는 cmd.exe가 node를 띄우므로 부모만 끝내면 node가 남는다.
     * 부모가 먼저 죽으면 자식 목록을 얻을 수 없으므로 목록부터 모은다.
     */
    private static void killProcessTree(Process process) {
        List<ProcessHandle> descendants = process.descendants().toList();
        descendants.forEach(ProcessHandle::destroyForcibly);
        process.destroyForcibly();
        try {
            process.waitFor(10, TimeUnit.SECONDS);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }
}
