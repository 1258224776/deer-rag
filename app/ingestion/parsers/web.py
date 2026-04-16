from __future__ import annotations

import trafilatura

from app.core.interfaces import BaseParser


class WebParser(BaseParser):
    def parse(self, source: str | bytes, **kwargs) -> str:
        html = source.decode(kwargs.get("encoding", "utf-8"), errors="ignore") if isinstance(source, bytes) else source
        extracted = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=True,
            favor_recall=True,
            no_fallback=False,
        )
        return (extracted or html).strip()
