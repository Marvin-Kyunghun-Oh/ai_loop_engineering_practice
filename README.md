# 요즘 AI 루프 엔지니어링 ... 책의 실습 로그
> 요즘 AI 루프 엔지니어링, 클로드 코드, 스킬, MCP, 훅, 컨텍스트, 하네스, 리뷰, 오케스트레이션, LLMOps, Langfuse 

### 1. quote-cli
> `chapter1/quote-cli`
- 명언을 한 줄 출력해주는 자바 애플리케이션

#### `/code-review`
- 코드 품질, 누락된 예외, 테스트 커버리지, 문서 일관성의 관점에서 품질을 피드백

### 2. todo-cli
> `chapter1/todo-cli`
- CLI로 할 일을 등록하고 옮기는 자바 애플리케이션

#### `에이전트 루프`
  - `[컨텍스트 수집 -> 작업수행 -> 결과 검증]`을 반복.
  
#### `프롬프트 캐싱`
```
claude -p "todos.json 스키마를 한 줄로 설명하시오" --output-format json
```