# UFE Research Writer - Custom UI

A complete full-stack application with custom SvelteKit UI for the UFE Research Writer agent, featuring session management, file uploads, and artifact visualization.

## Features

### Backend (FastAPI)
- ✅ **Session Management**: Create and manage research sessions with persistent storage
- ✅ **File Upload**: Support for PDF, Excel, and CSV file uploads
- ✅ **File Processing**: Automatic text/data extraction from uploaded files
- ✅ **Research Pipeline**: Integrated web research with uploaded file context
- ✅ **Report Generation**: Thesis-style finance reports in Mongolian/English
- ✅ **Artifact Storage**: SQLite database for sessions, artifacts, and files
- ✅ **Cloud Storage**: Upload generated reports to DigitalOcean Spaces

### Frontend (SvelteKit)
- ✅ **Session List**: Browse all research sessions with metadata
- ✅ **Session Details**: View session info, files, and artifacts
- ✅ **File Upload**: Drag-and-drop file upload interface
- ✅ **Artifact Viewer**: Beautiful markdown rendering of research reports
- ✅ **Responsive Design**: Mobile-friendly interface
- ✅ **Real-time Updates**: Live status indicators for processing

## Architecture

```
┌─────────────────────────────────────┐
│         SvelteKit Frontend          │
│    (Port 5173 - Development)        │
│    (Embedded in prod build)         │
└──────────────┬──────────────────────┘
               │ HTTP/API
┌──────────────▼──────────────────────┐
│       FastAPI Backend (8000)        │
│  - Session Management               │
│  - File Upload & Processing         │
│  - Research Orchestration           │
│  - Report Generation                │
└──────────────┬──────────────────────┘
               │
     ┌─────────┼─────────┐
     │         │         │
┌────▼───┐ ┌──▼────┐ ┌─▼──────┐
│ SQLite │ │ Gemini│ │ Tavily │
│   DB   │ │  API  │ │  API   │
└────────┘ └───────┘ └────────┘
```

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+
- Google Gemini API key
- Tavily API key
- DigitalOcean Spaces (optional, for file storage)

### 1. Backend Setup

```bash
# Install Python dependencies
pip install -r requirements.txt

# Create environment file
cp .env.example .env

# Edit .env with your API keys
nano .env

# Run the API server
python run_api.py
```

The API will be available at `http://localhost:8000`

### 2. Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The frontend will be available at `http://localhost:5173`

### 3. Using Docker Compose (Recommended)

```bash
# Start all services
docker-compose up

# Backend: http://localhost:8000
# Frontend: http://localhost:5173
```

## Environment Variables

Create a `.env` file with:

```env
# Required
GOOGLE_API_KEY=your_gemini_api_key
TAVILY_API_KEY=your_tavily_api_key

# Optional - DigitalOcean Spaces
SPACES_ACCESS_KEY=your_spaces_key
SPACES_SECRET_KEY=your_spaces_secret
SPACES_REGION=nyc3
SPACES_BUCKET=ufe-research-reports
SPACES_ENDPOINT=https://nyc3.digitaloceanspaces.com

# Database
DATABASE_PATH=data/app.db
```

## API Endpoints

### Sessions
- `POST /api/sessions` - Create new session
- `GET /api/sessions` - List all sessions
- `GET /api/sessions/{id}` - Get session details
- `DELETE /api/sessions/{id}` - Delete session

### File Upload
- `POST /api/sessions/{id}/upload` - Upload file
- `GET /api/sessions/{id}/files` - List uploaded files

### Research & Reports
- `POST /api/sessions/{id}/research` - Run research
- `POST /api/sessions/{id}/report` - Generate report
- `GET /api/sessions/{id}/artifacts` - List artifacts

### Artifacts
- `GET /api/artifacts/{id}` - Get specific artifact

## Usage Workflow

1. **Create Session**
   - Click "New Session"
   - Enter research topic (e.g., "Mongolia's sovereign credit rating")
   - Select language (Mongolian/English)

2. **Upload Files (Optional)**
   - Upload PDF reports, Excel data, or CSV files
   - System automatically processes and extracts content
   - Files are incorporated into research context

3. **Run Research**
   - Click "Run Research"
   - System searches web and analyzes uploaded files
   - Generates comprehensive research brief with citations

4. **Generate Report**
   - Click "Generate Report"
   - AI creates thesis-style document
   - Report appears in artifact viewer

5. **View & Download**
   - Read report in beautiful markdown viewer
   - Download .docx file for offline use
   - Share public URL from cloud storage

## Database Schema

### Sessions Table
```sql
- id (TEXT, PRIMARY KEY)
- created_at (TIMESTAMP)
- updated_at (TIMESTAMP)
- topic (TEXT)
- language (TEXT)
- status (TEXT)
- metadata (TEXT/JSON)
```

### Artifacts Table
```sql
- id (INTEGER, PRIMARY KEY)
- session_id (TEXT, FK)
- created_at (TIMESTAMP)
- title (TEXT)
- content (TEXT)
- research_brief (TEXT)
- references (TEXT)
- file_url (TEXT)
- metadata (TEXT/JSON)
```

### Uploaded Files Table
```sql
- id (INTEGER, PRIMARY KEY)
- session_id (TEXT, FK)
- uploaded_at (TIMESTAMP)
- filename (TEXT)
- file_type (TEXT)
- storage_path (TEXT)
- processed (BOOLEAN)
- extracted_content (TEXT)
- metadata (TEXT/JSON)
```

## Deployment

### DigitalOcean App Platform

1. **Using App Spec**:
```bash
doctl apps create --spec .do/app.yaml
```

2. **Set Environment Variables**:
   - Add secrets in DigitalOcean dashboard
   - Set `GOOGLE_API_KEY`, `TAVILY_API_KEY`, etc.

3. **Deploy**:
```bash
git push origin main
# Auto-deploys on push
```

### Manual Docker Deployment

```bash
# Build fullstack image
docker build -f Dockerfile.fullstack -t ufe-research:latest .

# Run container
docker run -p 8080:8080 \
  -e GOOGLE_API_KEY=$GOOGLE_API_KEY \
  -e TAVILY_API_KEY=$TAVILY_API_KEY \
  -v $(pwd)/data:/app/data \
  ufe-research:latest
```

## File Processing

### Supported Formats
- **PDF**: Research papers, financial reports
- **Excel/CSV**: Financial data, datasets
- **Text**: Notes, reference materials

### Processing Pipeline
1. File uploaded to `data/uploads/{session_id}/`
2. Content extracted using appropriate parser:
   - PDF: `pypdf` library
   - Excel/CSV: `pandas` library
3. Text summarized and added to research context
4. Used in research brief synthesis

## Development

### Frontend Structure
```
frontend/
├── src/
│   ├── routes/
│   │   ├── +layout.svelte      # Main layout
│   │   ├── +page.svelte         # Session list
│   │   ├── new/+page.svelte     # New session
│   │   └── sessions/[id]/+page.svelte  # Session detail
│   ├── app.html
│   └── app.css
├── package.json
└── svelte.config.js
```

### Backend Structure
```
src/
├── api/
│   └── app.py              # FastAPI application
├── database/
│   └── models.py           # SQLite ORM
├── tools/
│   ├── file_processor.py   # File extraction
│   └── output_formatter.py # Document generation
├── research/
│   └── orchestrator.py     # Research pipeline
└── llm/
    └── writer_agent.py     # Report generation
```

### Building for Production

```bash
# Build frontend
cd frontend
npm run build

# Build Docker image
docker build -f Dockerfile.fullstack -t ufe-research:prod .
```

## Troubleshooting

### Database Issues
```bash
# Reset database
rm data/app.db
python -c "from src.database import Database; Database().init_db()"
```

### File Upload Errors
- Check `data/uploads/` directory exists and is writable
- Verify file size limits (default: 10MB)
- Ensure `python-multipart` is installed

### API Connection Issues
- Frontend expects API at `http://localhost:8000`
- Update `vite.config.ts` proxy if API runs on different port
- Check CORS settings in `src/api/app.py`

## Performance Considerations

- **SQLite Limits**: For production with >100 concurrent users, migrate to PostgreSQL
- **File Storage**: Large files should go to object storage (Spaces/S3)
- **Caching**: Consider Redis for session caching
- **Rate Limiting**: Add rate limiting for API endpoints

## Security Notes

- API keys stored in environment variables (never in code)
- File uploads validated by type and size
- User input sanitized before database insertion
- CORS configured for production domains
- HTTPS required for production deployment

## License

Private - UFE Research Writer

## Support

For issues or questions:
1. Check existing GitHub issues
2. Review API logs: `docker-compose logs api`
3. Check browser console for frontend errors
