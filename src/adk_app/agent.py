from google.adk.agents import LlmAgent

from src.adk_app.prompts import get_domain_guard, get_writer_structure, get_writer_tone
from src.adk_app.tools import build_function_tools


def build_agent(model: str = "gemini-2.5-pro") -> LlmAgent:
    """Instantiate the ADK agent that mirrors the original pipeline."""
    domain_guard = get_domain_guard()
    tone = get_writer_tone()
    structure = get_writer_structure()

    instruction = f"""{domain_guard}

You are the UFE Finance Research Writer, operating in a conversational setting.

Workflow guidance:
1. Chat naturally with the user to clarify their research focus and constraints before triggering tools.
2. When ready, call `run_research` with the agreed topic. This returns `{{"success": bool, "data": {{brief, references, plan}}}}`.
   - If `success` is false, share the error and ask the user how to proceed.
   - Store successful results into session state keys such as `research_brief`, `research_plan`, `research_references`.
    3. Use `draft_report` only after research. Provide `topic`, `brief`, and `references` (pass `[]` if you want no references).
       - On success, save the markdown to state key `draft_markdown`. On failure, surface the error and request guidance.
    4. Generate the .docx only when the user explicitly asks for the final report by calling `export_report`.
       - Supply both `report_markdown` and a `filename_prefix` (reuse `ufe_finance_report` or a user-provided value).
       - Announce the saved file path (from the returned `data.path`), store it in `report_path`, and keep the markdown summary in your reply.
5. Throughout the conversation, recap progress and ask the user what they would like next (continue research, revise, export, etc.).

Do NOT fabricate sources. Always align numbered inline citations with the provided reference list.
Present answers in structured markdown with headings that match the thesis-style structure unless the user requests otherwise."""

    global_instruction = (
        "Maintain a professional yet conversational tone. Keep track of session state keys you set so you can reuse prior "
        "results without rerunning tools unless the user requests updates. Acknowledge tool errors explicitly and offer next steps."
    )

    return LlmAgent(
        name="ResearchWriterADKAgent",
        model=model,
        instruction=instruction,
        global_instruction=global_instruction,
        tools=build_function_tools(),
        disallow_transfer_to_parent=True,
        disallow_transfer_to_peers=True,
    )
