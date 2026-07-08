from __future__ import annotations

from pathlib import Path

from ..errors import ScannedPDFError

# A page with fewer extractable characters than this is treated as image-only.
_TEXTY_PAGE_MIN_CHARS = 25
# If fewer than this fraction of pages carry text, the PDF is likely scanned.
_TEXTY_PAGE_MIN_RATIO = 0.2


def parse_pdf(path: Path) -> str:
    import fitz  # PyMuPDF

    with fitz.open(path) as doc:
        pages = [page.get_text() for page in doc]

    texty = sum(1 for t in pages if len(t.strip()) >= _TEXTY_PAGE_MIN_CHARS)
    if not pages or texty / len(pages) < _TEXTY_PAGE_MIN_RATIO:
        raise ScannedPDFError(
            f"{path.name} has no usable text layer — it looks like a scanned PDF. "
            f"OCR is out of scope for docpod v1; run an OCR tool first "
            f"(e.g. `ocrmypdf {path.name} {path.stem}-ocr.pdf`) and retry."
        )

    # \f between pages preserves document structure for the chunker.
    return "\f".join(pages)
