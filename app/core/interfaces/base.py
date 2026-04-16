from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.core.models import Chunk, EvidencePack, SourceDocument


class BaseParser(ABC):
    @abstractmethod
    def parse(self, source: str | bytes, **kwargs: Any) -> str:
        """Return normalized text from a source payload."""


class BaseChunker(ABC):
    @abstractmethod
    def chunk(self, document: SourceDocument, text: str, **kwargs: Any) -> list[Chunk]:
        """Split a document into chunks."""


class BaseRetriever(ABC):
    @abstractmethod
    def retrieve(self, query: str, collection_id: str, top_k: int = 10, **kwargs: Any) -> list[EvidencePack]:
        """Return ranked evidence candidates for a query."""


class BaseReranker(ABC):
    @abstractmethod
    def rerank(self, query: str, candidates: list[EvidencePack], top_k: int | None = None, **kwargs: Any) -> list[EvidencePack]:
        """Rerank retrieved evidence candidates."""
