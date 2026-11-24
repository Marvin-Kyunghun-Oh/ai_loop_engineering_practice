package harness.prompt;

/** 프롬프트 파일이 없거나, 치환할 수 없는 변수가 있을 때. 하네스 코드나 프롬프트를 고쳐야 하는 오류다. */
public class PromptException extends RuntimeException {

    public PromptException(String message) {
        super(message);
    }

    public PromptException(String message, Throwable cause) {
        super(message, cause);
    }
}
