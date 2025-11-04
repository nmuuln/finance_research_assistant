from typing import Optional
import re
import requests
from bs4 import BeautifulSoup
from readability import Document

# Remove NUL and control chars (except common whitespace)
_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

def _sanitize(s: str) -> str:
    if not s:
        return s
    return _CTRL.sub("", s)

def fetch_and_clean(url: str, timeout: int = 20) -> Optional[str]:
    try:
        resp = requests.get(
            url,
            timeout=timeout,
            headers={"User-Agent": "UFE-ResearchWriter/1.0 (+https://example.com)"},
        )
        resp.raise_for_status()
        html = _sanitize(resp.text)
    except Exception:
        return None

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
