# DigitalOcean Full-Stack Deployment Guide

Deploy your custom SvelteKit UI with FastAPI backend to DigitalOcean.

## Quick Start

```bash
# 1. Build and push to DigitalOcean Container Registry
./build-and-push-fullstack-do.sh adk-test latest

# 2. Deploy to App Platform
doctl apps create --spec .do/app-fullstack.yaml

# 3. Set secrets (one-time setup)
# See "Setting Secrets" section below
```

## Prerequisites

1. **DigitalOcean Account** with billing enabled
2. **doctl CLI** installed and authenticated
   ```bash
   # macOS
   brew install doctl

   # Authenticate
   doctl auth init
   ```
3. **Docker Desktop** running locally
4. **DigitalOcean Spaces** bucket created (for file storage)

## Step-by-Step Deployment

### Step 1: Build and Push Image

Build the full-stack Docker image and push to your DigitalOcean Container Registry:

```bash
# Build and push (creates registry if it doesn't exist)
./build-and-push-fullstack-do.sh adk-test latest

# Or specify custom registry and version
./build-and-push-fullstack-do.sh my-registry v1.0.0
```

This will:
- ✅ Build SvelteKit frontend
- ✅ Build Python backend
- ✅ Create multi-stage Docker image
- ✅ Push to DigitalOcean Container Registry

### Step 2: Set Up Environment Secrets

Before deploying, you need to add your API keys as secrets:

```bash
# Add Google Gemini API Key
doctl apps secret create GOOGLE_API_KEY --value "YOUR_API_KEY"

# Add Tavily API Key
doctl apps secret create TAVILY_API_KEY --value "YOUR_API_KEY"

# Add DigitalOcean Spaces credentials
doctl apps secret create SPACES_ACCESS_KEY --value "YOUR_ACCESS_KEY"
doctl apps secret create SPACES_SECRET_KEY --value "YOUR_SECRET_KEY"

# Add Google Discovery Engine credentials (optional)
doctl apps secret create PROJECT_ID --value "YOUR_PROJECT_ID"
doctl apps secret create GDR_APP_ID --value "YOUR_APP_ID"
doctl apps secret create GDR_COLLECTION --value "YOUR_COLLECTION_ID"
doctl apps secret create GDR_ASSISTANT --value "YOUR_ASSISTANT_ID"
```

### Step 3: Deploy to App Platform

```bash
# Create new app from spec
doctl apps create --spec .do/app-fullstack.yaml

# Or update existing app
doctl apps update YOUR_APP_ID --spec .do/app-fullstack.yaml
```

### Step 4: Monitor Deployment

```bash
# List apps
doctl apps list

# Get app details
doctl apps get YOUR_APP_ID

# View logs
doctl apps logs YOUR_APP_ID --type=run

# View build logs
doctl apps logs YOUR_APP_ID --type=build
```

## Deployment Options

### Option A: App Platform (Recommended)

**Pros:**
- Fully managed (auto-scaling, load balancing)
- Easy deployments and rollbacks
- Built-in monitoring
- HTTPS by default

**Pricing:** Starting at $5/month (Professional-XS: 1GB RAM, 1 vCPU)

**Deploy:**
```bash
./build-and-push-fullstack-do.sh
doctl apps create --spec .do/app-fullstack.yaml
```

### Option B: Droplet (Self-Managed)

**Pros:**
- More control over infrastructure
- Can be cheaper for consistent workloads
- Direct SSH access

**Pricing:** Starting at $6/month (Basic Droplet: 1GB RAM, 1 vCPU)

**Deploy:**
```bash
# 1. Build and push image
./build-and-push-fullstack-do.sh

# 2. SSH into droplet
ssh root@YOUR_DROPLET_IP

# 3. Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# 4. Login to registry
doctl registry login

# 5. Create .env file with your secrets
cat > .env << EOF
GOOGLE_API_KEY=your-key
TAVILY_API_KEY=your-key
SPACES_ACCESS_KEY=your-key
SPACES_SECRET_KEY=your-key
SPACES_REGION=sgp1
SPACES_BUCKET=finance-bucket
DATABASE_PATH=/app/data/app.db
EOF

# 6. Run container
docker run -d \
  --name ufe-research \
  -p 80:8080 \
  --env-file .env \
  -v /data/db:/app/data \
  --restart unless-stopped \
  registry.digitalocean.com/adk-test/ufe-research-writer-fullstack:latest

# 7. Check logs
docker logs -f ufe-research
```

## Configuration

### Instance Sizing

Edit `.do/app-fullstack.yaml`:

```yaml
instance_size_slug: professional-xs  # 1GB RAM, 1 vCPU - $12/mo
# instance_size_slug: professional-s   # 2GB RAM, 1 vCPU - $24/mo
# instance_size_slug: professional-m   # 4GB RAM, 2 vCPU - $48/mo
```

### Auto-Scaling

Add to `.do/app-fullstack.yaml`:

```yaml
instance_count: 1
autoscaling:
  min_instance_count: 1
  max_instance_count: 3
  metrics:
    cpu:
      percent: 80
```

### Custom Domain

After deployment:

```bash
# Add domain
doctl apps update YOUR_APP_ID --add-domain yourdomain.com

# Get nameservers to configure
doctl apps list-domains YOUR_APP_ID
```

## What's Deployed

### Application Structure
```
https://your-app.ondigitalocean.app/
├── /                    → SvelteKit UI (sessions list)
├── /new                 → Create new session
├── /sessions/{id}       → Session detail with chat
└── /api/*              → FastAPI backend
    ├── /sessions       → Session management
    ├── /upload         → File uploads
    ├── /research       → Research pipeline
    └── /report         → Report generation
```

### Features
- ✅ Custom SvelteKit UI (sessions, files, artifacts tabs)
- ✅ FastAPI backend with ADK agent
- ✅ SQLite database (persisted in container volume)
- ✅ File uploads to DigitalOcean Spaces
- ✅ Research report generation (.docx export)
- ✅ Multi-language support (Mongolian/English)

## Updating the Deployment

When you make changes to the code:

```bash
# 1. Rebuild and push with new version
./build-and-push-fullstack-do.sh adk-test v1.0.1

# 2. Update app to use new version
# Edit .do/app-fullstack.yaml - change tag: v1.0.1
doctl apps update YOUR_APP_ID --spec .do/app-fullstack.yaml

# Or force redeployment with latest
doctl apps create-deployment YOUR_APP_ID
```

## Troubleshooting

### Check Deployment Status
```bash
doctl apps get YOUR_APP_ID
```

### View Logs
```bash
# Runtime logs
doctl apps logs YOUR_APP_ID --type=run --follow

# Build logs
doctl apps logs YOUR_APP_ID --type=build
```

### Common Issues

**1. Build fails**
- Check Dockerfile.fullstack exists
- Ensure frontend/package.json is valid
- Check build logs: `doctl apps logs YOUR_APP_ID --type=build`

**2. App crashes on startup**
- Check environment variables are set
- View logs: `doctl apps logs YOUR_APP_ID --type=run`
- Verify database path is writable

**3. File uploads fail**
- Verify Spaces credentials are correct
- Check bucket exists and region matches
- Review CORS settings in Spaces

**4. Frontend not loading**
- Check build output exists: frontend/build/client
- Verify static file serving in run_fullstack.py
- Check browser console for 404 errors

## Costs Estimate

Monthly costs for typical usage:

- **App Platform** (Professional-S): $24/month
  - 2GB RAM, 1 vCPU
  - 100GB bandwidth included

- **Container Registry** (Basic): $5/month
  - 500MB storage
  - 500GB outbound transfer

- **Spaces** (Object Storage): $5/month
  - 250GB storage
  - 1TB outbound transfer

**Total:** ~$34/month for production setup

## Next Steps

1. ✅ Deploy app
2. ✅ Configure custom domain
3. ✅ Set up monitoring alerts
4. ✅ Configure backup strategy for database
5. ✅ Enable CDN for static assets
6. ✅ Set up CI/CD for automatic deployments

## Support

- DigitalOcean Docs: https://docs.digitalocean.com/
- App Platform: https://docs.digitalocean.com/products/app-platform/
- Container Registry: https://docs.digitalocean.com/products/container-registry/
