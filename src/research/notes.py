from typing import Dict
import json
from google import genai
from google.genai.types import Content, Part

EXTRACT_PROMPT_TMPL = """You are a financial research analyst.
Extract factual notes for the finance topic with strict provenance.

Return compact JSON with keys:
- key_claims: list of concise claims (no hype)
- data_points: list of numbers with units/dates (e.g., "CPI YoY 7.2% (Mar 2023)")
- quotes: <= 20-word quotes (optional)
- source_url: exact URL
Text (truncated to 8k chars):
{TEXT}
URL: {URL}
"""

def extract_notes(client: genai.Client, text: str, url: str, model: str = "gemini-2.5-flash") -> Dict:
    prompt = EXTRACT_PROMPT_TMPL.format(TEXT=text[:8000], URL=url)
    resp = client.models.generate_content(
        model=model,
        contents=[Content(role="user", parts=[Part.from_text(text=prompt)])],
    )
    raw = resp.text or "{}"
    try:
        data = json.loads(raw)
    except Exception:
        data = {"key_claims": [], "data_points": [], "quotes": [], "source_url": url}
    # ensure url present
    data["source_url"] = url
    return data
