from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ResearchOutput(BaseModel):
    """Structured payload returned by the research tool."""

    plan: Dict[str, Any] = Field(
        default_factory=dict,
        description="JSON object describing sub-questions and search queries.",
    )
    brief: str = Field(
        default="",
        description="Markdown research brief derived from the collected notes.",
    )
    references: List[str] = Field(
        default_factory=list,
        description="List of deduplicated reference URLs associated with the brief.",
    )


class DraftOutput(BaseModel):
    """Structured payload returned by the drafting tool."""

    report_markdown: str = Field(
        default="",
        description="Full finance report in markdown with inline numbered citations.",
    )


class ExportedDocument(BaseModel):
    """Metadata returned when exporting the final document."""

    path: str = Field(description="Absolute path to the generated .docx file.")
    text: Optional[str] = Field(
        default=None,
        description="Optional copy of the document contents that were exported.",
    )
    filename: Optional[str] = Field(
        default=None,
        description="Name of the generated file.",
    )
    download_url: Optional[str] = Field(
        default=None,
        description="Public URL to download the file (if uploaded to cloud storage).",
    )
    size_bytes: Optional[int] = Field(
        default=None,
        description="Size of the file in bytes.",
    )


class LiteratureReviewOutput(BaseModel):
    """Structured payload from literature review phase."""

    papers: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of academic papers with metadata (title, authors, year, abstract, citations, DOI, URL).",
    )
    summary: str = Field(
        default="",
        description="Synthesized literature review markdown with themes and citations.",
    )
    themes: List[str] = Field(
        default_factory=list,
        description="Key themes identified across the academic papers.",
    )
    gaps: List[str] = Field(
        default_factory=list,
        description="Research gaps and under-explored areas identified.",
    )
    approved: bool = Field(
        default=False,
        description="Whether user has approved the literature review to proceed.",
    )
    search_query: str = Field(
        default="",
        description="English search query used for academic database search (translated from original topic).",
    )

