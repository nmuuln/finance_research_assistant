from typing import List
from google import genai
from google.genai.types import Content, Part

def init_gemini_client(api_key: str | None) -> genai.Client:
    return genai.Client(api_key=api_key or "")

def draft_finance_report(
    client: genai.Client,
    domain_guard: str,
    tone: str,
    structure: str,
    research_question: str,
    brief: str,
    references: List[str],
    model: str = "gemini-2.5-pro",
) -> str:
    sources_block = "\n".join(f"[{i+1}] {u}" for i, u in enumerate(references))
    prompt = f"""{domain_guard}

{tone}

{structure}

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
        contents=[Content(role="user", parts=[Part.from_text(prompt)])],  # <-- keyword arg
    )
    return resp.text or ""
