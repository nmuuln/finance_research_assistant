#!/bin/bash

# Deploy to DigitalOcean App Platform from Container Registry
# Usage: ./deploy-from-registry.sh

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deploy from Container Registry${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if doctl is installed
if ! command -v doctl &> /dev/null; then
    echo -e "${RED}Error: doctl CLI is not installed${NC}"
    exit 1
fi

# Check if app spec exists
if [ ! -f .do/app-from-registry.yaml ]; then
    echo -e "${RED}Error: .do/app-from-registry.yaml not found${NC}"
    exit 1
fi

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}Warning: .env file not found${NC}"
    cp .env.example .env
    echo "Please edit .env with your API keys"
    exit 1
fi

echo -e "${YELLOW}This will create a new app on DigitalOcean App Platform${NC}"
echo ""
read -p "Continue? (y/n): " confirm

if [ "$confirm" != "y" ]; then
    echo "Cancelled"
    exit 0
fi

# Load environment variables
source .env

# Create the app
echo ""
echo -e "${GREEN}Creating App Platform app from registry image...${NC}"
APP_OUTPUT=$(doctl apps create --spec .do/app-from-registry.yaml --format ID --no-header)
APP_ID=$(echo "$APP_OUTPUT" | head -n 1)

echo ""
echo -e "${GREEN}App created with ID: $APP_ID${NC}"
echo ""

# Wait a moment for app to initialize
sleep 3

# Set secrets (note: this requires the app to be created first)
echo -e "${GREEN}Setting environment secrets...${NC}"

# Note: doctl doesn't support setting encrypted env vars via CLI easily
# User needs to set them via dashboard
echo ""
echo -e "${YELLOW}IMPORTANT: Set the following secrets in the DigitalOcean dashboard:${NC}"
echo ""
echo "  1. Go to: https://cloud.digitalocean.com/apps/$APP_ID/settings"
echo "  2. Click 'Environment Variables'"
echo "  3. Add encrypted variables:"
echo "     - GOOGLE_API_KEY = ${GOOGLE_API_KEY:0:10}..."
echo "     - TAVILY_API_KEY = ${TAVILY_API_KEY:0:10}..."
echo ""

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Initiated!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "App ID: $APP_ID"
echo "Dashboard: https://cloud.digitalocean.com/apps/$APP_ID"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Set environment secrets in dashboard (see above)"
echo "2. Wait for deployment (~3-5 minutes)"
echo "3. Get app URL: doctl apps get $APP_ID --format DefaultIngress"
echo ""
