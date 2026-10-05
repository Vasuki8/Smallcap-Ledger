"""Bounded PDF text extraction using pypdf's supported page APIs."""
from __future__ import annotations

MAX_PDF_PAGE_CONTENT_BYTES=20*1024*1024


def safe_pdf_text(page, *, max_content_bytes: int = MAX_PDF_PAGE_CONTENT_BYTES, **kwargs):
    """Reject an oversized decompressed page content stream before text extraction."""
    get_contents=getattr(page,"get_contents",None)
    if callable(get_contents):
        contents=get_contents()
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
