# UFE Research Writer

Automates finance-focused research and report generation by orchestrating Gemini Deep Research, Tavily web search, and a structured Gemini writer pass. The system can run end-to-end as a simple CLI pipeline or as a conversational agent deployed through Google’s Agent Development Kit (ADK) with both terminal and web interfaces.

---

## High-Level Architecture

```
┌─────────────┐    plan/queries    ┌────────────────┐    GEMINI (flash/pro)
│  User Input │ ───────────────▶  │ Research Agent │ ──────────────────────┐
└─────────────┘                    │ (planner+tools)│                      │
                                   └───────┬────────┘                      │
                                           │ Tavily search + HTTP fetch    │
                                           ▼                               │
                                  ┌────────────────┐                       │
                                  │ Notes Extract  │ ◀── cleaned articles ◀┘
                                  └───────┬────────┘
                                          │ structured notes
                                          ▼
                                ┌────────────────────┐
                                │ Research Brief     │  (Gemini synthesises notes
                                └───────┬────────────┘   + citations in markdown)
                                        │
                                        ▼
                             ┌────────────────────┐
                             │ Writer Agent       │  (Gemini 2.5 Pro applies
                             └───────┬────────────┘   tone, structure, guardrails)
                                     │
                                     ▼
                          ┌───────────────────────┐
                          │ Docx Exporter         │  (python-docx)
                          └───────────────────────┘
```

*Prompts for domain guardrails, tone, and structure live in `src/prompts/` and are reused throughout the flow.*

---

## Repository Layout

- `src/pipeline.py` – classic “batch” pipeline that loads prompts, runs research, drafts the report, and writes `.docx`.
- `src/research/` – research stack:
  - `orchestrator.py` plans search queries with Gemini, calls Tavily, fetches articles, extracts structured notes, and synthesises a brief.
  - `fetch.py` uses `requests + readability-lxml + BeautifulSoup` to clean article HTML.
  - `notes.py` prompts Gemini Flash to produce structured claims/data points with provenance.
- `src/llm/writer_agent.py` – wraps Gemini 2.5 Pro to apply tone/structure guardrails and produce the final markdown report.
- `src/tools/output_formatter.py` – converts markdown to `.docx` using python-docx.
- `src/adk_app/` – ADK-specific wiring:
  - `prompts.py` cached prompt readers.
  - `models.py` Pydantic schemas for tool payloads.
  - `tools.py` exposes research/drafting/export functions as ADK function tools with success/error envelopes.
  - `agent.py` builds the conversational `LlmAgent` with instructions for multi-turn use (clarify topic → research → draft → export).
- `run.py` – minimal CLI entrypoint for the batch pipeline.
- `run_adk.py` – interactive console chat that uses ADK Runner locally (single-session loop).
- `run_adk_web.py` – FastAPI wrapper exposing `/chat` + `/sessions`, useful for custom UIs.
- `adk_agents/` – package ADK’s CLI/Web runner consumes (`root_agent` exported in `agent.py`, plus `research_writer` subpackage for named app).

---

## Workflows

### 1. Batch Pipeline (non-conversational)
```bash
source .venv/bin/activate
cp .env.example .env   # populate GOOGLE_API_KEY, TAVILY_API_KEY, etc.
python run.py          # prints previews and docx path (defaults to Mongolian output)
```

### 2. Conversational CLI (ADK Runner)
```bash
python run_adk.py
```
Chat with the agent; ask for research, refinements, and say “export report” to trigger `.docx` creation. State updates (e.g., saved report path) are printed inline.

### 3. ADK Web UI
```bash
adk web adk_agents --port 8000
```
Open `http://127.0.0.1:8000`, pick `research_writer`, and converse through Google’s built-in web interface. Sessions, artifacts, and state tabs show the same information captured in the CLI.

### 4. REST/Programmatic Access
```bash
python run_adk_web.py   # runs FastAPI app on port 8000 by default
```
Use `/sessions` to create sessions and POST `/chat` with user messages. Responses include full event parts (text, tool calls, thought signatures) plus `state_delta` entries such as `report_path`.

---

## Configuration

Environment variables consumed through `.env` (loaded via `python-dotenv`):

| Variable            | Purpose                                                |
|---------------------|--------------------------------------------------------|
| `GOOGLE_API_KEY`    | Gemini API key for planner, note extractor, writer     |
| `TAVILY_API_KEY`    | Tavily search key (optional but recommended)           |
| `PROJECT_ID`, `GDR_*` | Additional Discovery Engine settings (legacy Deep Research) |
| `TOPIC`             | Default topic for `run.py` / `run_adk.py`              |
| `LANGUAGE`          | Optional default output language (`mn` or `en`); defaults to Mongolian |

For ADK CLI/Web, the same `.env` file is auto-loaded by the runner.

---

## Key Dependencies

- `google-genai` – access to Gemini Generate Content APIs.
- `google-adk` – Agent Development Kit (runners, tools, FastAPI server, web UI).
- `tavily-python` – web search results used in research stage.
- `readability-lxml`, `beautifulsoup4` – HTML extraction and cleaning.
- `python-docx` – final report export to Microsoft Word format.
- `fastapi`, `uvicorn` – optional REST server (`run_adk_web.py`).
- `pypdf` – lightweight text extraction for PDF sources (improves Step 2 note capture).

---

## Development Notes

- All tool functions return `{ "success": bool, "data" | "error": ... }`, enabling the agent to reason about failures.
- Session state keys (`research_plan`, `research_brief`, `draft_markdown`, `report_path`, etc.) are stored by the agent so follow-up turns can reuse prior work without re-running tools unnecessarily.
- The ADK agent instructions enforce finance-only scope, thesis-style structure, a Mongolian-first experience (with optional English on request), and numbered citations aligned to the references list.
- Logging from ADK commands is written to `/tmp/agents_log/agent.latest.log` for troubleshooting.

---

## Troubleshooting

- **Module `readability` not found** – ensure `pip install -r requirements.txt` in your active virtual environment.
- **ADK web app cannot find `research_writer`** – restart `adk web adk_agents` after any changes; the loader caches module imports.
- **App name mismatch warnings** – resolved by keeping `APP_NAME = "agents"` in ADK runners (`run_adk.py`, `run_adk_web.py`).

---

This architecture keeps the research pipeline reusable: the same core modules power both batch and conversational experiences, while ADK provides session management, tool orchestration, and logging out of the box. Extend by adding new prompts or tools (e.g., spreadsheet generation) and registering them through `src/adk_app/tools.py` and the agent instructions.
