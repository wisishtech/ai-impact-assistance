# import fitz  # pymupdf
import pymupdf as fitz


def extract_pages(path: str) -> list[dict]:
    """Return [{'page': 1, 'text': '...'}, ...] for every page that has text."""
    pages = []
    with fitz.open(path) as doc:
        for i, page in enumerate(doc, start=1):
            text = page.get_text("text").strip()
            if text:
                pages.append({"page": i, "text": text})
    return pages