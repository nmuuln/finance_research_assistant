from typing import Dict, List, Optional, Any
from google import genai
from google.genai.types import Content, Part

from .tavily_search import WebSearch
from .fetch import fetch_and_clean
from .notes import extract_notes
from .literature_review import LiteratureReview
from src.utils.retry import retry_gemini_call

PLANNER_PROMPT = """{DOMAIN_GUARD}

Task: Decompose the finance research topic into sub-questions and web search queries.
Output JSON with:
- sub_questions: [ ... ]
- queries: [ ... ]  // 3-6 focused queries with financial/credit/policy terms
Topic: {TOPIC}
"""

# --- Token budgeting constants ---
AVG_CHARS_PER_TOKEN = 4.0
SOFT_CAP_TOKENS = 11000
HARD_CAP_TOKENS = 12000
NOTE_SUMMARIZE_THRESHOLD = 2500
MAX_BRIEF_CHARS = int(SOFT_CAP_TOKENS * AVG_CHARS_PER_TOKEN)


def _estimate_tokens(text: str) -> int:
    return int(len(text) / AVG_CHARS_PER_TOKEN)


def _truncate_notes(notes: List[Dict]) -> List[Dict]:
    import json

    serialized = json.dumps(notes)
    if _estimate_tokens(serialized) <= SOFT_CAP_TOKENS:
        return notes

    trimmed: List[Dict] = []
    for note in notes:
        note_copy = dict(note)
        serialized_note = json.dumps(note_copy, ensure_ascii=False)
        if len(serialized_note) > NOTE_SUMMARIZE_THRESHOLD:
            note_copy["_trimmed"] = True
            note_copy["_excerpt"] = serialized_note[:NOTE_SUMMARIZE_THRESHOLD] + "…[truncated]"
        trimmed.append(note_copy)
        serialized = json.dumps(trimmed, ensure_ascii=False)
        if _estimate_tokens(serialized) > HARD_CAP_TOKENS:
            break
    return trimmed


@retry_gemini_call
def plan_queries(client: genai.Client, domain_guard: str, topic: str, model: str = "gemini-2.0-flash") -> Dict:
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

@retry_gemini_call
def build_brief_from_notes(client: genai.Client, domain_guard: str, notes: List[Dict], model: str = "gemini-2.0-flash") -> str:
    import json

    safe_notes = _truncate_notes(notes)
    notes_json = json.dumps(safe_notes, ensure_ascii=False)
    if len(notes_json) > MAX_BRIEF_CHARS:
        notes_json = notes_json[:MAX_BRIEF_CHARS] + "…[truncated]"
        print("[WARN] Notes clipped to stay under model token limit.")

    prompt = (
        f"{domain_guard}\n\n"
        "Synthesize the following structured notes into a concise research brief with numbered references.\n"
        "Rules: Only use facts from notes. Identify disagreements. Output markdown.\n\n"
        f"NOTES (JSON):\n{notes_json}"
    )

    est_tokens = _estimate_tokens(prompt)
    if est_tokens > SOFT_CAP_TOKENS:
        print(f"[WARN] build_brief_from_notes prompt est {est_tokens} tokens.")

    resp = client.models.generate_content(
        model=model,
        contents=[Content(role="user", parts=[Part.from_text(text=prompt)])],
    )
    return resp.text or ""

def run_research(topic: str, domain_guard: str, gemini: genai.Client, tavily_key: str | None = None, additional_context: str = "") -> Dict:
    import time

    # 1) Plan
    plan = plan_queries(gemini, domain_guard, topic)
    queries = plan.get("queries") or [f"{topic} financial markets credit policy analysis"]

    # 2) Search + fetch + extract
    search = WebSearch(api_key=tavily_key)
    notes, refs = [], []

    # If additional context provided (from uploaded files), add it as first note
    if additional_context:
        context_note = {
            "source": "uploaded_files",
            "url": "local://uploaded-files",
            "claims": ["User-provided reference materials"],
            "data": [additional_context[:2000]],  # Truncate to avoid overflow
            "quotes": []
        }
        notes.append(context_note)
        refs.append("Uploaded Files")

    for q in queries[:6]:
        results = search.search(q, max_results=5)
        for r in results:
            url = r.get("url")
            if not url:
                continue
            text = fetch_and_clean(url)
            if not text or len(text) < 400:
                continue
            note = extract_notes(gemini, text, url, model="gemini-2.0-flash")
            notes.append(note)
            refs.append(url)
            # Add small delay between API calls to avoid rate limiting
            time.sleep(0.5)

    # 3) Brief
    brief = build_brief_from_notes(gemini, domain_guard, notes)
    refs = sorted(set(refs))
    return {"plan": plan, "notes": notes, "brief": brief, "references": refs}


def run_research_with_literature(
    topic: str,
    domain_guard: str,
    gemini: genai.Client,
    literature_review: Optional[LiteratureReview] = None,
    tavily_key: Optional[str] = None,
    additional_context: str = "",
) -> Dict[str, Any]:
    """
    Run research with optional approved literature review context.

    If literature_review is provided and approved, it will be included
    in the notes and its references added to the reference list.

    Args:
        topic: Research topic
        domain_guard: Domain restriction prompt
        gemini: Gemini client
        literature_review: Optional approved LiteratureReview
        tavily_key: Tavily API key
        additional_context: Additional context from uploaded files

    Returns:
        Dict with plan, notes, brief, references, and literature_included flag
    """
    import time

    # 1) Plan
    plan = plan_queries(gemini, domain_guard, topic)
    queries = plan.get("queries") or [f"{topic} financial markets credit policy analysis"]

    # 2) Search + fetch + extract
    search = WebSearch(api_key=tavily_key)
    notes: List[Dict] = []
    refs: List[str] = []

    # Add approved literature review as context first
    literature_included = False
    if literature_review and literature_review.approved:
        literature_included = True
        lit_note = {
            "source": "literature_review",
            "url": "academic://literature-review",
            "claims": literature_review.themes + literature_review.gaps,
            "data": [literature_review.summary[:3000]],  # Truncate to avoid overflow
            "quotes": [],
            "paper_count": len(literature_review.papers),
        }
        notes.append(lit_note)

        # Add paper URLs/DOIs as references
        for paper in literature_review.papers:
            if paper.get("doi"):
                refs.append(f"https://doi.org/{paper['doi']}")
            elif paper.get("url"):
                refs.append(paper["url"])

    # If additional context provided (from uploaded files), add it as note
    if additional_context:
        context_note = {
            "source": "uploaded_files",
            "url": "local://uploaded-files",
            "claims": ["User-provided reference materials"],
            "data": [additional_context[:2000]],
            "quotes": []
        }
        notes.append(context_note)
        refs.append("Uploaded Files")

    # Web search loop
    for q in queries[:6]:
        results = search.search(q, max_results=5)
        for r in results:
            url = r.get("url")
            if not url:
                continue
            text = fetch_and_clean(url)
            if not text or len(text) < 400:
                continue
            note = extract_notes(gemini, text, url, model="gemini-2.0-flash")
            notes.append(note)
            refs.append(url)
            time.sleep(0.5)

    # 3) Brief
    brief = build_brief_from_notes(gemini, domain_guard, notes)
    refs = sorted(set(refs))

    return {
        "plan": plan,
        "notes": notes,
        "brief": brief,
        "references": refs,
        "literature_included": literature_included,
    }
