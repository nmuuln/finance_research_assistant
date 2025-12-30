"""Literature review orchestration with academic database search and Gemini synthesis."""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import json
import logging

from google import genai
from google.genai.types import Content, Part

from .scholar_search import AcademicSearch, AcademicPaper
from src.utils.retry import retry_gemini_call

logger = logging.getLogger(__name__)


@dataclass
class LiteratureReview:
    """Complete literature review output."""
    papers: List[Dict[str, Any]]  # List of paper dicts
    summary: str                   # Synthesized markdown summary
    themes: List[str]              # Key themes identified
    gaps: List[str]                # Research gaps identified
    approved: bool = False         # User approval status
    search_query: str = ""         # English query used for search

    def to_dict(self) -> Dict[str, Any]:
        return {
            "papers": self.papers,
            "summary": self.summary,
            "themes": self.themes,
            "gaps": self.gaps,
            "approved": self.approved,
            "search_query": self.search_query,
        }


TOPIC_TRANSLATION_PROMPT = """Translate the following research topic to English for academic database search.

Topic: {TOPIC}

Requirements:
- Output ONLY the English translation, nothing else
- Use standard academic/finance terminology
- Keep it concise (suitable for database search query)
- If already in English, return as-is with minor improvements for search

English search query:"""


LITERATURE_SYNTHESIS_PROMPT = """{DOMAIN_GUARD}

You are an academic literature review specialist for finance research.

Given the following academic papers on the topic "{TOPIC}", synthesize a comprehensive literature review.

IMPORTANT: Write ALL output in {LANGUAGE_NAME} ({LANGUAGE_CODE}).

PAPERS (JSON):
{PAPERS_JSON}

Your output must be valid JSON with these keys:
1. "summary": A markdown-formatted literature review (500-800 words) in {LANGUAGE_NAME} that:
   - Organizes papers by theme/methodology
   - Highlights consensus findings
   - Notes contradictions or debates
   - Uses inline citations like (Author et al., Year)

2. "themes": A list of 3-5 key themes across the papers (in {LANGUAGE_NAME})

3. "gaps": A list of 2-4 identified research gaps or under-explored areas (in {LANGUAGE_NAME})

Format your response as JSON only, no markdown fences.
"""

# Language mappings for display
LANGUAGE_LABELS = {
    "mn": {
        "name": "Mongolian",
        "literature_review": "Уран зохиолын тойм",
        "search_query": "Хайлтын түлхүүр үг",
        "papers_found": "Олдсон эрдэм шинжилгээний өгүүлэл",
        "papers": "өгүүлэл",
        "authors": "Зохиогчид",
        "year": "Он",
        "citations": "Эшлэл",
        "source": "Эх сурвалж",
        "venue": "Хэвлэл",
        "abstract": "Хураангуй",
        "synthesis": "Нэгтгэл",
        "key_themes": "Гол сэдвүүд",
        "research_gaps": "Судалгааны цоорхой",
    },
    "en": {
        "name": "English",
        "literature_review": "Literature Review",
        "search_query": "Search query",
        "papers_found": "Academic Papers Found",
        "papers": "papers",
        "authors": "Authors",
        "year": "Year",
        "citations": "Citations",
        "source": "Source",
        "venue": "Venue",
        "abstract": "Abstract",
        "synthesis": "Synthesis",
        "key_themes": "Key Themes",
        "research_gaps": "Research Gaps",
    },
}


def _coerce_json(text: str) -> Dict:
    """Attempt to deserialize model output that may include fences or prose."""
    if not text:
        return {}

    candidate = text.strip()
    if candidate.startswith("```"):
        lines = candidate.splitlines()
        lines = [ln for ln in lines if not ln.strip().startswith("```")]
        candidate = "\n".join(lines).strip()

    # Keep substring between first '{' and last '}'
    start = candidate.find("{")
    end = candidate.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = candidate[start : end + 1]

    try:
        return json.loads(candidate)
    except Exception:
        return {}


@retry_gemini_call
def translate_topic_for_search(
    client: genai.Client,
    topic: str,
    model: str = "gemini-2.0-flash",
) -> str:
    """
    Translate topic to English for academic database search.

    Args:
        client: Gemini client
        topic: Original topic (may be in Mongolian or other language)
        model: Gemini model to use

    Returns:
        English search query
    """
    prompt = TOPIC_TRANSLATION_PROMPT.format(TOPIC=topic)

    resp = client.models.generate_content(
        model=model,
        contents=[Content(role="user", parts=[Part.from_text(text=prompt)])],
    )

    translated = (resp.text or topic).strip()
    # Clean up any quotes or extra formatting
    translated = translated.strip('"\'')

    logger.info(f"Translated topic for search: '{topic}' -> '{translated}'")
    return translated


@retry_gemini_call
def synthesize_literature(
    client: genai.Client,
    domain_guard: str,
    topic: str,
    papers: List[AcademicPaper],
    model: str = "gemini-2.0-flash",
    language: str = "mn",
) -> Dict[str, Any]:
    """
    Use Gemini to synthesize papers into a literature review.

    Returns:
        Dict with keys: summary, themes, gaps
    """
    # Get language name
    lang_info = LANGUAGE_LABELS.get(language, LANGUAGE_LABELS["en"])
    language_name = lang_info["name"]

    # Convert papers to JSON
    papers_data = [p.to_dict() for p in papers]
    papers_json = json.dumps(papers_data, indent=2, ensure_ascii=False)

    # Truncate if too long
    if len(papers_json) > 15000:
        papers_json = papers_json[:15000] + "\n... [truncated]"

    prompt = LITERATURE_SYNTHESIS_PROMPT.format(
        DOMAIN_GUARD=domain_guard,
        TOPIC=topic,
        PAPERS_JSON=papers_json,
        LANGUAGE_NAME=language_name,
        LANGUAGE_CODE=language,
    )

    logger.info(f"Synthesizing literature review for {len(papers)} papers")

    resp = client.models.generate_content(
        model=model,
        contents=[Content(role="user", parts=[Part.from_text(text=prompt)])],
    )

    # Parse JSON response
    data = _coerce_json(resp.text or "{}")

    # Ensure required keys exist
    if not data.get("summary"):
        data["summary"] = resp.text or "Unable to synthesize literature review."
    if not data.get("themes"):
        data["themes"] = []
    if not data.get("gaps"):
        data["gaps"] = []

    return data


def run_literature_review(
    topic: str,
    domain_guard: str,
    gemini: genai.Client,
    semantic_scholar_key: Optional[str] = None,
    openalex_email: Optional[str] = None,
    max_papers_per_source: int = 5,
    model: str = "gemini-2.0-flash",
    language: str = "mn",
) -> LiteratureReview:
    """
    Execute the complete literature review phase.

    Args:
        topic: Research topic
        domain_guard: Domain restriction prompt
        gemini: Gemini client
        semantic_scholar_key: Optional API key for higher rate limits
        openalex_email: Optional email for polite pool
        max_papers_per_source: Papers per academic source (default 5)
        model: Gemini model to use
        language: Output language code (default "mn" for Mongolian)

    Returns:
        LiteratureReview object (not yet approved)
    """
    # 1. Translate topic to English for academic search
    search_query = translate_topic_for_search(
        client=gemini,
        topic=topic,
        model=model,
    )

    # 2. Search academic databases with English query
    search = AcademicSearch(
        semantic_scholar_key=semantic_scholar_key,
        openalex_email=openalex_email,
    )

    papers = search.search(
        query=search_query,
        max_per_source=max_papers_per_source,
    )

    if not papers:
        logger.warning(f"No academic papers found for search query: {search_query}")
        return LiteratureReview(
            papers=[],
            summary=f"No academic papers were found for this topic (searched: '{search_query}'). The research will proceed with web sources only.",
            themes=[],
            gaps=["Unable to identify gaps - no academic papers found"],
            approved=False,
            search_query=search_query,
        )

    # 3. Synthesize with Gemini
    synthesis = synthesize_literature(
        client=gemini,
        domain_guard=domain_guard,
        topic=topic,
        papers=papers,
        model=model,
        language=language,
    )

    return LiteratureReview(
        papers=[p.to_dict() for p in papers],
        summary=synthesis.get("summary", ""),
        themes=synthesis.get("themes", []),
        gaps=synthesis.get("gaps", []),
        approved=False,
        search_query=search_query,
    )


def format_literature_review_for_display(review: LiteratureReview, language: str = "mn") -> str:
    """
    Format literature review for user presentation.

    Args:
        review: LiteratureReview object
        language: Output language code (default "mn" for Mongolian)

    Returns:
        Markdown string for display
    """
    # Get language labels
    labels = LANGUAGE_LABELS.get(language, LANGUAGE_LABELS["en"])

    lines = [f"## {labels['literature_review']}\n"]

    # Show search query if different from original (translated)
    if review.search_query:
        lines.append(f"**{labels['search_query']}:** {review.search_query}\n")

    # Papers with full details
    lines.append(f"### {labels['papers_found']} ({len(review.papers)} {labels['papers']})\n")

    for i, paper in enumerate(review.papers, 1):
        title = paper.get("title", "Untitled")
        year = paper.get("year", "N/A")
        citations = paper.get("citation_count", 0)
        source = paper.get("source", "")
        url = paper.get("url", "")
        doi = paper.get("doi", "")
        venue = paper.get("venue", "")
        abstract = paper.get("abstract", "")

        # Format authors
        authors = paper.get("authors", [])
        if len(authors) > 3:
            authors_str = ", ".join(authors[:3]) + " et al."
        else:
            authors_str = ", ".join(authors) if authors else "Unknown"

        lines.append(f"#### {i}. {title}\n")
        lines.append(f"- **{labels['authors']}:** {authors_str}")
        lines.append(f"- **{labels['year']}:** {year} | **{labels['citations']}:** {citations} | **{labels['source']}:** {source}")
        if venue:
            lines.append(f"- **{labels['venue']}:** {venue}")
        if doi:
            lines.append(f"- **DOI:** [{doi}](https://doi.org/{doi})")
        elif url:
            lines.append(f"- **URL:** {url}")

        if abstract:
            # Truncate abstract if too long
            if len(abstract) > 400:
                abstract = abstract[:400] + "..."
            lines.append(f"- **{labels['abstract']}:** {abstract}")
        lines.append("")

    # Synthesis
    lines.append("---\n")
    lines.append(f"### {labels['synthesis']}\n")
    lines.append(review.summary)
    lines.append("")

    # Themes
    if review.themes:
        lines.append(f"### {labels['key_themes']}\n")
        for theme in review.themes:
            lines.append(f"- {theme}")
        lines.append("")

    # Gaps
    if review.gaps:
        lines.append(f"### {labels['research_gaps']}\n")
        for gap in review.gaps:
            lines.append(f"- {gap}")
        lines.append("")

    return "\n".join(lines)
