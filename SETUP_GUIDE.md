# UFE Research Writer - Complete Setup Guide

## ✅ Fixed Issues

1. **Database Schema**: Fixed SQL syntax error with reserved keyword `references` → renamed to `reference_list`
2. **Virtual Environment**: Created `.venv` for isolated Python dependencies
3. **Import Errors**: Fixed all function imports in API (`draft_finance_report`, `OutputFormatterTool`)
4. **Dependencies**: Installed all required packages in venv

## 🚀 Quick Start (Recommended)

### One-Command Setup
```bash
./quickstart.sh
```

This script will:
- Create `.env` from template (if needed)
- Create data directories
- Set up virtual environment
- Install all Python dependencies
- Initialize SQLite database
- Optionally install frontend dependencies
- Start the application

### Manual Setup

#### 1. Create Virtual Environment
```bash
python3.10 -m venv .venv
source .venv/bin/activate
```

#### 2. Install Python Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### 3. Set Up Environment
```bash
cp .env.example .env
# Edit .env with your API keys
nano .env
```

Required environment variables:
- `GOOGLE_API_KEY` - Gemini API key
- `TAVILY_API_KEY` - Tavily search API key

Optional:
- `SPACES_ACCESS_KEY` - DigitalOcean Spaces
- `SPACES_SECRET_KEY` - DigitalOcean Spaces
- `DATABASE_PATH` - Default: `data/app.db`

#### 4. Initialize Database
```bash
python -c "from src.database import Database; Database()"
```

#### 5. Install Frontend (Optional)
```bash
cd frontend
npm install
cd ..
```

## 🏃 Running the Application

### Option 1: Backend Only
```bash
source .venv/bin/activate
python run_api.py
```
- API: http://localhost:8000
- Docs: http://localhost:8000/docs

### Option 2: Full Stack (2 Terminals)

**Terminal 1 - Backend:**
```bash
source .venv/bin/activate
python run_api.py
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```
- Frontend: http://localhost:5173
- Backend: http://localhost:8000

### Option 3: Docker Compose
```bash
docker-compose up
```
- Frontend: http://localhost:5173
- Backend: http://localhost:8000

## 🧪 Testing Your Setup

Run the verification script:
```bash
source .venv/bin/activate
python test_setup.py
```

Expected output:
```
✅ Database initialization
✅ Create test session
✅ Create test artifact
✅ File processor imports
✅ FastAPI app initialization
✅ Frontend files
✅ Query session and artifacts
✅ ALL TESTS PASSED!
```

## 📁 Project Structure

```
finance-research-agent/
├── .venv/                      # Virtual environment (not in git)
├── data/                       # SQLite DB & uploads (not in git)
│   ├── app.db                 # SQLite database
│   ├── uploads/               # Uploaded files
│   └── outputs/               # Generated reports
├── src/
│   ├── api/
│   │   └── app.py            # FastAPI backend
│   ├── database/
│   │   └── models.py         # SQLite ORM
│   ├── tools/
│   │   ├── file_processor.py # PDF/Excel/CSV processing
│   │   └── output_formatter.py
│   ├── research/
│   │   └── orchestrator.py   # Research pipeline
│   └── llm/
│       └── writer_agent.py   # Report generation
├── frontend/                   # SvelteKit UI
│   ├── src/
│   │   └── routes/
│   │       ├── +page.svelte           # Session list
│   │       ├── new/+page.svelte       # Create session
│   │       └── sessions/[id]/+page.svelte  # Session detail
│   └── package.json
├── .env                        # Environment variables (create from .env.example)
├── requirements.txt            # Python dependencies
├── quickstart.sh              # Automated setup script
├── test_setup.py              # Verification script
└── run_api.py                 # API launcher
```

## 🔧 Common Issues & Solutions

### Issue: "Module not found"
```bash
# Make sure venv is activated
source .venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Issue: "Database locked"
```bash
# Stop all running instances
pkill -f "python run_api.py"

# Remove database and recreate
rm data/app.db
python -c "from src.database import Database; Database()"
```

### Issue: "Port 8000 already in use"
```bash
# Find and kill process
lsof -ti:8000 | xargs kill -9

# Or change port in run_api.py
```

### Issue: Frontend build fails
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

## 🎯 Usage Workflow

1. **Start Services**
   - Backend: `source .venv/bin/activate && python run_api.py`
   - Frontend: `cd frontend && npm run dev`

2. **Create Session**
   - Go to http://localhost:5173
   - Click "New Session"
   - Enter topic: "Mongolia's credit rating outlook"
   - Select language (mn/en)

3. **Upload Files** (Optional)
   - Upload PDF research papers
   - Upload Excel/CSV financial data
   - Files are automatically processed

4. **Run Research**
   - Click "Run Research"
   - System searches web + analyzes files
   - Generates research brief

5. **Generate Report**
   - Click "Generate Report"
   - AI creates thesis-style document
   - View in markdown viewer
   - Download .docx file

## 📊 Database Schema

**sessions**
- id, topic, language, status, created_at, updated_at, metadata

**artifacts** (reports)
- id, session_id, title, content, research_brief, reference_list, file_url, created_at, metadata

**uploaded_files**
- id, session_id, filename, file_type, storage_path, processed, extracted_content, uploaded_at, metadata

**messages** (conversation history)
- id, session_id, role, content, created_at, metadata

## 🚢 Deployment

### DigitalOcean App Platform
```bash
# Using the app spec
doctl apps create --spec .do/app.yaml

# Or use DigitalOcean dashboard
# - Upload Dockerfile.fullstack
# - Set environment variables
# - Deploy
```

### Docker Production Build
```bash
docker build -f Dockerfile.fullstack -t ufe-research:prod .
docker run -p 8080:8080 \
  -e GOOGLE_API_KEY=$GOOGLE_API_KEY \
  -e TAVILY_API_KEY=$TAVILY_API_KEY \
  -v $(pwd)/data:/app/data \
  ufe-research:prod
```

## 📚 API Endpoints

### Sessions
- `POST /api/sessions` - Create new session
- `GET /api/sessions` - List all sessions
- `GET /api/sessions/{id}` - Get session details
- `DELETE /api/sessions/{id}` - Delete session

### File Upload
- `POST /api/sessions/{id}/upload` - Upload file (PDF, Excel, CSV)
- `GET /api/sessions/{id}/files` - List uploaded files

### Research & Reports
- `POST /api/sessions/{id}/research` - Run research pipeline
- `POST /api/sessions/{id}/report` - Generate thesis-style report
- `GET /api/sessions/{id}/artifacts` - List generated reports

### Artifacts
- `GET /api/artifacts/{id}` - Get specific artifact

### Health
- `GET /health` - Health check endpoint

## 🔒 Security Notes

- API keys in `.env` (never commit)
- File uploads validated by type/size
- SQL injection prevented (parameterized queries)
- CORS configured for production
- HTTPS required for production

## 💡 Tips

1. **Development**
   - Use `reload=True` in uvicorn for hot-reload
   - Frontend watches files automatically
   - Check logs: `docker-compose logs -f`

2. **Performance**
   - SQLite good for <100 concurrent users
   - Migrate to PostgreSQL for production
   - Use Redis for session caching
   - Add rate limiting

3. **Maintenance**
   - Backup database regularly: `cp data/app.db backups/`
   - Clean old files: `find data/uploads -mtime +30 -delete`
   - Monitor disk space for uploads

## 📞 Support

- Check logs: `docker-compose logs` or console output
- Verify setup: `python test_setup.py`
- Read full docs: `CUSTOM_UI_README.md`
- Frontend errors: Browser console (F12)
- Backend errors: Terminal output

## 🎉 Success!

If all tests pass, you're ready to use the UFE Research Writer!

Open http://localhost:5173 and start creating research reports.
