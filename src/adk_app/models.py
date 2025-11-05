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

