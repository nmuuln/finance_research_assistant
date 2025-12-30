# Comprehensive Project Documentation: UFE Research Writer

## Overview

UFE Research Writer is a sophisticated AI-powered finance research agent designed to automate finance-focused research and report generation. It orchestrates multiple AI services (Gemini Deep Research, Tavily web search) and a structured Gemini writer to produce thesis-style finance reports, primarily in Mongolian with optional English support.

---

## Project Architecture

### High-Level System Flow

```
User Input (Topic)
    ↓
Research Orchestrator (src/research/orchestrator.py)
    ├─→ Query Planning (Gemini 2.0 Flash)
    ├─→ Web Search (Tavily API)
    ├─→ Article Fetching & Cleaning (BeautifulSoup + readability)
    └─→ Note Extraction (Gemini Flash)
    ↓
Research Brief Synthesis (Gemini)
    ↓
Writer Agent (src/llm/writer_agent.py)
    ├─→ Tone Application
    ├─→ Structure Enforcement
    └─→ Domain Guardrails
    ↓
Output Formatter (python-docx)
    ↓
.docx Report + Cloud Storage (Optional)
```

---

## Project Structure

### Root Directory Layout

```
finance-research-agent/
├── src/                          # Core application code
│   ├── adk_app/                  # Google ADK integration
│   ├── api/                      # FastAPI backend
│   ├── database/                 # SQLite database models
│   ├── llm/                      # LLM interactions
│   ├── prompts/                  # Prompt templates
│   ├── research/                 # Research pipeline
│   ├── tools/                    # Utilities (file processing, output)
│   └── utils/                    # Helper functions
├── adk_agents/                   # ADK agent definitions
├── frontend/                     # SvelteKit web UI
├── .do/                          # DigitalOcean App Platform config
├── outputs/                      # Generated reports (local)
├── data/                         # Database and uploads
├── run.py                        # CLI batch pipeline
├── run_adk.py                    # ADK console interface
├── run_adk_web.py                # ADK web interface
├── run_api.py                    # FastAPI server
├── run_fullstack.py              # Combined API + Frontend
├── requirements.txt              # Python dependencies
└── docker-compose.yml            # Multi-container setup
```

---

## Core Modules Explained

### 1. Research Pipeline (`src/research/`)

#### `orchestrator.py` - Main Research Coordinator
**Location:** src/research/orchestrator.py:1

**Purpose:** Orchestrates the entire research process from query planning to brief synthesis.

**Key Functions:**

- `plan_queries()` (line 53): Uses Gemini to decompose research topic into sub-questions and search queries
- `build_brief_from_notes()` (line 67): Synthesizes structured notes into a research brief
- `run_research()` (line 93): Main orchestrator that:
  1. Plans search queries
  2. Searches Tavily for results
  3. Fetches and cleans articles
  4. Extracts structured notes
  5. Synthesizes final brief

**Token Management:**
- Implements soft cap (11,000 tokens) and hard cap (12,000 tokens)
- Truncates notes to stay within limits
- Estimates tokens using 4 chars per token approximation

#### `tavily_search.py` - Web Search Integration
**Purpose:** Interfaces with Tavily API for web search results

#### `fetch.py` - Article Extraction
**Purpose:** Fetches URLs and cleans HTML using `readability-lxml` and BeautifulSoup

#### `notes.py` - Structured Note Extraction
**Purpose:** Uses Gemini Flash to extract structured claims, data points, and quotes from articles with provenance tracking

---

### 2. LLM Integration (`src/llm/`)

#### `writer_agent.py` - Report Generation
**Location:** src/llm/writer_agent.py:1

**Key Function:** `draft_finance_report()` (line 35)

**Features:**
- Multilingual support (Mongolian/English)
- Applies domain guardrails, tone, and structure
- Enforces numbered citations mapped to reference list
- Uses Gemini 2.0 Flash model
- Retry logic via `@retry_gemini_call` decorator

**Language Directives:**
- Mongolian (default): Formal academic tone, transliteration of technical terms
- English: Formal academic tone, preserves Mongolian names
- Automatic fallback to Mongolian

---

### 3. Pipeline Module (`src/pipeline.py`)

**Location:** src/pipeline.py:1

**Purpose:** Batch processing pipeline that chains all components.

**Workflow:**
1. Load prompts (domain guard, tone, structure)
2. Initialize Gemini client
3. Run research orchestration
4. Execute writer pass
5. Export to .docx

**Function:** `run_pipeline()` (line 14)
- Parameters: topic, language, additional_context (for uploaded files)
- Returns: Dictionary with brief, references, preview, and docx path

---

### 4. ADK Integration (`src/adk_app/`)

Google's Agent Development Kit (ADK) integration for conversational agents.

#### `agent.py` - ADK Agent Definition
**Location:** src/adk_app/agent.py:1

**Agent Identity:** "UFE Research Writer агент"

**Conversational Workflow:**
1. Greet user and clarify research focus
2. Call `run_research` tool with topic
3. Call `draft_report` tool after research
4. Call `export_report` tool to generate .docx
5. Provide download URL (cloud or local)

**State Management:**
- `research_brief`: Stored research output
- `research_plan`: Query plan
- `research_references`: Citation list
- `draft_markdown`: Generated report
- `report_path`: File location

#### `tools.py` - ADK Function Tools
**Location:** src/adk_app/tools.py:1

**Three Main Tools:**

1. **run_research(topic)** (line 28)
   - Plans and executes research
   - Returns: `{success: bool, data: {plan, brief, references}}`

2. **draft_report(topic, brief, references, language)** (line 56)
   - Drafts final report from research brief
   - Returns: `{success: bool, data: {report_markdown}}`

3. **export_report(report_markdown, filename_prefix)** (line 95)
   - Exports to .docx
   - Returns: `{success: bool, data: {path, url, size_bytes}}`

All tools return success/error envelopes for agent reasoning.

#### `models.py` - Pydantic Schemas
**Location:** src/adk_app/models.py:1

Defines type-safe data models for tool inputs/outputs.

---

### 5. API Backend (`src/api/`)

#### `app.py` - FastAPI Application
**Location:** src/api/app.py:1

**Comprehensive REST API with:**

**Session Management:**
- `POST /api/sessions` - Create session
- `GET /api/sessions` - List sessions
- `GET /api/sessions/{id}` - Get session details
- `DELETE /api/sessions/{id}` - Delete session

**File Upload:**
- `POST /api/sessions/{id}/upload` - Upload file (PDF, CSV, Excel)
- `GET /api/sessions/{id}/files` - List uploaded files
- Automatic content extraction and processing
- Cloud storage integration (DigitalOcean Spaces)

**Research & Reports:**
- `POST /api/sessions/{id}/research` - Run research with optional file context
- `POST /api/sessions/{id}/report` - Generate thesis-style report
- `GET /api/sessions/{id}/artifacts` - List generated reports

**Message/Chat:**
- `POST /api/sessions/{id}/messages` - Save message
- `GET /api/sessions/{id}/messages` - Get conversation history
- `POST /api/sessions/{id}/agent-chat` - Chat with ADK agent

**Features:**
- CORS middleware for frontend integration
- SQLite database for persistence
- DigitalOcean Spaces for cloud storage
- File processing pipeline (PDF, Excel, CSV)
- ADK agent integration for conversational interface

---

### 6. Database Layer (`src/database/`)

#### `models.py` - Database Manager
**Location:** src/database/models.py:1

**SQLite Database with 4 Tables:**

1. **sessions** - Research sessions
   - id, created_at, updated_at, topic, language, status, metadata

2. **artifacts** - Generated reports
   - id, session_id, title, content, research_brief, reference_list, file_url, metadata

3. **uploaded_files** - User-uploaded files
   - id, session_id, filename, file_type, storage_path, processed, extracted_content, metadata

4. **messages** - Conversation history
   - id, session_id, role, content, metadata

**Key Features:**
- Foreign key relationships with CASCADE delete
- Indexes on session_id for performance
- JSON metadata storage
- Automatic timestamp management

---

### 7. Frontend (`frontend/`)

#### Technology Stack
- **Framework:** SvelteKit
- **Language:** TypeScript
- **Styling:** Vanilla CSS with CSS variables
- **Markdown:** `marked` library
- **Sanitization:** `dompurify`

#### Pages (`frontend/src/routes/`)

1. **`+page.svelte`** - Session List
   - Grid view of all research sessions
   - Shows artifact count, file count
   - Filtering and pagination

2. **`new/+page.svelte`** - New Session
   - Create new research session
   - Topic input and language selection

3. **`sessions/[id]/+page.svelte`** - Session Detail
   - File upload interface
   - Research execution
   - Report generation
   - Artifact viewer with markdown rendering

4. **`+layout.svelte`** - Global Layout
   - Navigation, header, footer
   - CSS variables for theming

#### Build Configuration
**package.json:** Frontend dependencies and scripts
- Adapters: `@sveltejs/adapter-static` or `@sveltejs/adapter-node`
- Build output can be served by FastAPI or standalone

---

## Deployment Configurations

### 1. Google Cloud Run (`DEPLOYMENT.md`)

**Script:** `deploy.sh`

**Process:**
1. Enable Cloud Build, Cloud Run APIs
2. Build container: `gcloud builds submit --tag gcr.io/PROJECT_ID/ufe-research-writer`
3. Deploy with environment variables
4. Auto-scaling: 0-10 instances
5. Resources: 2Gi memory, 2 CPU, 900s timeout

**Environment Variables:**
- GOOGLE_API_KEY, TAVILY_API_KEY
- LANGUAGE (default: mn)
- PROJECT_ID

**CI/CD:** `cloudbuild.yaml` for automated GitHub deployments

---

### 2. DigitalOcean (`DEPLOYMENT_DIGITALOCEAN.md`)

**Two Options:**

#### Option A: App Platform (Recommended)
- **Script:** `deploy-digitalocean.sh`
- **Config:** `.do/app.yaml`
- **Pricing:** $12-24/month (1-2GB RAM)
- **Features:**
  - Auto-scaling
  - GitHub auto-deploy
  - Automatic HTTPS
  - Built-in metrics

**Deployment:**
```bash
doctl apps create --spec .do/app.yaml
```

#### Option B: Droplet (Manual)
- **Pricing:** $18/month (2GB RAM, 2 vCPU)
- **Setup:**
  1. Create Ubuntu 22.04 droplet
  2. Install Docker
  3. Clone repository
  4. Build and run container
  5. Configure Nginx + Let's Encrypt

---

### 3. Docker Configurations

#### `Dockerfile` - Base Image
**Location:** Dockerfile:1

**Features:**
- Python 3.13-slim base
- System dependencies: gcc, libxml2, libxslt (for lxml)
- Installs requirements.txt
- Runs FastAPI with uvicorn on port 8080

#### `Dockerfile.adk-web` - ADK Web Interface
- Similar to base but optimized for ADK web runner

#### `Dockerfile.fullstack` - Combined Frontend + Backend
- Multi-stage build
- Stage 1: Build SvelteKit frontend
- Stage 2: Copy frontend build + Python backend
- Serves both from single container

#### `docker-compose.yml` - Local Development
**Location:** docker-compose.yml:1

**Services:**
1. **api**: Backend on port 8000
2. **frontend**: Dev server on port 5173
3. Volume mounts for hot reload
4. Environment variables from .env

---

### 4. Container Registry (`CONTAINER_REGISTRY.md`)

**Scripts:**
- `build-and-push-do.sh` - Push to DigitalOcean Container Registry
- `build-and-push-fullstack-do.sh` - Push fullstack image
- `deploy-from-registry.sh` - Deploy from existing image

---

## Execution Modes

### 1. Batch Pipeline (CLI)
**Entry:** `run.py`
**Location:** run.py:1

**Usage:**
```bash
python run.py
```

**Process:**
1. Load topic from .env (TOPIC variable)
2. Run complete pipeline
3. Print previews and docx path
4. Exit

**Output:** Console output + .docx file in `outputs/`

---

### 2. ADK Console (Interactive)
**Entry:** `run_adk.py`

**Usage:**
```bash
python run_adk.py
```

**Features:**
- Interactive conversation with agent
- Multi-turn dialogue
- State persistence within session
- Tool invocations visible
- Session logs in `/tmp/agents_log/`

---

### 3. ADK Web Interface
**Entry:** `adk web adk_agents --port 8000`

**Features:**
- Google's built-in web UI
- Session management tabs
- Artifact visualization
- State inspection
- Event stream display

---

### 4. Custom FastAPI Backend
**Entry:** `run_api.py`
**Location:** src/api/app.py:1

**Usage:**
```bash
python run_api.py
```

**Features:**
- Full REST API
- Session + file management
- Database persistence
- Cloud storage integration
- ADK agent endpoint

---

### 5. Fullstack Application
**Entry:** `run_fullstack.py`

**Combines:** FastAPI backend + SvelteKit frontend

**Ports:**
- Backend: 8000
- Frontend: 5173 (dev) or served by backend (prod)

---

## Key Technologies & Libraries

### Python Dependencies (requirements.txt)

**Google Services:**
- `google-genai` - Gemini API
- `google-adk` - Agent Development Kit
- `google-auth`, `google-auth-httplib2`, `google-auth-oauthlib` - Authentication
- `google-cloud-storage` - GCS integration

**Research & Search:**
- `tavily-python` - Web search API
- `beautifulsoup4` - HTML parsing
- `readability-lxml` - Article extraction
- `lxml_html_clean` - HTML sanitization

**Document Processing:**
- `python-docx` - Word document generation
- `pypdf` - PDF text extraction
- `pandas`, `openpyxl` - Excel/CSV processing

**Web Framework:**
- `fastapi` - REST API
- `uvicorn` - ASGI server
- `python-multipart` - File upload support

**Cloud Storage:**
- `boto3` - S3-compatible storage (DigitalOcean Spaces)

**Utilities:**
- `python-dotenv` - Environment variable management
- `requests` - HTTP client

---

### Frontend Dependencies (frontend/package.json)

**Core:**
- `svelte` - UI framework
- `@sveltejs/kit` - Application framework
- `vite` - Build tool
- `typescript` - Type safety

**Content Rendering:**
- `marked` - Markdown parser
- `dompurify` - XSS protection

---

## Configuration Files

### `.env.example` - Environment Template
**Location:** .env.example:1

**Required Variables:**
- GOOGLE_API_KEY - Gemini API key
- TAVILY_API_KEY - Tavily search key

**Optional:**
- PROJECT_ID, GDR_* - Legacy Deep Research settings
- TOPIC - Default research topic
- LANGUAGE - Output language (mn/en)
- SPACES_* - DigitalOcean Spaces configuration
- DATABASE_PATH - SQLite database location

---

### Prompt Templates (`src/prompts/`)

1. **`domain_guard.txt`** - Finance domain enforcement
2. **`writer_tone.txt`** - Professional academic tone
3. **`writer_structure.txt`** - Thesis-style structure

Loaded by both pipeline and ADK agent.

---

## Deployment Scripts Breakdown

### `deploy.sh` - Google Cloud Run
**Location:** deploy.sh:1

**Steps:**
1. Check gcloud CLI installation
2. Validate .env file
3. Set GCP project
4. Enable required APIs
5. Build container with Cloud Build
6. Deploy to Cloud Run with env vars
7. Output service URL

**Usage:**
```bash
./deploy.sh your-gcp-project-id us-central1
```

### `deploy-digitalocean.sh` - DO App Platform
**Similar process but using doctl CLI**

### `quickstart.sh` - One-Command Setup
**Likely combines multiple setup steps**

---

## File Processing Pipeline

### Supported Formats
**Location:** src/tools/file_processor.py

1. **PDF** - `pypdf` extraction
2. **Excel** - `pandas` with openpyxl engine
3. **CSV** - `pandas` parsing

### Processing Flow
1. User uploads file via API
2. File saved to `data/uploads/{session_id}/` or Spaces
3. `FileProcessor.process_file()` extracts content
4. Content summarized to max 3000 chars
5. Added to research context as "Uploaded Files" note
6. Incorporated into research brief synthesis

---

## Cloud Storage Integration

### DigitalOcean Spaces (`src/utils/spaces.py`)

**Features:**
- S3-compatible object storage
- Public/private file URLs
- Upload and download support

**Usage:**
- Uploaded files: `uploads/{session_id}/filename`
- Generated reports: `reports/{session_id}/filename.docx`
- Public URLs for report downloads
- Fallback to local filesystem if not configured

---

## Security & Best Practices

1. **API Keys:** Environment variables only, never committed
2. **File Validation:** Type and size checks before processing
3. **Input Sanitization:** SQL injection prevention via parameterized queries
4. **CORS:** Configured for allowed origins in production
5. **HTTPS:** Required for production deployments
6. **Cascade Deletes:** Database ensures referential integrity
7. **Error Handling:** Try-catch blocks with logging
8. **Rate Limiting:** Should be added for production

---

## Testing & Monitoring

### Health Checks
- `/health` or `/healthz` endpoint
- Returns status and timestamp

### Logging
- ADK logs: `/tmp/agents_log/agent.latest.log`
- Docker logs: `docker logs -f container_name`
- Cloud Run logs: GCP Console or `gcloud run services logs tail`

### Test Setup
**File:** `test_setup.py`
**Likely validates:** API keys, database connection, dependencies

---

## Development Workflow

### Local Development
```bash
# Backend
python run_api.py

# Frontend
cd frontend && npm run dev

# Or both with docker-compose
docker-compose up
```

### Adding Features
1. Add prompts to `src/prompts/`
2. Create tool functions in `src/adk_app/tools.py`
3. Update agent instructions in `src/adk_app/agent.py`
4. Add API endpoints in `src/api/app.py`
5. Update frontend UI in `frontend/src/routes/`

---

## Cost Considerations

### API Costs
- **Gemini API:** Pay per token (input + output)
- **Tavily API:** Pay per search query
- Optimize by caching results and limiting queries

### Infrastructure Costs
- **Google Cloud Run:** ~$5-50/month (depends on usage)
- **DigitalOcean App Platform:** $12-24/month (fixed)
- **DigitalOcean Droplet:** $18/month (fixed)
- **Storage:** Minimal (<$1/month for small datasets)

---

## Known Limitations & Future Enhancements

### Current Limitations
1. SQLite not suitable for >100 concurrent users
2. Token limits require careful note truncation
3. No real-time collaboration
4. Single-threaded research execution

### Potential Enhancements
1. Migrate to PostgreSQL for scale
2. Add Redis caching for session state
3. Implement background job queue (Celery)
4. Add real-time WebSocket updates
5. Multi-language UI (beyond Mongolian/English)
6. Advanced citation management
7. PDF export in addition to .docx
8. Integration with more data sources

---

## Troubleshooting Guide

### Common Issues

**1. Module `readability` not found**
```bash
pip install readability-lxml
```

**2. ADK web app cannot find `research_writer`**
```bash
# Restart ADK with clean cache
adk web adk_agents --port 8000
```

**3. Database locked errors**
- SQLite doesn't handle concurrent writes well
- Consider PostgreSQL for production

**4. Out of memory**
- Increase Docker memory limits
- Use Gemini Flash instead of Pro for initial steps
- Reduce max_results in Tavily searches

**5. API rate limits**
- Add delays between API calls
- Implement exponential backoff
- Cache results when possible

---

## Documentation Files

1. **README.md** - High-level overview and quickstart
2. **DEPLOYMENT.md** - Google Cloud Run deployment
3. **DEPLOYMENT_DIGITALOCEAN.md** - DigitalOcean deployment
4. **DEPLOYMENT_FULLSTACK.md** - Combined frontend+backend deployment
5. **CUSTOM_UI_README.md** - Custom SvelteKit UI documentation
6. **CONTAINER_REGISTRY.md** - Container registry usage
7. **SPACES_SETUP.md** - DigitalOcean Spaces setup
8. **SETUP_GUIDE.md** - Development environment setup

---

## Summary

This is a production-ready, multi-mode AI agent system with:

- **4 Execution Modes:** CLI batch, ADK console, ADK web, Custom API
- **3 Deployment Targets:** Google Cloud Run, DigitalOcean App Platform, DigitalOcean Droplets
- **Full Stack:** Python backend + SvelteKit frontend + SQLite database
- **Cloud Storage:** DigitalOcean Spaces integration
- **File Processing:** PDF, Excel, CSV support
- **Multilingual:** Mongolian (primary) + English
- **Containerized:** Docker and docker-compose ready
- **Well-Documented:** Comprehensive docs for every aspect

The architecture is modular, allowing reuse of core research pipeline across different interfaces while Google ADK provides conversation management, tool orchestration, and logging out of the box.
