"""Document parsing: dispatch by extension to pdf (PyMuPDF), docx (python-docx),
or plain text. A PDF with no extractable text (scanned) raises ScannedPDFError
with a clear message — OCR is out of scope for v1."""

from __future__ import annotations

from pathlib import Path

from ..errors import EmptyDocumentError, UnsupportedFormatError


def parse_document(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        from .pdf import parse_pdf

        text = parse_pdf(path)
    elif suffix == ".docx":
        from .docx import parse_docx

        text = parse_docx(path)
    elif suffix in (".txt", ".md"):
        from .text import parse_text

        text = parse_text(path)
    else:
        raise UnsupportedFormatError(
            f"can't parse '{suffix or path.name}' — supported inputs are .pdf, .docx, .txt, .md"
        )

    if not text.strip():
        raise EmptyDocumentError(f"{path.name} parsed to an empty document")
    return text
