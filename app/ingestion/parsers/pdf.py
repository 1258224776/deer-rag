from __future__ import annotations

import fitz

from app.core.interfaces import BaseParser


class PdfParser(BaseParser):
    def parse(self, source: str | bytes, **kwargs) -> str:
        if isinstance(source, bytes):
            document = fitz.open(stream=source, filetype="pdf")
        else:
            document = fitz.open(source)

        texts: list[str] = []
        try:
            for page in document:
                text = page.get_text("text").strip()
                if text:
                    texts.append(text)
        finally:
            document.close()
        return "\n\n".join(texts)
