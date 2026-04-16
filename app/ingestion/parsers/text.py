from __future__ import annotations

from bs4 import BeautifulSoup

from app.core.interfaces import BaseParser


class MarkdownParser(BaseParser):
    def parse(self, source: str | bytes, **kwargs) -> str:
        if isinstance(source, bytes):
            return source.decode(kwargs.get("encoding", "utf-8"), errors="ignore").strip()
        return source.strip()


class HtmlParser(BaseParser):
    def parse(self, source: str | bytes, **kwargs) -> str:
        html = source.decode(kwargs.get("encoding", "utf-8"), errors="ignore") if isinstance(source, bytes) else source
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
            tag.decompose()
        lines = [line.strip() for line in soup.get_text(separator="\n").splitlines() if line.strip()]
        return "\n".join(lines)
