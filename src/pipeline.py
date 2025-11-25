import os
from typing import Dict
from pathlib import Path

from src.tools.output_formatter import OutputFormatterTool
from src.llm.writer_agent import init_gemini_client, draft_finance_report

# NEW: local research orchestrator
from src.research.orchestrator import run_research

def _load(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")

def run_pipeline(topic: str, include_web: bool = True, language: str = "mn") -> Dict[str, str]:
    base = Path(__file__).parent
    domain_guard = _load(base / "prompts" / "domain_guard.txt")
    writer_tone = _load(base / "prompts" / "writer_tone.txt")
    writer_structure = _load(base / "prompts" / "writer_structure.txt")

    # 1) Init Gemini client (AI Studio key)
    from src.config import cfg
    c = cfg()
    gemini = init_gemini_client(c["GOOGLE_API_KEY"])

    # 2) Research (planner -> search -> fetch -> notes -> brief)
    research = run_research(topic, domain_guard, gemini, tavily_key=os.getenv("TAVILY_API_KEY"))
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
        model="gemini-2.5-flash",
        language=language,
    )

    # 4) Export .docx
    formatter = OutputFormatterTool()
    doc = formatter(draft, out_dir="outputs", filename_prefix="ufe_finance_report")

    return {
        "plan_preview": str(research.get("plan"))[:1000],
        "brief_preview": brief[:1000],
        "num_references": str(len(references)),
        "docx_path": doc["path"],
    }
