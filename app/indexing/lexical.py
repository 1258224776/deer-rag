from __future__ import annotations

import json
from pathlib import Path

from rank_bm25 import BM25Okapi

from app.core.models import Chunk


class BM25LexicalIndex:
    def __init__(self, state_path: str | Path) -> None:
        self.state_path = Path(state_path)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

    def build(self, chunks: list[Chunk]) -> int:
        chunk_ids = [chunk.id for chunk in chunks]
        tokenized_corpus = [self._tokenize(chunk.text) for chunk in chunks]

        payload = {
            "chunk_ids": chunk_ids,
            "tokenized_corpus": tokenized_corpus,
        }
        self.state_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return len(chunk_ids)

    def load(self) -> tuple[BM25Okapi | None, list[str]]:
        if not self.state_path.exists():
            return None, []

        payload = json.loads(self.state_path.read_text(encoding="utf-8"))
        tokenized_corpus = payload.get("tokenized_corpus", [])
        chunk_ids = payload.get("chunk_ids", [])
        if not tokenized_corpus:
            return None, chunk_ids
        return BM25Okapi(tokenized_corpus), chunk_ids

    def _tokenize(self, text: str) -> list[str]:
        # MVP limitation: whitespace tokenization works poorly for Chinese text.
        # A language-aware tokenizer should replace this in a later iteration.
        return text.split()
