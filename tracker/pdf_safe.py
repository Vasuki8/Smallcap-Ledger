"""Bounded PDF text extraction using pypdf's supported APIs."""
from __future__ import annotations

import io

from pypdf import PdfReader

MAX_PDF_PAGES=400
MAX_PDF_PAGE_CONTENT_BYTES=20*1024*1024


def pdf_reader(content: bytes, *, max_pages: int = MAX_PDF_PAGES):
    """Create a reader only for unencrypted PDFs within the page-count limit."""
    if not content.startswith(b"%PDF"):
        raise ValueError("Document is not a PDF")
    try:
        reader=PdfReader(io.BytesIO(content))
    except Exception as exc:
        raise ValueError("PDF could not be parsed") from exc
    if reader.is_encrypted:
        raise ValueError("Encrypted PDFs are unsupported")
    if len(reader.pages)>max_pages:
        raise ValueError("PDF contains too many pages")
    return reader


def safe_pdf_text(page, *, max_content_bytes: int = MAX_PDF_PAGE_CONTENT_BYTES, **kwargs):
    """Reject an oversized decompressed page content stream before text extraction."""
    contents=page.get_contents()
    if contents is not None:
        try:
            data=contents.get_data()
        except Exception as exc:
            raise ValueError("PDF page content stream could not be decoded") from exc
        if len(data)>max_content_bytes:
            raise ValueError("PDF page content stream exceeds the parser limit")
    try:
        return page.extract_text(**kwargs) or ""
    except Exception as exc:
        if isinstance(exc,ValueError):
            raise
        raise ValueError("PDF text extraction failed") from exc
