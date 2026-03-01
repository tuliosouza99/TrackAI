#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}Starting TrackAI...${NC}\n"

# Function to check if a port is available
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 1  # Port is in use
    else
        return 0  # Port is available
    fi
}

# Find an available port starting from 8000
find_available_port() {
    local port=8000
    while true; do
        if check_port $port; then
            echo $port
            return 0
        fi
        port=$((port + 1))
        if [ $port -gt 8100 ]; then
            echo -e "${RED}No available ports found between 8000-8100${NC}" >&2
            exit 1
        fi
    done
}

# Get available port
PORT=$(find_available_port)
echo -e "${GREEN}Found available port: ${YELLOW}$PORT${NC}\n"

# Function to cleanup background processes on exit
cleanup() {
    echo -e "\n${RED}Shutting down server...${NC}"
    kill $BACKEND_PID 2>/dev/null
    exit 0
}

# Set up trap to catch Ctrl+C and other termination signals
trap cleanup SIGINT SIGTERM

# Build frontend
echo -e "${GREEN}Building frontend...${NC}"
(cd frontend && npm run build)

if [ $? -ne 0 ]; then
    echo -e "${RED}Frontend build failed!${NC}"
    exit 1
fi

echo -e "${GREEN}Frontend built successfully!${NC}\n"

# Start backend (which will serve the frontend)
echo -e "${GREEN}Starting backend server on port $PORT...${NC}"
(cd backend && uv run uvicorn trackai.api.main:app --reload --port $PORT) &
BACKEND_PID=$!

echo -e "\n${BLUE}TrackAI is running!${NC}"
echo -e "Access the app at: ${YELLOW}http://localhost:$PORT${NC}"
echo -e "\n${RED}Press Ctrl+C to stop the server${NC}\n"

# Wait for the backend process
wait $BACKEND_PID
