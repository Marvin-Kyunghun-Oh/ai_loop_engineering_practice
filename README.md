# 요즘 AI 루프 엔지니어링 ... 책의 실습 로그
> 요즘 AI 루프 엔지니어링, 클로드 코드, 스킬, MCP, 훅, 컨텍스트, 하네스, 리뷰, 오케스트레이션, LLMOps, Langfuse 

### 1. quote-cli
> `chapter1/quote-cli`
- 명언을 한 줄 출력해주는 자바 애플리케이션

#### `/code-review`
- 코드 품질, 누락된 예외, 테스트 커버리지, 문서 일관성의 관점에서 품질을 피드백

### 2. todo-cli
> `chapter2/todo-cli`
- CLI로 할 일을 등록하고 옮기는 자바 애플리케이션

#### `에이전트 루프`
  - `[컨텍스트 수집 -> 작업수행 -> 결과 검증]`을 반복.
  
#### `프롬프트 캐싱`
```
claude -p "todos.json 스키마를 한 줄로 설명하시오" --output-format json
```

### 3. skills-example
> `chapter3/skills-example/task-keeper`

#### 스킬 생성하여 워크플로우 반자동화
1. create-issue : 고쳐야 할 버그나 추가 작업을 이슈로 생성 
2. git-commit : 이슈를 수정하는 과정에서 발생한 코드 변경을 작은 단위로 저장
3. create-pr : 내 변경을 원본과 합치기 전, 검토를 요청하는 단계
4. review-pr : (검토를 요청받은 사람이) 변경에 대한 피드백을 남기는 단계.
5. apply-pr-review : 피드백을 처리하는 단계 (코드 수정, 기록 추가)
- commit-and-pr : `git-commit` + `create-pr`