from typing import List
from google import genai
from google.genai.types import Content, Part
from src.utils.retry import retry_gemini_call


def init_gemini_client(api_key: str | None) -> genai.Client:
    return genai.Client(api_key=api_key or "")


def _language_directive(language: str) -> str:
    lang = (language or "").strip().lower()
    if lang.startswith("en"):
        return (
            "Primary output language: English. Maintain formal academic tone. "
            "If references contain Mongolian names/terms, keep original spelling."
        )
    if lang.startswith("mn"):
        return (
            "Primary output language: Mongolian (Монгол хэлээр). "
            "Use formal academic tone suitable for finance research. "
            "Translate technical terms where appropriate and provide transliteration "
            "in parentheses if the English term is essential."
        )
    if not lang:
        return (
            "Default to Mongolian (Монгол хэлээр). Switch languages only if explicitly requested."
        )
    return (
        f"Primary output language: {language}. Maintain formal academic tone and stay consistent."
    )


@retry_gemini_call
def draft_finance_report(
    client: genai.Client,
    domain_guard: str,
    tone: str,
    structure: str,
    research_question: str,
    brief: str,
    references: List[str],
    model: str = "gemini-2.0-flash",
    language: str = "mn",
) -> str:
    sources_block = "\n".join(f"[{i+1}] {u}" for i, u in enumerate(references))
    prompt = f"""{domain_guard}

{tone}

{structure}

Language directive:
{_language_directive(language)}

Research Question:
{research_question}

Deep Research Brief (verbatim):
{brief}

References (use numbered inline citations [1], [2], ... mapped to this list; do NOT invent new sources):
{sources_block}

Write the final report now.
"""
    resp = client.models.generate_content(
        model=model,
        contents=[Content(role="user", parts=[Part.from_text(text=prompt)])],
    )
    return resp.text or ""
