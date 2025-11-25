#!/bin/bash

# DigitalOcean App Platform Deployment Script
# Usage: ./deploy-digitalocean.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}UFE Research Writer - DigitalOcean Deployment${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if doctl is installed
if ! command -v doctl &> /dev/null; then
    echo -e "${RED}Error: doctl CLI is not installed${NC}"
    echo ""
    echo "Install doctl:"
    echo "  macOS: brew install doctl"
    echo "  Linux: snap install doctl"
    echo "  Or visit: https://docs.digitalocean.com/reference/doctl/how-to/install/"
    echo ""
    exit 1
fi

# Check if user is authenticated
if ! doctl auth list &> /dev/null; then
    echo -e "${YELLOW}You need to authenticate with DigitalOcean${NC}"
    echo "Run: doctl auth init"
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}Warning: .env file not found${NC}"
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo -e "${YELLOW}Please edit .env with your API keys${NC}"
    exit 1
fi

echo -e "${BLUE}Deployment Options:${NC}"
echo ""
echo "1. ${GREEN}App Platform${NC} (Recommended - Easy, managed, auto-scaling)"
echo "2. ${BLUE}Droplet${NC} (Manual setup, full control)"
echo ""
read -p "Select deployment type (1 or 2): " deployment_type

if [ "$deployment_type" = "1" ]; then
    echo ""
    echo -e "${GREEN}Deploying to DigitalOcean App Platform...${NC}"
    echo ""

    # Load environment variables
    source .env

    # Create app spec from template
    APP_SPEC=".do/app.yaml"

    if [ ! -f "$APP_SPEC" ]; then
        echo -e "${RED}Error: App spec not found at $APP_SPEC${NC}"
        exit 1
    fi

    echo -e "${YELLOW}Please update .do/app.yaml with your GitHub repo before continuing${NC}"
    echo "Press Enter when ready, or Ctrl+C to cancel..."
    read

    # Create the app
    echo -e "${GREEN}Creating App Platform app...${NC}"
    doctl apps create --spec "$APP_SPEC"

    # Get the app ID
    APP_ID=$(doctl apps list --format ID --no-header | head -n 1)

    echo ""
    echo -e "${GREEN}Setting environment variables (secrets)...${NC}"

    # Note: Secrets must be set via UI or API after app creation
    echo -e "${YELLOW}IMPORTANT: You need to set the following secrets in the DigitalOcean dashboard:${NC}"
    echo "  - GOOGLE_API_KEY"
    echo "  - TAVILY_API_KEY"
    echo ""
    echo "Go to: https://cloud.digitalocean.com/apps/$APP_ID/settings"
    echo ""

    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}Deployment Initiated!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "App ID: $APP_ID"
    echo "View deployment: https://cloud.digitalocean.com/apps/$APP_ID"
    echo ""
    echo -e "${YELLOW}Next steps:${NC}"
    echo "1. Set environment secrets in the dashboard"
    echo "2. Wait for deployment to complete (~5 minutes)"
    echo "3. Your app will be available at the provided URL"

elif [ "$deployment_type" = "2" ]; then
    echo ""
    echo -e "${BLUE}Droplet deployment requires manual setup.${NC}"
    echo "See DEPLOYMENT_DIGITALOCEAN.md for instructions."
    exit 0
else
    echo -e "${RED}Invalid option${NC}"
    exit 1
fi
