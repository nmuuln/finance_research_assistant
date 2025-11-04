from typing import Dict, List
from google import genai
from google.genai.types import Content, Part

from .tavily_search import WebSearch
from .fetch import fetch_and_clean
from .notes import extract_notes

PLANNER_PROMPT = """{DOMAIN_GUARD}

Task: Decompose the finance research topic into sub-questions and web search queries.
Output JSON with:
- sub_questions: [ ... ]
- queries: [ ... ]  // 3-6 focused queries with financial/credit/policy terms
Topic: {TOPIC}
"""

def plan_queries(client: genai.Client, domain_guard: str, topic: str, model: str = "gemini-2.5-pro") -> Dict:
    prompt = PLANNER_PROMPT.format(DOMAIN_GUARD=domain_guard, TOPIC=topic)
    resp = client.models.generate_content(
        model=model,
        contents=[Content(role="user", parts=[Part.from_text(text=prompt)])],
        
    )
    import json
    try:
        return json.loads(resp.text or "{}")
    except Exception:
        return {"sub_questions": [], "queries": [f"{topic} financial markets credit policy analysis"]}

def build_brief_from_notes(client: genai.Client, domain_guard: str, notes: List[Dict], model: str = "gemini-2.5-pro") -> str:
    prompt = (
        f"{domain_guard}\n\n"
        "Synthesize the following structured notes into a concise research brief with numbered references.\n"
        "Rules: Only use facts from notes. Identify disagreements. Output markdown.\n\n"
        f"NOTES (JSON):\n{notes}"
    )
    resp = client.models.generate_content(
        model=model,
        contents=[Content(role="user", parts=[Part.from_text(text=prompt)])],
    )
    return resp.text or ""

def run_research(topic: str, domain_guard: str, gemini: genai.Client, tavily_key: str | None = None) -> Dict:
    # 1) Plan
    plan = plan_queries(gemini, domain_guard, topic)
    queries = plan.get("queries") or [f"{topic} financial markets credit policy analysis"]

    # 2) Search + fetch + extract
    search = WebSearch(api_key=tavily_key)
    notes, refs = [], []

    for q in queries[:6]:
        results = search.search(q, max_results=5)
        for r in results:
            url = r.get("url")
            if not url:
                continue
            text = fetch_and_clean(url)
            if not text or len(text) < 400:
                continue
            note = extract_notes(gemini, text, url, model="gemini-2.5-flash")
            notes.append(note)
            refs.append(url)

    # 3) Brief
    brief = build_brief_from_notes(gemini, domain_guard, notes)
    refs = sorted(set(refs))
    return {"plan": plan, "notes": notes, "brief": brief, "references": refs}
