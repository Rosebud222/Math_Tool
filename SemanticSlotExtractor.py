@dataclass
class SemanticSearchSlotExtractorConfig:
    enable_rule_override: bool = True


class SemanticSearchSlotExtractor:
    def __init__(
        self,
        llm: ChatModel,
        config: SemanticSearchSlotExtractorConfig | None = None,
    ):
        self.llm = llm
        self.config = config or SemanticSearchSlotExtractorConfig()

    def extract(self, user_query: str) -> SemanticSearchSlotResult:
        user_query = user_query.strip()
        if not user_query:
            raise ValueError("user_query must not be empty")

        raw_result = self._call_llm(user_query)
        result = self._parse_result(raw_result)

        if self.config.enable_rule_override:
            result = self._apply_rule_overrides(user_query, result)

        return result

    def _call_llm(self, user_query: str) -> str:
        messages = [
            {"role": "system", "content": SEMANTIC_SLOT_EXTRACTOR_SYSTEM_PROMPT},
            {"role": "system", "content": SEMANTIC_SLOT_EXTRACTOR_FEWSHOT},
            {
                "role": "user",
                "content": json.dumps(
                    {"user_query": user_query},
                    ensure_ascii=False
                )
            },
        ]
        return self.llm.invoke(messages=messages, temperature=0)

    def _parse_result(self, raw_result: str) -> SemanticSearchSlotResult:
        try:
            data = json.loads(raw_result)
            return SemanticSearchSlotResult.model_validate(data)
        except Exception as e:
            raise ValueError(f"Failed to parse semantic slot extractor output: {raw_result}") from e
