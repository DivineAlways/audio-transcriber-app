#!/bin/bash

# Audio Transcriber - Cloud Run Deployment Script
# Usage: ./deploy.sh [PROJECT_ID]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SERVICE_NAME="audio-transcriber"
REGION="us-central1"
MEMORY="512Mi"
CPU="1"

# Get project ID from argument or prompt
if [ -z "$1" ]; then
    echo -e "${YELLOW}Please provide your Google Cloud Project ID:${NC}"
    read -p "Project ID: " PROJECT_ID
else
    PROJECT_ID=$1
fi

if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}Error: Project ID is required${NC}"
    exit 1
fi

echo -e "${GREEN}Deploying Audio Transcriber to Google Cloud Run...${NC}"
echo -e "${YELLOW}Project ID: $PROJECT_ID${NC}"
echo -e "${YELLOW}Service Name: $SERVICE_NAME${NC}"
echo -e "${YELLOW}Region: $REGION${NC}"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    # Try to find gcloud in common locations
    if [ -f "$HOME/google-cloud-sdk/bin/gcloud" ]; then
        echo -e "${YELLOW}Found Google Cloud SDK, adding to PATH...${NC}"
        export PATH="$HOME/google-cloud-sdk/bin:$PATH"
    else
        echo -e "${RED}Error: Google Cloud SDK is not installed${NC}"
        echo "Please install it from: https://cloud.google.com/sdk/docs/install"
        echo "Or if already installed, add it to your PATH:"
        echo "export PATH=\"\$HOME/google-cloud-sdk/bin:\$PATH\""
        exit 1
    fi
fi

# Set the project
echo -e "${YELLOW}Setting project...${NC}"
gcloud config set project $PROJECT_ID

# Enable required APIs
echo -e "${YELLOW}Enabling required APIs...${NC}"
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com

# Deploy to Cloud Run
echo -e "${YELLOW}Deploying to Cloud Run...${NC}"
gcloud run deploy $SERVICE_NAME \
    --source . \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --port 8080 \
    --memory $MEMORY \
    --cpu $CPU \
    --max-instances 10 \
    --timeout 300

# Get the service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --platform managed --region $REGION --format 'value(status.url)')

echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
echo -e "${GREEN}🌐 Service URL: $SERVICE_URL${NC}"
echo -e "${GREEN}🏥 Health Check: $SERVICE_URL/health${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Update your Assembly AI API key in the deployed service"
echo "2. Update your n8n webhook URL in the deployed service"
echo "3. Test the service by uploading an audio file"
echo ""
echo -e "${YELLOW}To view logs:${NC}"
echo "gcloud logs tail --follow --resource=cloud_run_revision/service_name=$SERVICE_NAME --region=$REGION"
