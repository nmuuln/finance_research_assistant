from typing import Optional
import re
from io import BytesIO

import requests
from bs4 import BeautifulSoup
from readability import Document
from pypdf import PdfReader

# Remove NUL and control chars (except common whitespace)
_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

def _sanitize(s: str) -> str:
    if not s:
        return s
    return _CTRL.sub("", s)


def _extract_pdf_text(binary: bytes) -> Optional[str]:
    """Return concatenated text from a PDF payload."""
    if not binary:
        return None
    try:
        reader = PdfReader(BytesIO(binary))
    except Exception:
        return None

    parts: list[str] = []
    for page in reader.pages:
        try:
            page_text = page.extract_text() or ""
        except Exception:
            page_text = ""
        if page_text:
            parts.append(page_text.strip())

    text = "\n".join(parts)
    return text if text else None

def fetch_and_clean(url: str, timeout: int = 20) -> Optional[str]:
    try:
        resp = requests.get(
            url,
            timeout=timeout,
            headers={"User-Agent": "UFE-ResearchWriter/1.0 (+https://example.com)"},
        )
        resp.raise_for_status()
    except Exception:
        return None

    content_type = resp.headers.get("Content-Type", "").lower()

    # Handle PDFs explicitly before running HTML cleaners.
    if "pdf" in content_type or url.lower().endswith(".pdf"):
        pdf_text = _extract_pdf_text(resp.content)
        if pdf_text:
            return pdf_text
        # fall through to HTML parsing if PDF extraction failed unexpectedly

    html = _sanitize(resp.text)

    # Try Readability first
    try:
        doc = Document(html)
        summary_html = doc.summary()
        soup = BeautifulSoup(summary_html, "html.parser")
        text = soup.get_text(" ", strip=True)
        if text and len(text) >= 200:
            return text
    except Exception:
        # fall through to plain parse
        pass

    # Fallback: plain parsing of sanitized HTML
    try:
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(" ", strip=True)
        return text or None
    except Exception:
        return None
