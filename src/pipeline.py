import os
from typing import Dict, Any, Union, Optional
from pathlib import Path

from src.tools.output_formatter import OutputFormatterTool
from src.llm.writer_agent import init_gemini_client, draft_finance_report

# Research orchestrators
from src.research.orchestrator import run_research, run_research_with_literature
from src.research.literature_review import (
    run_literature_review,
    LiteratureReview,
    format_literature_review_for_display,
)

def _load(path: Union[str, Path]) -> str:
    return Path(path).read_text(encoding="utf-8")

def run_pipeline(topic: str, include_web: bool = True, language: str = "mn", additional_context: str = "") -> Dict[str, Any]:
    base = Path(__file__).parent
    domain_guard = _load(base / "prompts" / "domain_guard.txt")
    writer_tone = _load(base / "prompts" / "writer_tone.txt")
    writer_structure = _load(base / "prompts" / "writer_structure.txt")

    # 1) Init Gemini client (AI Studio key)
    from src.config import cfg
    c = cfg()
    gemini = init_gemini_client(c["GOOGLE_API_KEY"])

    # 2) Research (planner -> search -> fetch -> notes -> brief)
    research = run_research(
        topic,
        domain_guard,
        gemini,
        tavily_key=os.getenv("TAVILY_API_KEY"),
        additional_context=additional_context
    )
    brief = research["brief"]
    references = research["references"]

    # 3) Writer pass (tone + structure)
    draft = draft_finance_report(
        client=gemini,
        domain_guard=domain_guard,
        tone=writer_tone,
        structure=writer_structure,
        research_question=topic,
        brief=brief,
        references=references,
        model="gemini-2.0-flash",
        language=language,
    )

    # 4) Export .docx
    formatter = OutputFormatterTool()
    doc = formatter(draft, out_dir="outputs", filename_prefix="ufe_finance_report")

    return {
        "success": True,
        "brief": brief,
        "references": references,
        "preview": brief[:1000],
        "plan_preview": str(research.get("plan"))[:1000],
        "brief_preview": brief[:1000],
        "num_references": str(len(references)),
        "docx_path": doc["path"],
    }


def run_literature_review_phase(
    topic: str,
    language: str = "mn",
    max_papers_per_source: int = 5,
) -> Dict[str, Any]:
    """
    Phase 1: Run literature review only.

    Searches academic databases (Semantic Scholar, OpenAlex) and synthesizes
    findings into a literature review. Returns review for user approval.

    Args:
        topic: Research topic
        language: Output language (for future use)
        max_papers_per_source: Number of papers per academic source

    Returns:
        Dict with success, phase, review data, and requires_approval flag
    """
    base = Path(__file__).parent
    domain_guard = _load(base / "prompts" / "domain_guard.txt")

    from src.config import cfg
    c = cfg()
    gemini = init_gemini_client(c["GOOGLE_API_KEY"])

    review = run_literature_review(
        topic=topic,
        domain_guard=domain_guard,
        gemini=gemini,
        semantic_scholar_key=c.get("SEMANTIC_SCHOLAR_API_KEY"),
        openalex_email=c.get("OPENALEX_EMAIL"),
        max_papers_per_source=max_papers_per_source,
    )

    return {
        "success": True,
        "phase": "literature_review",
        "review": review.to_dict(),
        "formatted": format_literature_review_for_display(review),
        "paper_count": len(review.papers),
        "requires_approval": True,
    }


def run_pipeline_with_literature(
    topic: str,
    literature_review_data: Dict[str, Any],
    include_web: bool = True,
    language: str = "mn",
    additional_context: str = "",
) -> Dict[str, Any]:
    """
    Phase 2: Run main research pipeline with approved literature review.

    Args:
        topic: Research topic
        literature_review_data: Approved review dict from phase 1
        include_web: Whether to include web search
        language: Output language
        additional_context: Additional context from uploaded files

    Returns:
        Dict with full pipeline results including literature context
    """
    base = Path(__file__).parent
    domain_guard = _load(base / "prompts" / "domain_guard.txt")
    writer_tone = _load(base / "prompts" / "writer_tone.txt")
    writer_structure = _load(base / "prompts" / "writer_structure.txt")

    from src.config import cfg
    c = cfg()
    gemini = init_gemini_client(c["GOOGLE_API_KEY"])

    # Reconstruct LiteratureReview object from dict
    lit_review = LiteratureReview(
        papers=literature_review_data.get("papers", []),
        summary=literature_review_data.get("summary", ""),
        themes=literature_review_data.get("themes", []),
        gaps=literature_review_data.get("gaps", []),
        approved=True,  # Mark as approved for this phase
    )

    # Run research with literature context
    research = run_research_with_literature(
        topic=topic,
        domain_guard=domain_guard,
        gemini=gemini,
        literature_review=lit_review,
        tavily_key=os.getenv("TAVILY_API_KEY"),
        additional_context=additional_context,
    )
    brief = research["brief"]
    references = research["references"]

    # Writer pass (tone + structure)
    draft = draft_finance_report(
        client=gemini,
        domain_guard=domain_guard,
        tone=writer_tone,
        structure=writer_structure,
        research_question=topic,
        brief=brief,
        references=references,
        model="gemini-2.0-flash",
        language=language,
    )

    # Export .docx
    formatter = OutputFormatterTool()
    doc = formatter(draft, out_dir="outputs", filename_prefix="ufe_finance_report")

    return {
        "success": True,
        "brief": brief,
        "references": references,
        "preview": brief[:1000],
        "plan_preview": str(research.get("plan"))[:1000],
        "brief_preview": brief[:1000],
        "num_references": str(len(references)),
        "docx_path": doc["path"],
        "literature_included": research.get("literature_included", False),
        "literature_paper_count": len(lit_review.papers),
    }
