from __future__ import annotations

import re
from typing import Iterable

import tiktoken

from app.core.interfaces import BaseChunker
from app.core.models import Chunk, SourceDocument


def _get_encoder(model_name: str = "cl100k_base"):
    try:
        return tiktoken.get_encoding(model_name)
    except Exception:
        return None


class FixedChunker(BaseChunker):
    def __init__(self, chunk_size: int = 800, overlap: int = 120, encoder_name: str = "cl100k_base") -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.encoder = _get_encoder(encoder_name)

    def _estimate_tokens(self, text: str) -> int:
        if self.encoder is not None:
            return len(self.encoder.encode(text))
        return max(1, len(text.split()))

    def _split_paragraphs(self, text: str) -> Iterable[str]:
        paragraphs = [part.strip() for part in re.split(r"\n{2,}", text) if part.strip()]
        return paragraphs or [text.strip()]

    def _tail_overlap_text(self, text: str, overlap: int) -> str:
        if overlap <= 0 or not text.strip():
            return ""

        if self.encoder is not None:
            tokens = self.encoder.encode(text)
            return self.encoder.decode(tokens[-overlap:]).strip()

        words = text.split()
        return " ".join(words[-overlap:]).strip()

    def _slice_to_budget(self, text: str, chunk_size: int, overlap: int) -> tuple[str, str]:
        if self.encoder is not None:
            tokens = self.encoder.encode(text)
            head_tokens = tokens[:chunk_size]
            remainder_start = max(chunk_size - overlap, 0)
            remainder_tokens = tokens[remainder_start:]
            return (
                self.encoder.decode(head_tokens).strip(),
                self.encoder.decode(remainder_tokens).strip(),
            )

        words = text.split()
        head_words = words[:chunk_size]
        remainder_words = words[max(chunk_size - overlap, 0):]
        return " ".join(head_words).strip(), " ".join(remainder_words).strip()

    def chunk(self, document: SourceDocument, text: str, **kwargs) -> list[Chunk]:
        chunk_size = int(kwargs.get("chunk_size", self.chunk_size))
        overlap = int(kwargs.get("overlap", self.overlap))

        chunks: list[Chunk] = []
        buffer = ""

        for paragraph in self._split_paragraphs(text):
            candidate = paragraph if not buffer else f"{buffer}\n\n{paragraph}"
            if self._estimate_tokens(candidate) <= chunk_size:
                buffer = candidate
                continue

            if buffer.strip():
                chunks.append(
                    Chunk(
                        document_id=document.id,
                        chunk_index=len(chunks),
                        text=buffer.strip(),
                        token_count=self._estimate_tokens(buffer.strip()),
                    )
                )

            if overlap > 0 and buffer:
                carry = self._tail_overlap_text(buffer, overlap)
                buffer = f"{carry}\n\n{paragraph}".strip()
            else:
                buffer = paragraph

            while self._estimate_tokens(buffer) > chunk_size:
                chunk_text, remainder = self._slice_to_budget(buffer, chunk_size, overlap)
                if not chunk_text:
                    break
                chunks.append(
                    Chunk(
                        document_id=document.id,
                        chunk_index=len(chunks),
                        text=chunk_text,
                        token_count=self._estimate_tokens(chunk_text),
                    )
                )
                if remainder == buffer:
                    break
                buffer = remainder
                if not buffer:
                    break

        if buffer.strip():
            chunks.append(
                Chunk(
                    document_id=document.id,
                    chunk_index=len(chunks),
                    text=buffer.strip(),
                    token_count=self._estimate_tokens(buffer.strip()),
                )
            )

        return [chunk for chunk in chunks if chunk.text]
