#!/bin/bash

# Cloud Run Deployment Script for UFE Research Writer (Full-Stack with Custom UI)
# Usage: ./deploy-fullstack.sh [PROJECT_ID] [REGION]

set -e

# Configuration
PROJECT_ID="${1:-your-gcp-project-id}"
REGION="${2:-us-central1}"
SERVICE_NAME="ufe-research-writer-fullstack"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}UFE Research Writer - Full-Stack Deployment${NC}"
echo -e "${GREEN}Custom SvelteKit UI + FastAPI Backend${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI is not installed${NC}"
    echo "Install from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}Warning: .env file not found${NC}"
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo -e "${YELLOW}Please edit .env with your API keys before deploying${NC}"
    exit 1
fi

# Validate project ID
if [ "$PROJECT_ID" = "your-gcp-project-id" ]; then
    echo -e "${RED}Error: Please provide a valid GCP project ID${NC}"
    echo "Usage: ./deploy-fullstack.sh YOUR_PROJECT_ID [REGION]"
    exit 1
fi

echo -e "${YELLOW}Project ID: ${PROJECT_ID}${NC}"
echo -e "${YELLOW}Region: ${REGION}${NC}"
echo -e "${YELLOW}Service Name: ${SERVICE_NAME}${NC}"
echo -e "${YELLOW}Deployment: Full-Stack (SvelteKit + FastAPI)${NC}"
echo ""

# Set GCP project
echo -e "${GREEN}Setting GCP project...${NC}"
gcloud config set project ${PROJECT_ID}

# Enable required APIs
echo -e "${GREEN}Enabling required GCP APIs...${NC}"
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    containerregistry.googleapis.com

# Build the container image
echo -e "${GREEN}Building full-stack container image...${NC}"
echo -e "${YELLOW}This will build both SvelteKit frontend and Python backend${NC}"
gcloud builds submit --tag ${IMAGE_NAME} -f Dockerfile.fullstack

# Load environment variables for deployment
echo -e "${GREEN}Preparing environment variables...${NC}"
source .env

# Deploy to Cloud Run
echo -e "${GREEN}Deploying full-stack app to Cloud Run...${NC}"
gcloud run deploy ${SERVICE_NAME} \
    --image ${IMAGE_NAME} \
    --platform managed \
    --region ${REGION} \
    --allow-unauthenticated \
    --set-env-vars "GOOGLE_API_KEY=${GOOGLE_API_KEY}" \
    --set-env-vars "TAVILY_API_KEY=${TAVILY_API_KEY}" \
    --set-env-vars "PROJECT_ID=${PROJECT_ID}" \
    --set-env-vars "GDR_APP_ID=${GDR_APP_ID}" \
    --set-env-vars "GDR_LOCATION=${GDR_LOCATION:-global}" \
    --set-env-vars "GDR_COLLECTION=${GDR_COLLECTION}" \
    --set-env-vars "GDR_ASSISTANT=${GDR_ASSISTANT}" \
    --set-env-vars "SPACES_ACCESS_KEY=${SPACES_ACCESS_KEY}" \
    --set-env-vars "SPACES_SECRET_KEY=${SPACES_SECRET_KEY}" \
    --set-env-vars "SPACES_REGION=${SPACES_REGION:-sgp1}" \
    --set-env-vars "SPACES_BUCKET=${SPACES_BUCKET:-finance-bucket}" \
    --set-env-vars "DATABASE_PATH=/app/data/app.db" \
    --memory 4Gi \
    --cpu 2 \
    --timeout 3600 \
    --max-instances 10 \
    --min-instances 0

# Get the service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
    --platform managed \
    --region ${REGION} \
    --format 'value(status.url)')

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Full-Stack Deployment Successful!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${GREEN}Application URL: ${SERVICE_URL}${NC}"
echo ""
echo -e "${YELLOW}Features:${NC}"
echo "  ✅ Custom SvelteKit UI (sessions, files, artifacts)"
echo "  ✅ FastAPI backend with ADK agent integration"
echo "  ✅ Session management with SQLite database"
echo "  ✅ File uploads to DigitalOcean Spaces"
echo "  ✅ Research report generation"
echo "  ✅ Multi-language support (Mongolian/English)"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "  1. Open ${SERVICE_URL} in your browser"
echo "  2. Create a new research session"
echo "  3. Upload reference materials (PDF, Excel, CSV)"
echo "  4. Ask the agent to research and generate reports"
echo ""
