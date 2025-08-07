#!/bin/bash

# Local testing script for Audio Transcriber
# Usage: ./test-local.sh

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

IMAGE_NAME="audio-transcriber"
CONTAINER_NAME="audio-transcriber-test"
PORT=8080

echo -e "${GREEN}Building and testing Audio Transcriber locally...${NC}"

# Stop and remove existing container if it exists
if docker ps -a | grep -q $CONTAINER_NAME; then
    echo -e "${YELLOW}Stopping existing container...${NC}"
    docker stop $CONTAINER_NAME 2>/dev/null || true
    docker rm $CONTAINER_NAME 2>/dev/null || true
fi

# Build the Docker image
echo -e "${YELLOW}Building Docker image...${NC}"
docker build -t $IMAGE_NAME .

# Run the container
echo -e "${YELLOW}Starting container...${NC}"
docker run -d --name $CONTAINER_NAME -p $PORT:8080 $IMAGE_NAME

# Wait a moment for the container to start
sleep 3

# Check if container is running
if docker ps | grep -q $CONTAINER_NAME; then
    echo -e "${GREEN}✅ Container is running successfully!${NC}"
    echo -e "${GREEN}🌐 Local URL: http://localhost:$PORT${NC}"
    echo -e "${GREEN}🏥 Health Check: http://localhost:$PORT/health${NC}"
    echo ""
    echo -e "${YELLOW}To stop the container:${NC}"
    echo "docker stop $CONTAINER_NAME"
    echo ""
    echo -e "${YELLOW}To view logs:${NC}"
    echo "docker logs -f $CONTAINER_NAME"
else
    echo -e "${RED}❌ Container failed to start${NC}"
    echo "Check logs with: docker logs $CONTAINER_NAME"
    exit 1
fi
