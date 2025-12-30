#!/bin/bash

# Build and Push Full-Stack App to DigitalOcean Container Registry
# Usage: ./build-and-push-fullstack-do.sh [registry-name] [version]

set -e

# Configuration
REGISTRY_NAME="${1:-adk-test}"
IMAGE_NAME="ufe-research-writer-fullstack"
VERSION="${2:-latest}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Build & Push Full-Stack to DO Registry${NC}"
echo -e "${GREEN}Custom UI + Backend${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}Error: Docker is not running${NC}"
    echo "Please start Docker Desktop and try again"
    exit 1
fi

# Check if doctl is installed
if ! command -v doctl &> /dev/null; then
    echo -e "${RED}Error: doctl CLI is not installed${NC}"
    echo ""
    echo "Install doctl:"
    echo "  macOS: brew install doctl"
    echo "  Linux: snap install doctl"
    echo ""
    exit 1
fi

# Check authentication
if ! doctl auth list &> /dev/null; then
    echo -e "${YELLOW}You need to authenticate with DigitalOcean${NC}"
    echo "Run: doctl auth init"
    exit 1
fi

echo -e "${BLUE}Configuration:${NC}"
echo "  Registry: ${REGISTRY_NAME}"
echo "  Image: ${IMAGE_NAME}"
echo "  Version: ${VERSION}"
echo "  Build: Multi-stage (SvelteKit + FastAPI)"
echo ""

# Check if registry exists, create if not
echo -e "${GREEN}Checking container registry...${NC}"
if ! doctl registry get "$REGISTRY_NAME" &> /dev/null; then
    echo -e "${YELLOW}Registry '$REGISTRY_NAME' not found. Creating...${NC}"

    read -p "Select region (nyc3/sfo3/ams3/sgp1/fra1): " region
    region=${region:-sgp1}

    doctl registry create "$REGISTRY_NAME" --region "$region" --subscription-tier basic
    echo -e "${GREEN}Registry created!${NC}"
else
    echo -e "${GREEN}Registry '$REGISTRY_NAME' found${NC}"
fi

# Login to registry
echo ""
echo -e "${GREEN}Logging into DigitalOcean Container Registry...${NC}"
doctl registry login

# Build the Docker image (multi-stage build)
echo ""
echo -e "${GREEN}Building full-stack Docker image for linux/amd64...${NC}"
echo -e "${YELLOW}This will build the SvelteKit frontend and Python backend${NC}"
docker build --platform linux/amd64 -t "${IMAGE_NAME}:${VERSION}" -f Dockerfile.fullstack .

# Tag the image for the registry
REGISTRY_URL="registry.digitalocean.com/${REGISTRY_NAME}"
FULL_IMAGE_NAME="${REGISTRY_URL}/${IMAGE_NAME}:${VERSION}"

echo ""
echo -e "${GREEN}Tagging image...${NC}"
docker tag "${IMAGE_NAME}:${VERSION}" "$FULL_IMAGE_NAME"

# Also tag as latest if version is not latest
if [ "$VERSION" != "latest" ]; then
    docker tag "${IMAGE_NAME}:${VERSION}" "${REGISTRY_URL}/${IMAGE_NAME}:latest"
fi

# Push to registry
echo ""
echo -e "${GREEN}Pushing to DigitalOcean Container Registry...${NC}"

# Push with retry logic (up to 3 attempts)
MAX_RETRIES=3
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    echo "Attempt $((RETRY_COUNT + 1)) of $MAX_RETRIES..."

    if docker push "$FULL_IMAGE_NAME"; then
        echo -e "${GREEN}Successfully pushed $FULL_IMAGE_NAME${NC}"
        break
    else
        RETRY_COUNT=$((RETRY_COUNT + 1))
        if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
            echo -e "${YELLOW}Push failed. Retrying in 5 seconds...${NC}"
            sleep 5
        else
            echo -e "${RED}Failed to push after $MAX_RETRIES attempts${NC}"
            exit 1
        fi
    fi
done

if [ "$VERSION" != "latest" ]; then
    RETRY_COUNT=0
    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        echo "Pushing latest tag - Attempt $((RETRY_COUNT + 1)) of $MAX_RETRIES..."

        if docker push "${REGISTRY_URL}/${IMAGE_NAME}:latest"; then
            echo -e "${GREEN}Successfully pushed latest tag${NC}"
            break
        else
            RETRY_COUNT=$((RETRY_COUNT + 1))
            if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
                echo -e "${YELLOW}Push failed. Retrying in 5 seconds...${NC}"
                sleep 5
            else
                echo -e "${RED}Failed to push latest tag after $MAX_RETRIES attempts${NC}"
                exit 1
            fi
        fi
    done
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Build & Push Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${GREEN}Image pushed to:${NC}"
echo "  $FULL_IMAGE_NAME"
if [ "$VERSION" != "latest" ]; then
    echo "  ${REGISTRY_URL}/${IMAGE_NAME}:latest"
fi
echo ""
echo -e "${YELLOW}What's included:${NC}"
echo "  ✅ Custom SvelteKit UI (sessions, files, artifacts)"
echo "  ✅ FastAPI backend with ADK agent"
echo "  ✅ SQLite database"
echo "  ✅ DigitalOcean Spaces integration"
echo "  ✅ Multi-language support"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo ""
echo "1. Deploy to DigitalOcean App Platform:"
echo "   Create app.yaml and run:"
echo "   doctl apps create --spec .do/app-fullstack.yaml"
echo ""
echo "2. Or deploy to a Droplet:"
echo "   ssh root@YOUR_DROPLET_IP"
echo "   doctl registry login"
echo "   docker run -d -p 80:8080 \\"
echo "     --env-file .env \\"
echo "     -v /data/db:/app/data \\"
echo "     $FULL_IMAGE_NAME"
echo ""
echo "3. View your images:"
echo "   doctl registry repository list-v2"
echo ""
