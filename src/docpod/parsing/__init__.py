"""Document parsing: dispatch by extension to pdf (PyMuPDF), docx (python-docx),
or plain text. A PDF with no extractable text (scanned) raises ScannedPDFError
with a clear message — OCR is out of scope for v1."""
