# Full-Stack Deployment Guide

Deploy the UFE Research Writer with custom SvelteKit UI to Google Cloud Run.

## Overview

This deployment includes:
- **Frontend**: Custom SvelteKit UI with session management, file uploads, and artifacts viewer
- **Backend**: FastAPI with ADK agent integration, SQLite database, and DigitalOcean Spaces storage
- **Deployment**: Google Cloud Run with multi-stage Docker build

## Prerequisites

1. **Google Cloud Project** with billing enabled
2. **gcloud CLI** installed and configured
3. **Environment Variables** configured in `.env`

## Required Environment Variables

Create a `.env` file with the following:

```bash
# Google Gemini API
GOOGLE_API_KEY=your-google-api-key

# Tavily Search API
TAVILY_API_KEY=your-tavily-api-key

# GCP Project
PROJECT_ID=your-gcp-project-id

# Google Discovery Engine (optional)
GDR_APP_ID=your-gdr-app-id
GDR_LOCATION=global
GDR_COLLECTION=your-collection-id
GDR_ASSISTANT=your-assistant-id

# DigitalOcean Spaces (S3-compatible storage)
SPACES_ACCESS_KEY=your-spaces-access-key
SPACES_SECRET_KEY=your-spaces-secret-key
SPACES_REGION=sgp1
SPACES_BUCKET=finance-bucket
```

## Deployment Steps

### Option 1: Deploy to Google Cloud Run

```bash
# Make the deployment script executable
chmod +x deploy-fullstack.sh

# Deploy (replace with your GCP project ID)
./deploy-fullstack.sh YOUR_PROJECT_ID us-central1
```

### Option 2: Manual Deployment

```bash
# 1. Set your GCP project
gcloud config set project YOUR_PROJECT_ID

# 2. Enable required APIs
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    containerregistry.googleapis.com

# 3. Build the container
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/ufe-research-fullstack -f Dockerfile.fullstack

# 4. Deploy to Cloud Run
gcloud run deploy ufe-research-fullstack \
    --image gcr.io/YOUR_PROJECT_ID/ufe-research-fullstack \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --set-env-vars-file .env \
    --memory 4Gi \
    --cpu 2 \
    --timeout 3600
```

## Local Testing

Test the full-stack app locally before deploying:

```bash
# 1. Build the frontend
cd frontend
npm install
npm run build
cd ..

# 2. Run the full-stack app
python run_fullstack.py
```

The app will be available at http://localhost:8080

## What's Deployed

### Frontend Routes
- `/` - Session list
- `/new` - Create new session
- `/sessions/{id}` - Session detail with chat interface

### Backend API
- `/api/sessions` - Session management
- `/api/sessions/{id}/agent-chat` - ADK agent chat
- `/api/sessions/{id}/upload` - File upload
- `/api/sessions/{id}/research` - Run research pipeline
- `/api/sessions/{id}/report` - Generate report
- `/health` - Health check

### Features
- ✅ Multi-language support (Mongolian/English)
- ✅ File uploads (PDF, Excel, CSV) to DigitalOcean Spaces
- ✅ ADK agent integration with tool calling
- ✅ Research report generation with .docx export
- ✅ Session management with SQLite database
- ✅ Artifacts viewer with markdown rendering
- ✅ Files viewer with download capability

## Architecture

```
┌─────────────────────────────────────────┐
│         SvelteKit Frontend              │
│  (Build output served as static files)  │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│          FastAPI Backend                │
│  ┌─────────────────────────────────┐   │
│  │  ADK Agent (Gemini + Tools)     │   │
│  └─────────────────────────────────┘   │
│  ┌─────────────────────────────────┐   │
│  │  SQLite Database                │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│     DigitalOcean Spaces Storage         │
│  (Uploaded files + Generated reports)   │
└─────────────────────────────────────────┘
```

## Troubleshooting

### Frontend not loading
- Check that `frontend/build/client` directory exists
- Verify `npm run build` completed successfully
- Check browser console for 404 errors

### API routes not working
- Verify environment variables are set
- Check Cloud Run logs: `gcloud run logs tail ufe-research-fullstack`
- Test health endpoint: `curl https://YOUR_URL/health`

### File uploads failing
- Verify DigitalOcean Spaces credentials are correct
- Check that bucket exists and has proper permissions
- Review Cloud Run logs for error messages

## Cost Optimization

Cloud Run charges based on:
- **CPU/Memory**: 4GB RAM, 2 vCPU (only while handling requests)
- **Storage**: SQLite database stored in container (ephemeral)
- **Network**: Egress to DigitalOcean Spaces

Recommended settings:
- `--min-instances 0` - Scale to zero when idle
- `--max-instances 10` - Cap concurrent instances
- `--timeout 3600` - Allow long research operations

## Next Steps

After deployment:
1. Access your app at the Cloud Run URL
2. Create a research session
3. Upload reference materials
4. Ask the agent to research and generate reports
5. Download reports from the Artifacts tab

For production use:
- Set up custom domain
- Configure authentication
- Enable Cloud SQL for persistent database
- Set up monitoring and alerts
