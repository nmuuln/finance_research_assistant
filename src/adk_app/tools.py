import os
import logging
from typing import List, Optional

from google.adk.tools.function_tool import FunctionTool
from pydantic import ValidationError

logger = logging.getLogger(__name__)

from src.adk_app.models import DraftOutput, ExportedDocument, ResearchOutput, LiteratureReviewOutput
from src.adk_app.prompts import (
    get_domain_guard,
    get_writer_structure,
    get_writer_tone,
)
from src.config import cfg
from src.llm.writer_agent import draft_finance_report, init_gemini_client
from src.research.orchestrator import run_research as orchestrate_research
from src.research.literature_review import (
    run_literature_review,
    format_literature_review_for_display,
)
from src.tools.output_formatter import OutputFormatterTool


def _get_gemini_client():
    config = cfg()
    key = config.get("GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY", "")
    return init_gemini_client(key)


def run_academic_review(topic: str, language: str = "mn") -> dict:
    """
    Search academic databases and synthesize a literature review.

    This tool searches Semantic Scholar and OpenAlex for academic papers
    on the given topic, then synthesizes findings into a structured
    literature review with key themes and research gaps.

    The user must approve the review before main research can proceed.

    Args:
        topic: The research topic to search for in academic databases.
        language: Output language code - "mn" for Mongolian (default), "en" for English.

    Returns:
        A dictionary containing:
        - success: bool indicating if the search succeeded
        - data: Full literature review data (papers, summary, themes, gaps, search_query)
        - formatted_display: IMPORTANT - A complete markdown-formatted literature review
          that you MUST show to the user. It includes all papers with titles, authors,
          year, citations, DOI links, abstracts, synthesis, themes, and gaps.
        - paper_count: Number of papers found
        - requires_approval: Always True - wait for user approval before proceeding
    """
    if not topic or not topic.strip():
        return {"success": False, "error": "Topic must be a non-empty string."}

    client = _get_gemini_client()
    domain_guard = get_domain_guard()
    config = cfg()

    try:
        review = run_literature_review(
            topic=topic,
            domain_guard=domain_guard,
            gemini=client,
            semantic_scholar_key=config.get("SEMANTIC_SCHOLAR_API_KEY"),
            openalex_email=config.get("OPENALEX_EMAIL"),
            max_papers_per_source=5,
            language=language,
        )
    except Exception as exc:
        logger.error(f"run_academic_review failed: {exc}", exc_info=True)
        return {"success": False, "error": f"Literature review failed: {exc}"}

    output = LiteratureReviewOutput(
        papers=review.papers,
        summary=review.summary,
        themes=review.themes,
        gaps=review.gaps,
        approved=False,
        search_query=review.search_query,
    )

    return {
        "success": True,
        "data": output.model_dump(),
        "formatted_display": format_literature_review_for_display(review, language=language),
        "requires_approval": True,
        "paper_count": len(review.papers),
    }


def run_research(topic: str) -> dict:
    """Plan and execute deep research for the provided finance topic."""
    if not topic or not topic.strip():
        return {"success": False, "error": "Topic must be a non-empty string."}

    client = _get_gemini_client()
    domain_guard = get_domain_guard()
    tavily_key = os.getenv("TAVILY_API_KEY")

    try:
        research = orchestrate_research(
            topic=topic,
            domain_guard=domain_guard,
            gemini=client,
            tavily_key=tavily_key,
        )
    except Exception as exc:
        logger.error(f"run_research failed: {exc}", exc_info=True)
        return {"success": False, "error": f"run_research failed: {exc}"}

    output = ResearchOutput(
        plan=research.get("plan", {}),
        brief=research.get("brief", ""),
        references=list(research.get("references", [])),
    )
    return {"success": True, "data": output.model_dump()}


def draft_report(
    topic: str,
    brief: str,
    references: Optional[List[str]],
    language: str = "mn",
) -> dict:
    """Draft the final finance report given research brief and references."""
    if not brief or not brief.strip():
        return {"success": False, "error": "Brief must be supplied to draft the report."}

    client = _get_gemini_client()
    domain_guard = get_domain_guard()
    tone = get_writer_tone()
    structure = get_writer_structure()

    refs = references or []

    try:
        report = draft_finance_report(
            client=client,
            domain_guard=domain_guard,
            tone=tone,
            structure=structure,
            research_question=topic,
            brief=brief,
            references=refs,
            model="gemini-2.0-flash",
            language=language,
        )
    except Exception as exc:
        logger.error(f"draft_report failed: {exc}", exc_info=True)
        return {"success": False, "error": f"draft_report failed: {exc}"}

    return {
        "success": True,
        "data": DraftOutput(report_markdown=report).model_dump(),
    }


def export_report(
    report_markdown: str,
    filename_prefix: Optional[str],
) -> dict:
    """Persist the generated report to a .docx file."""
    if not report_markdown or not report_markdown.strip():
        return {"success": False, "error": "Report markdown must be supplied to export."}

    formatter = OutputFormatterTool()
    prefix = filename_prefix or "ufe_finance_report"
    try:
        doc = formatter(
            report_markdown,
            out_dir="outputs",
            filename_prefix=prefix,
        )
    except Exception as exc:
        logger.error(f"export_report failed: {exc}", exc_info=True)
        return {"success": False, "error": f"export_report failed: {exc}"}

    try:
        exported = ExportedDocument.model_validate(doc).model_dump()
    except ValidationError:
        # fall back to manual construction if python-docx output changes
        fallback = ExportedDocument(
            path=doc.get("path", ""),
            text=doc.get("text"),
        )
        exported = fallback.model_dump()

    return {"success": True, "data": exported}


def build_function_tools() -> List[FunctionTool]:
    """Expose the orchestrator, drafting, and export utilities as ADK tools."""
    return [
        FunctionTool(run_academic_review),
        FunctionTool(run_research),
        FunctionTool(draft_report),
        FunctionTool(export_report),
    ]
