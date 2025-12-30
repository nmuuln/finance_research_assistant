from typing import Dict
import json
from google import genai
from google.genai.types import Content, Part
from src.utils.retry import retry_gemini_call

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


def _coerce_json(text: str) -> Dict:
    """Attempt to deserialise model output that may include fences or prose."""
    if not text:
        return {}

    candidate = text.strip()
    if candidate.startswith("```"):
        lines = candidate.splitlines()
        # drop leading fence
        lines = [ln for ln in lines if not ln.strip().startswith("```")]
        candidate = "\n".join(lines).strip()

    # Heuristic: keep substring between first '{' and last '}'.
    start = candidate.find("{")
    end = candidate.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = candidate[start : end + 1]

    try:
        return json.loads(candidate)
    except Exception:
        return {}


@retry_gemini_call
def extract_notes(client: genai.Client, text: str, url: str, model: str = "gemini-2.0-flash") -> Dict:
    prompt = EXTRACT_PROMPT_TMPL.format(TEXT=text[:8000], URL=url)
    resp = client.models.generate_content(
        model=model,
        contents=[Content(role="user", parts=[Part.from_text(text=prompt)])],
    )
    data = _coerce_json(resp.text or "")
    if not isinstance(data, dict):
        data = {}
    data.setdefault("key_claims", [])
    data.setdefault("data_points", [])
    data.setdefault("quotes", [])
    # ensure url present
    data["source_url"] = url
    return data
