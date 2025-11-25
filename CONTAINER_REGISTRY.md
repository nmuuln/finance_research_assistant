# DigitalOcean Container Registry Deployment

Deploy your UFE Research Writer by building a container locally and pushing to DigitalOcean Container Registry.

## Why Use Container Registry?

✅ **Full control** - Build locally, push when ready
✅ **Faster deploys** - Pre-built images deploy instantly
✅ **Version control** - Tag and rollback easily
✅ **Multi-platform** - Deploy same image to App Platform, Droplets, or Kubernetes

---

## Prerequisites

1. **DigitalOcean Account** with billing enabled
2. **doctl CLI** installed and authenticated
3. **Docker Desktop** running locally

### Install doctl

```bash
# macOS
brew install doctl

# Linux
snap install doctl

# Windows
# Download from: https://github.com/digitalocean/doctl/releases
```

### Authenticate

```bash
doctl auth init
# Enter your API token from: https://cloud.digitalocean.com/account/api/tokens
```

---

## Quick Start: Build & Deploy

### Step 1: Build and Push Container

```bash
# Build, tag, and push in one command
./build-and-push-do.sh

# Or specify custom registry name and version
./build-and-push-do.sh my-registry v1.0.0
```

This script will:
1. Check/create DigitalOcean Container Registry
2. Build Docker image from `Dockerfile.adk-web`
3. Tag image with registry URL
4. Push to DigitalOcean Container Registry

### Step 2: Deploy to App Platform

```bash
# Deploy from registry
./deploy-from-registry.sh
```

### Step 3: Set Secrets

Go to your app dashboard and add:
- `GOOGLE_API_KEY` (encrypted)
- `TAVILY_API_KEY` (encrypted)

### Step 4: Access Your App

```bash
# Get app URL
doctl apps list --format DefaultIngress
```

---

## Manual Step-by-Step

### 1. Create Container Registry

```bash
# Create registry (one-time setup)
doctl registry create adk-test --region nyc3 --subscription-tier basic

# Login to registry
doctl registry login
```

**Pricing:**
- Basic: $5/month (500 MB storage)
- Professional: $20/month (10 GB storage)

### 2. Build Docker Image

```bash
# Build the web UI image
docker build -t ufe-research-writer-web:latest -f Dockerfile.adk-web .

# Verify image
docker images | grep ufe-research-writer
```

### 3. Tag for Registry

```bash
# Tag with registry URL
docker tag ufe-research-writer-web:latest \
  registry.digitalocean.com/adk-test/ufe-research-writer-web:latest

# Tag with version (optional)
docker tag ufe-research-writer-web:latest \
  registry.digitalocean.com/adk-test/ufe-research-writer-web:v1.0.0
```

### 4. Push to Registry

```bash
# Push latest
docker push registry.digitalocean.com/adk-test/ufe-research-writer-web:latest

# Push version
docker push registry.digitalocean.com/adk-test/ufe-research-writer-web:v1.0.0
```

### 5. Verify Upload

```bash
# List repositories
doctl registry repository list-v2

# List tags
doctl registry repository list-tags ufe-research-writer-web
```

---

## Deploy Options

### Option A: App Platform (Managed)

```bash
# Deploy using spec file
doctl apps create --spec .do/app-from-registry.yaml

# Or via dashboard:
# 1. Go to https://cloud.digitalocean.com/apps
# 2. Create App → From Container Registry
# 3. Select: registry.digitalocean.com/adk-test/ufe-research-writer-web:latest
# 4. Set environment variables
# 5. Deploy
```

**Cost:** $12/month (Professional XS)

### Option B: Droplet (Manual)

```bash
# SSH into your droplet
ssh root@YOUR_DROPLET_IP

# Login to registry
doctl registry login

# Pull and run
docker pull registry.digitalocean.com/adk-test/ufe-research-writer-web:latest

docker run -d \
  --name ufe-research-writer \
  --restart unless-stopped \
  -p 80:8080 \
  -e GOOGLE_API_KEY="your-key" \
  -e TAVILY_API_KEY="your-key" \
  -e LANGUAGE="mn" \
  registry.digitalocean.com/adk-test/ufe-research-writer-web:latest
```

**Cost:** $18/month (2GB Droplet)

### Option C: Kubernetes

```bash
# For production-scale deployments
# See DigitalOcean Kubernetes documentation
```

---

## Version Management

### Tagging Strategy

```bash
# Development
docker tag IMAGE registry.digitalocean.com/REGISTRY/IMAGE:dev

# Staging
docker tag IMAGE registry.digitalocean.com/REGISTRY/IMAGE:staging

# Production with semantic versioning
docker tag IMAGE registry.digitalocean.com/REGISTRY/IMAGE:v1.0.0
docker tag IMAGE registry.digitalocean.com/REGISTRY/IMAGE:latest
```

### Update Deployment

```bash
# Build new version
./build-and-push-do.sh adk-test v1.1.0

# Update App Platform to use new version
# Edit .do/app-from-registry.yaml, change tag to v1.1.0
doctl apps update APP_ID --spec .do/app-from-registry.yaml

# Or via dashboard: Apps → Settings → Change image tag
```

### Rollback

```bash
# Revert to previous version
doctl apps update APP_ID --spec .do/app-from-registry.yaml
# (after changing tag back to previous version)
```

---

## Testing Locally

Before pushing to registry, test locally:

```bash
# Build
docker build -t ufe-test -f Dockerfile.adk-web .

# Run locally
docker run -p 8080:8080 --env-file .env ufe-test

# Test
curl http://localhost:8080/healthz

# Open browser
open http://localhost:8080
```

---

## Registry Management

### View Images

```bash
# List all repositories
doctl registry repository list-v2

# List tags for a repository
doctl registry repository list-tags ufe-research-writer-web

# Get manifest
doctl registry repository get-manifest ufe-research-writer-web latest
```

### Delete Images

```bash
# Delete specific tag
doctl registry repository delete-tag ufe-research-writer-web v1.0.0

# Delete entire repository
doctl registry repository delete ufe-research-writer-web
```

### Garbage Collection

```bash
# Run garbage collection to free up space
doctl registry garbage-collection start ufe-research-writer

# Check garbage collection status
doctl registry garbage-collection list
```

---

## CI/CD Integration

### GitHub Actions Example

Create `.github/workflows/deploy.yml`:

```yaml
name: Build and Deploy

on:
  push:
    branches: [main]

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Install doctl
        uses: digitalocean/action-doctl@v2
        with:
          token: ${{ secrets.DIGITALOCEAN_ACCESS_TOKEN }}

      - name: Build image
        run: docker build -t ufe-research-writer-web -f Dockerfile.adk-web .

      - name: Login to DO Container Registry
        run: doctl registry login

      - name: Tag and push
        run: |
          docker tag ufe-research-writer-web \
            registry.digitalocean.com/adk-test/ufe-research-writer-web:latest
          docker push registry.digitalocean.com/adk-test/ufe-research-writer-web:latest

      - name: Deploy to App Platform
        run: |
          doctl apps create-deployment ${{ secrets.APP_ID }}
```

---

## Troubleshooting

### Authentication Issues

```bash
# Re-login to registry
doctl registry login

# Check authentication
docker info | grep Registry
```

### Push Fails

```bash
# Check registry exists
doctl registry get adk-test

# Check image name format
# Must be: registry.digitalocean.com/REGISTRY_NAME/IMAGE_NAME:TAG
```

### Image Too Large

```bash
# Check image size
docker images | grep ufe-research-writer

# Optimize Dockerfile (use .dockerignore)
# Remove unnecessary files
```

### Out of Storage

```bash
# Check storage usage
doctl registry get adk-test

# Run garbage collection
doctl registry garbage-collection start adk-test

# Or upgrade plan
doctl registry update adk-test --subscription-tier professional
```

---

## Best Practices

1. **Tag versions** - Always tag with version numbers, not just `latest`
2. **Use .dockerignore** - Keep images small
3. **Multi-stage builds** - Reduce final image size
4. **Security scanning** - Use `doctl registry repository scan`
5. **Automate** - Set up CI/CD for automatic builds

---

## Cost Summary

| Service | Cost | What's Included |
|---------|------|-----------------|
| **Container Registry Basic** | $5/mo | 500 MB storage |
| **Container Registry Pro** | $20/mo | 10 GB storage |
| **App Platform (Professional XS)** | $12/mo | 1GB RAM, hosting |
| **Total (Registry + App)** | **$17/mo** | Complete solution |

---

## Quick Reference

```bash
# Build and push
./build-and-push-do.sh

# Deploy from registry
./deploy-from-registry.sh

# List images
doctl registry repository list-v2

# Update app
doctl apps update APP_ID --spec .do/app-from-registry.yaml

# View logs
doctl apps logs APP_ID
```

---

For more details, see [DigitalOcean Container Registry Docs](https://docs.digitalocean.com/products/container-registry/)
