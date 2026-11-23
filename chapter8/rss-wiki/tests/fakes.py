from rss_wiki.pipeline.llm import LLMResponse


class FakeLLM:
    """complete_json / complete_text 응답을 미리 정해 두는 가짜 LLM. 항목이 예외면 던진다."""

    def __init__(self, json_responses=(), text_responses=(), attempts=1):
        self._json = list(json_responses)
        self._text = list(text_responses)
        self.attempts = attempts
        self.json_prompts: list[str] = []
        self.text_prompts: list[str] = []

    async def complete_json(self, prompt):
        self.json_prompts.append(prompt)
        item = self._json.pop(0) if len(self._json) > 1 or not callable(self._json[0]) else self._json[0](prompt)
        if isinstance(item, BaseException):
            raise item
        return LLMResponse(item, self.attempts)

    async def complete_text(self, prompt):
        self.text_prompts.append(prompt)
        item = self._text.pop(0) if len(self._text) > 1 or not callable(self._text[0]) else self._text[0](prompt)
        if isinstance(item, BaseException):
            raise item
        return LLMResponse(item, self.attempts)
