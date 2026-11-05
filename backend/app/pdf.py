from __future__ import annotations

import io

import pdfplumber


def pdf_to_text(data: bytes) -> str:
    """Read the text of a PDF. Returns '' for a scan with no text layer."""
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        pages = [(p.extract_text() or "") for p in pdf.pages]
    return "\n".join(pages).strip()
