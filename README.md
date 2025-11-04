# UFE Research Writer (Gemini Deep Research + WriterAgent)

This project calls **Gemini Deep Research** via **Discovery Engine `streamAssist`** (`agentId=deep_research`) to
auto-plan, browse, and synthesize a research brief with citations. The brief is then passed to a **WriterAgent** (Gemini API)
that enforces:
- Finance-only domain guard
- Formal academic tone
- Thesis-style structure (Intro, Analysis, Conclusion, Recommendations)
Finally, we export a `.docx`.

> ⚠️ Deep Research API requires Gemini Enterprise + allowlisted access in your GCP project.

## Setup

1. **Auth**: Use Application Default Credentials
   ```bash
   gcloud auth application-default login
