#!/bin/bash

# Cloud Run Deployment Script for UFE Research Writer Agent
# Usage: ./deploy.sh [PROJECT_ID] [REGION]

set -e

# Configuration
PROJECT_ID="${1:-your-gcp-project-id}"
REGION="${2:-us-central1}"
SERVICE_NAME="ufe-research-writer"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}UFE Research Writer - Cloud Run Deployment${NC}"
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
    echo "Usage: ./deploy.sh YOUR_PROJECT_ID [REGION]"
    exit 1
fi

echo -e "${YELLOW}Project ID: ${PROJECT_ID}${NC}"
echo -e "${YELLOW}Region: ${REGION}${NC}"
echo -e "${YELLOW}Service Name: ${SERVICE_NAME}${NC}"
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
echo -e "${GREEN}Building container image...${NC}"
gcloud builds submit --tag ${IMAGE_NAME}

# Load environment variables for deployment
echo -e "${GREEN}Preparing environment variables...${NC}"
source .env

# Deploy to Cloud Run
echo -e "${GREEN}Deploying to Cloud Run...${NC}"
gcloud run deploy ${SERVICE_NAME} \
    --image ${IMAGE_NAME} \
    --platform managed \
    --region ${REGION} \
    --allow-unauthenticated \
    --set-env-vars "GOOGLE_API_KEY=${GOOGLE_API_KEY}" \
    --set-env-vars "TAVILY_API_KEY=${TAVILY_API_KEY}" \
    --set-env-vars "PROJECT_ID=${PROJECT_ID}" \
    --set-env-vars "LANGUAGE=${LANGUAGE:-mn}" \
    --memory 2Gi \
    --cpu 2 \
    --timeout 900 \
    --max-instances 10 \
    --min-instances 0

# Get the service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
    --platform managed \
    --region ${REGION} \
    --format 'value(status.url)')

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Successful!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${GREEN}Service URL: ${SERVICE_URL}${NC}"
echo -e "${GREEN}Health Check: ${SERVICE_URL}/healthz${NC}"
echo ""
echo -e "${YELLOW}Test your deployment:${NC}"
echo "curl ${SERVICE_URL}/healthz"
echo ""
echo -e "${YELLOW}Create a chat session:${NC}"
echo "curl -X POST ${SERVICE_URL}/sessions -H 'Content-Type: application/json' -d '{\"user_id\": \"test-user\"}'"
