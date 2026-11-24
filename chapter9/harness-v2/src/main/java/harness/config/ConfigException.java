package harness.config;

/** {@code harness.yml}을 쓸 수 없을 때. 메시지에 문제가 된 키 이름이 들어 있다. */
public class ConfigException extends RuntimeException {

    public ConfigException(String message) {
        super(message);
    }

    public ConfigException(String message, Throwable cause) {
        super(message, cause);
    }
}
