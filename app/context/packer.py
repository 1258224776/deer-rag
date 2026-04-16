from __future__ import annotations

from app.core.models import EvidencePack


class ContextPacker:
    def pack(self, evidence: list[EvidencePack], profile: str = "markdown") -> str:
        if profile == "plain":
            return self._pack_plain(evidence)
        if profile == "agent":
            return self._pack_agent(evidence)
        return self._pack_markdown(evidence)

    def _pack_markdown(self, evidence: list[EvidencePack]) -> str:
        blocks: list[str] = []
        for idx, item in enumerate(evidence, start=1):
            title = item.title or "Untitled"
            source = item.source or "unknown"
            citation = item.citation_id or f"E{idx}"
            blocks.append(
                "\n".join(
                    [
                        f"### Evidence {idx} [{citation}]",
                        f"- Title: {title}",
                        f"- Source: {source}",
                        f"- Score: {item.rerank_score if item.rerank_score is not None else item.score:.4f}",
                        "",
                        item.snippet,
                    ]
                )
            )
        return "\n\n".join(blocks).strip()

    def _pack_plain(self, evidence: list[EvidencePack]) -> str:
        blocks: list[str] = []
        for idx, item in enumerate(evidence, start=1):
            blocks.append(f"[{idx}] {item.title} | {item.source}\n{item.snippet}")
        return "\n\n".join(blocks).strip()

    def _pack_agent(self, evidence: list[EvidencePack]) -> str:
        blocks: list[str] = []
        for idx, item in enumerate(evidence, start=1):
            citation = item.citation_id or f"E{idx}"
            blocks.append(
                "\n".join(
                    [
                        f"[{citation}] title={item.title or 'Untitled'}",
                        f"source={item.source or 'unknown'}",
                        f"score={(item.rerank_score if item.rerank_score is not None else item.score):.4f}",
                        "snippet:",
                        item.snippet,
                    ]
                )
            )
        return "\n\n".join(blocks).strip()
