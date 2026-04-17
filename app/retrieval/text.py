from __future__ import annotations

import re
import unicodedata


_CJK_REGEX_CLASS = (
    "\u3400-\u4DBF"
    "\u4E00-\u9FFF"
    "\uF900-\uFAFF"
    "\U00020000-\U0002A6DF"
    "\U0002A700-\U0002B73F"
    "\U0002B740-\U0002B81F"
    "\U0002B820-\U0002CEAF"
    "\U0002CEB0-\U0002EBEF"
    "\U00030000-\U0003134F"
)
_TOKEN_PATTERN = re.compile(rf"[A-Za-z0-9]+(?:[._/-][A-Za-z0-9]+)*|[{_CJK_REGEX_CLASS}]+")
_CJK_BLOCKS = (
    (0x3400, 0x4DBF),
    (0x4E00, 0x9FFF),
    (0xF900, 0xFAFF),
    (0x20000, 0x2A6DF),
    (0x2A700, 0x2B73F),
    (0x2B740, 0x2B81F),
    (0x2B820, 0x2CEAF),
    (0x2CEB0, 0x2EBEF),
    (0x30000, 0x3134F),
)
_ASCII_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "be",
    "for",
    "how",
    "in",
    "is",
    "of",
    "on",
    "or",
    "the",
    "to",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
}
_CJK_STOPWORDS = {
    "\u4e00\u4e0b",
    "\u4ec0\u4e48",
    "\u4e3a\u4f55",
    "\u5982\u4f55",
    "\u54ea\u4e9b",
    "\u8fd9\u4e2a",
    "\u90a3\u4e2a",
    "\u4ee5\u53ca",
    "\u8bf7\u95ee",
    "\u600e\u4e48",
}
_SORTED_CJK_STOPWORDS = sorted(_CJK_STOPWORDS, key=len, reverse=True)


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text or "")
    normalized = normalized.replace("\u3000", " ")
    return re.sub(r"\s+", " ", normalized).strip()


def tokenize_text(text: str, *, keep_stopwords: bool = False) -> list[str]:
    normalized = normalize_text(text)
    tokens: list[str] = []
    for part in _TOKEN_PATTERN.findall(normalized):
        if _is_cjk_text(part):
            tokens.extend(_tokenize_cjk(part, keep_stopwords=keep_stopwords))
            continue

        token = part.lower()
        if not keep_stopwords and token in _ASCII_STOPWORDS:
            continue
        tokens.append(token)

    return [token for token in tokens if token]


def extract_entity_terms(text: str) -> list[str]:
    entities: list[str] = []
    seen: set[str] = set()
    for token in tokenize_text(text):
        if token in _ASCII_STOPWORDS or token in _CJK_STOPWORDS:
            continue
        if token.isdigit():
            continue
        if _is_cjk_text(token):
            keep = len(token) >= 2
        else:
            keep = len(token) >= 3 or any(char.isdigit() for char in token)
        if keep and token not in seen:
            seen.add(token)
            entities.append(token)
    return entities


def contains_token(text: str, token: str) -> bool:
    haystack = normalize_text(text).lower()
    return token.lower() in haystack


def _tokenize_cjk(text: str, *, keep_stopwords: bool) -> list[str]:
    content_spans = [text] if keep_stopwords else _split_cjk_content(text)
    tokens: list[str] = []
    for span in content_spans:
        tokens.extend(_tokenize_cjk_span(span))

    if keep_stopwords:
        return _deduplicate_preserving_order(tokens)
    return [token for token in _deduplicate_preserving_order(tokens) if token not in _CJK_STOPWORDS]


def _split_cjk_content(text: str) -> list[str]:
    parts: list[str] = []
    buffer: list[str] = []
    index = 0
    while index < len(text):
        matched_stopword = None
        for stopword in _SORTED_CJK_STOPWORDS:
            if text.startswith(stopword, index):
                matched_stopword = stopword
                break

        if matched_stopword is not None:
            if buffer:
                parts.append("".join(buffer))
                buffer.clear()
            index += len(matched_stopword)
            continue

        buffer.append(text[index])
        index += 1

    if buffer:
        parts.append("".join(buffer))

    return [part for part in parts if part]


def _tokenize_cjk_span(text: str) -> list[str]:
    chars = [char for char in text if _is_cjk_char(char)]
    if not chars:
        return []
    if len(chars) == 1:
        return chars

    tokens = ["".join(chars[index : index + 2]) for index in range(len(chars) - 1)]
    if len(chars) <= 4:
        tokens.append("".join(chars))
    return tokens


def _deduplicate_preserving_order(tokens: list[str]) -> list[str]:
    seen: set[str] = set()
    deduplicated: list[str] = []
    for token in tokens:
        if token in seen:
            continue
        seen.add(token)
        deduplicated.append(token)
    return deduplicated


def _is_cjk_text(text: str) -> bool:
    return bool(text) and all(_is_cjk_char(char) for char in text)


def _is_cjk_char(char: str) -> bool:
    code = ord(char)
    return any(start <= code <= end for start, end in _CJK_BLOCKS)
