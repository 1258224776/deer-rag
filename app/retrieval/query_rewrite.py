from __future__ import annotations

from app.retrieval.text import extract_entity_terms, normalize_text, tokenize_text


class RuleBasedQueryRewriter:
    def rewrite(self, query: str) -> list[str]:
        normalized = normalize_text(query)
        if not normalized:
            return []

        rewrites: list[str] = [normalized]
        stripped = self._strip_question_terms(normalized)
        if stripped and stripped not in rewrites:
            rewrites.append(stripped)

        keywords = self._keyword_query(normalized)
        if keywords and keywords not in rewrites:
            rewrites.append(keywords)

        entity_query = " ".join(extract_entity_terms(normalized))
        if entity_query and entity_query not in rewrites:
            rewrites.append(entity_query)

        return rewrites

    def _strip_question_terms(self, query: str) -> str:
        prefixes = (
            "请问",
            "帮我找",
            "帮我查",
            "什么是",
            "怎么",
            "如何",
            "what is",
            "how do",
            "how does",
            "tell me",
            "explain",
        )
        lowered = query.lower()
        for prefix in prefixes:
            if lowered.startswith(prefix):
                candidate = query[len(prefix) :].strip(" ??.，,：:")
                return candidate
        return query

    def _keyword_query(self, query: str) -> str:
        tokens = []
        seen: set[str] = set()
        for token in tokenize_text(query):
            if token in {"what", "how", "why", "when", "where", "who", "请问", "如何", "怎么", "什么"}:
                continue
            if token not in seen:
                seen.add(token)
                tokens.append(token)
        return " ".join(tokens[:8]).strip()
