import json
from dataclasses import dataclass

@dataclass
class QueryClassifierConfig:
    confidence_floor_for_pure_sql_upgrade: float = 0.75
    enable_rule_override: bool = True


class QueryClassifier:
    def __init__(self, llm: ChatModel, config: QueryClassifierConfig | None = None):
        self.llm = llm
        self.config = config or QueryClassifierConfig()

    def classify(self, user_query: str) -> QueryClassification:
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
            {"role": "system", "content": CLASSIFIER_SYSTEM_PROMPT},
            {"role": "system", "content": CLASSIFIER_FEWSHOT},
            {"role": "user", "content": f"입력: {user_query}\n출력:"},
        ]
        return self.llm.invoke(messages=messages, temperature=0)

    def _parse_result(self, raw_result: str) -> QueryClassification:
        try:
            data = json.loads(raw_result)
            return QueryClassification.model_validate(data)
        except Exception as e:
            raise ValueError(f"Failed to parse classifier output: {raw_result}") from e

    def _apply_rule_overrides(
        self,
        user_query: str,
        result: QueryClassification
    ) -> QueryClassification:
        has_doc_hint = any(k in user_query for k in DOC_HINT_KEYWORDS)
        has_semantic_hint = any(k in user_query for k in SEMANTIC_HINT_KEYWORDS)

        # 문서 힌트가 있으면 doc로 상향
        if has_doc_hint:
            return QueryClassification(
                query_type="hybrid_sql_semantic_doc",
                confidence=max(result.confidence, 0.9),
                reason="문서 또는 회의 기반 근거가 요구되어 문서 검색이 필요"
            )

        # pure_sql인데 confidence가 낮거나 semantic 힌트가 있으면 hybrid로 상향
        if (
            result.query_type == "pure_sql"
            and (
                has_semantic_hint
                or result.confidence < self.config.confidence_floor_for_pure_sql_upgrade
            )
        ):
            return QueryClassification(
                query_type="hybrid_sql_semantic",
                confidence=max(result.confidence, 0.8),
                reason="의미 기반 이슈 식별 가능성이 있어 semantic 검색 경로로 라우팅"
            )

        return result

  def classify_with_fallback(self, user_query: str) -> QueryClassification:
        try:
            return self.classify(user_query)
        except Exception:
            return self._fallback_classification(user_query)

  def _fallback_classification(self, user_query: str) -> QueryClassification:
      has_doc_hint = any(k in user_query for k in DOC_HINT_KEYWORDS)
      has_semantic_hint = any(k in user_query for k in SEMANTIC_HINT_KEYWORDS)

      if has_doc_hint:
          return QueryClassification(
              query_type="hybrid_sql_semantic_doc",
              confidence=0.6,
              reason="문서 관련 표현이 있어 보수적으로 문서 검색 경로 선택"
          )

      if has_semantic_hint:
          return QueryClassification(
              query_type="hybrid_sql_semantic",
              confidence=0.6,
              reason="의미 기반 표현이 있어 보수적으로 semantic 검색 경로 선택"
          )

      return QueryClassification(
          query_type="hybrid_sql_semantic",
          confidence=0.5,
          reason="파싱 실패로 보수적으로 hybrid semantic 경로 선택"
      )
