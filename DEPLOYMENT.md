# Cloud Run Deployment Guide

This guide walks you through deploying the UFE Research Writer agent to Google Cloud Run.

## Prerequisites

1. **Google Cloud Account**
   - Active GCP project
   - Billing enabled
   - Owner or Editor role

2. **Local Tools**
   - [Google Cloud SDK (gcloud)](https://cloud.google.com/sdk/docs/install)
   - Docker (optional, for local testing)

3. **API Keys**
   - Google API Key (Gemini API access)
   - Tavily API Key (web search)

## Quick Start Deployment

### Step 1: Configure Environment Variables

```bash
# Copy the example .env file
cp .env.example .env

# Edit .env and add your API keys
nano .env
```

Required variables in `.env`:
```bash
GOOGLE_API_KEY=your-actual-google-api-key
TAVILY_API_KEY=your-actual-tavily-api-key
LANGUAGE=mn  # or "en"
```

### Step 2: Deploy to Cloud Run

```bash
# Make the deployment script executable (already done)
chmod +x deploy.sh

# Run deployment (replace with your GCP project ID)
./deploy.sh your-gcp-project-id us-central1
```

The script will:
- Enable required GCP APIs
- Build your Docker container
- Deploy to Cloud Run
- Output your service URL

### Step 3: Test Your Deployment

```bash
# Health check
curl https://your-service-url.run.app/healthz

# Create a session
curl -X POST https://your-service-url.run.app/sessions \
  -H 'Content-Type: application/json' \
  -d '{"user_id": "test-user"}'

# Send a chat message
curl -X POST https://your-service-url.run.app/chat \
  -H 'Content-Type: application/json' \
  -d '{
    "user_id": "test-user",
    "session_id": "session-1",
    "message": "Монголын санхүүгийн зах зээлийн талаар судалгаа хийх"
  }'
```

## Manual Deployment Steps

If you prefer manual control:

### 1. Install and Configure gcloud

```bash
# Install gcloud CLI
# macOS: brew install google-cloud-sdk
# Linux: https://cloud.google.com/sdk/docs/install

# Login and set project
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

### 2. Enable Required APIs

```bash
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
```

### 3. Build Container

```bash
# Build and push to Google Container Registry
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/ufe-research-writer
```

### 4. Deploy to Cloud Run

```bash
gcloud run deploy ufe-research-writer \
  --image gcr.io/YOUR_PROJECT_ID/ufe-research-writer \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "GOOGLE_API_KEY=your-key,TAVILY_API_KEY=your-key" \
  --memory 2Gi \
  --cpu 2 \
  --timeout 900 \
  --max-instances 10
```

## Configuration Options

### Resource Allocation

- **Memory**: 2Gi (recommended for Gemini processing)
- **CPU**: 2 cores
- **Timeout**: 900s (15 minutes for long research tasks)
- **Max Instances**: 10 (adjust based on expected traffic)
- **Min Instances**: 0 (cost-effective, slight cold start delay)

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GOOGLE_API_KEY` | Yes | Gemini API key from AI Studio |
| `TAVILY_API_KEY` | Yes | Tavily search API key |
| `LANGUAGE` | No | Default output language (`mn` or `en`), defaults to `mn` |
| `PORT` | No | Server port (Cloud Run sets this automatically) |

### Security Settings

Current deployment allows unauthenticated access. For production:

```bash
# Deploy with authentication required
gcloud run deploy ufe-research-writer \
  --no-allow-unauthenticated \
  # ... other flags
```

Then use:
- Cloud IAM for access control
- API Gateway for rate limiting
- Cloud Armor for DDoS protection

## CI/CD Setup (Optional)

### Automated Deployment with Cloud Build

1. **Connect GitHub Repository**
   ```bash
   # In GCP Console: Cloud Build > Triggers > Connect Repository
   ```

2. **Configure Substitution Variables**

   In Cloud Build trigger settings, add:
   - `_GOOGLE_API_KEY`: Your Gemini API key
   - `_TAVILY_API_KEY`: Your Tavily API key
   - `_LANGUAGE`: Default language

3. **Create Trigger**
   - Event: Push to main branch
   - Configuration: `cloudbuild.yaml`
   - Auto-deploy on every commit

## Local Testing

Test the container locally before deploying:

```bash
# Build locally
docker build -t ufe-research-writer .

# Run locally
docker run -p 8080:8080 \
  --env-file .env \
  ufe-research-writer

# Test
curl http://localhost:8080/healthz
```

## Monitoring and Logs

### View Logs

```bash
# Real-time logs
gcloud run services logs tail ufe-research-writer --region us-central1

# View in Cloud Console
# https://console.cloud.google.com/run
```

### Metrics

Monitor in Cloud Console:
- Request count
- Response time
- Error rate
- Instance count
- Memory/CPU usage

## Cost Optimization

Cloud Run pricing is based on:
- **CPU**: Allocated during request processing
- **Memory**: Allocated during request processing
- **Requests**: Per million requests

**Estimated costs** (us-central1):
- Light usage (<1000 requests/month): ~$5-10/month
- Medium usage (10k requests/month): ~$30-50/month
- Gemini API costs separate (pay-per-token)

**Tips to reduce costs**:
- Set `min-instances=0` (avoid idle charges)
- Use `--cpu-throttling` flag
- Enable request timeout
- Monitor and optimize token usage

## Troubleshooting

### Common Issues

**1. Container build fails**
```bash
# Check Docker build locally first
docker build -t test .
```

**2. Service timeout**
```bash
# Increase timeout for long research tasks
--timeout 900
```

**3. Out of memory**
```bash
# Increase memory allocation
--memory 4Gi
```

**4. API key errors**
```bash
# Verify environment variables are set
gcloud run services describe ufe-research-writer \
  --region us-central1 \
  --format="value(spec.template.spec.containers[0].env)"
```

**5. Permission errors**
```bash
# Ensure service account has required roles
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:YOUR_SERVICE_ACCOUNT" \
  --role="roles/run.admin"
```

## Production Checklist

Before going live:

- [ ] Configure authentication (remove `--allow-unauthenticated`)
- [ ] Set up custom domain
- [ ] Enable Cloud CDN
- [ ] Configure rate limiting
- [ ] Set up monitoring alerts
- [ ] Enable error reporting
- [ ] Implement backup strategy for session data
- [ ] Configure CORS properly for your frontend
- [ ] Set up Cloud Armor for DDoS protection
- [ ] Review and optimize costs
- [ ] Document API endpoints
- [ ] Set up staging environment
- [ ] Load testing

## Updating the Deployment

```bash
# Make code changes, then redeploy
./deploy.sh YOUR_PROJECT_ID us-central1

# Or manually
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/ufe-research-writer
gcloud run deploy ufe-research-writer \
  --image gcr.io/YOUR_PROJECT_ID/ufe-research-writer \
  --region us-central1
```

## Rollback

```bash
# List revisions
gcloud run revisions list --service ufe-research-writer

# Rollback to previous revision
gcloud run services update-traffic ufe-research-writer \
  --to-revisions REVISION_NAME=100
```

## Support

- Cloud Run Documentation: https://cloud.google.com/run/docs
- Google ADK Documentation: https://cloud.google.com/agent-builder/docs
- Project Issues: Create issue in repository
