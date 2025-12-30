# Changelog

## [2024-12-30] Academic Literature Review Feature

### Overview
Added a new literature review phase that runs BEFORE the main research pipeline. This feature searches academic databases and synthesizes findings to provide scholarly context for finance research.

### New Flow
```
Topic → [Topic Translation] → LITERATURE REVIEW → [User Approval] → Main Research → Report
                                     │
                                     ├─ OpenAlex (5 papers)
                                     ├─ Semantic Scholar (5 papers)
                                     └─ Gemini synthesis
```

### Features Added

#### 1. Academic Database Integration
- **OpenAlex**: Free API, 100k requests/day, 10 req/sec
- **Semantic Scholar**: Free tier 100 req/5min (higher with API key)
- Automatic deduplication by DOI
- Results sorted by citation count

#### 2. Multilingual Support
- **Topic Translation**: Mongolian topics are automatically translated to English for academic search
- Synthesis can still be provided in user's preferred language
- Shows both original topic and translated search query

#### 3. Literature Synthesis
- Gemini-powered analysis of academic papers
- Identifies key themes across papers (3-5 themes)
- Discovers research gaps (2-4 gaps)
- Creates structured literature review with inline citations

#### 4. User Approval Workflow
- Literature review presented to user before main research
- User must approve to continue
- Can reject and refine topic if needed

### Files Created

| File | Description |
|------|-------------|
| `src/research/scholar_search.py` | Academic API clients (SemanticScholarSearch, OpenAlexSearch, AcademicSearch) |
| `src/research/literature_review.py` | Literature review orchestration with Gemini synthesis |

### Files Modified

| File | Changes |
|------|---------|
| `src/config.py` | Added `SEMANTIC_SCHOLAR_API_KEY`, `OPENALEX_EMAIL` |
| `.env.example` | Added documentation for new environment variables |
| `src/research/orchestrator.py` | Added `run_research_with_literature()` function |
| `src/pipeline.py` | Added `run_literature_review_phase()`, `run_pipeline_with_literature()` |
| `src/api/app.py` | Added 3 new API endpoints |
| `src/adk_app/tools.py` | Added `run_academic_review()` tool |
| `src/adk_app/agent.py` | Updated workflow to call literature review first |
| `src/adk_app/models.py` | Added `LiteratureReviewOutput` Pydantic model |

### New API Endpoints

```
POST /api/sessions/{id}/literature-review          # Start literature review
POST /api/sessions/{id}/literature-review/approve  # Approve/reject review
POST /api/sessions/{id}/research-with-literature   # Continue with approved review
```

### New ADK Tool

```python
run_academic_review(topic: str) -> dict
```
- Searches Semantic Scholar and OpenAlex
- Translates non-English topics automatically
- Returns papers, synthesis, themes, gaps
- Requires user approval before proceeding

### Environment Variables

```bash
# Optional - increases Semantic Scholar rate limits
SEMANTIC_SCHOLAR_API_KEY=

# Optional - enables OpenAlex polite pool for higher limits
OPENALEX_EMAIL=
```

### Example Usage

**Mongolian Topic Input:**
```
Монголын банкны салбарын эрсдэлийн удирдлага
```

**Translated Search Query:**
```
Risk Management in the Mongolian Banking Sector
```

**Output:**
- 6 academic papers found
- Key themes: Credit Risk Management, SME Finance Access, Technology in Risk Management
- Research gaps: Mongolian-specific studies, Basel implementation analysis

### Technical Notes

- OpenAlex is queried first (more reliable, no API key needed)
- Semantic Scholar has retry logic for rate limiting (429 errors)
- Topic translation uses Gemini to convert to academic English terminology
- All API calls use exponential backoff retry decorator
