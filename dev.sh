#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}Starting TrackAI in development mode...${NC}\n"

# Function to check if a port is available
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 1  # Port is in use
    else
        return 0  # Port is available
    fi
}

# Find an available port starting from a given port
find_available_port() {
    local start_port=$1
    local port=$start_port
    while true; do
        if check_port $port; then
            echo $port
            return 0
        fi
        port=$((port + 1))
        if [ $port -gt $((start_port + 100)) ]; then
            echo -e "${RED}No available ports found between $start_port-$((start_port + 100))${NC}" >&2
            exit 1
        fi
    done
}

# Get available ports
BACKEND_PORT=$(find_available_port 8000)
FRONTEND_PORT=$(find_available_port 5173)

echo -e "${GREEN}Found available backend port: ${YELLOW}$BACKEND_PORT${NC}"
echo -e "${GREEN}Found available frontend port: ${YELLOW}$FRONTEND_PORT${NC}\n"

# Function to cleanup background processes on exit
cleanup() {
    echo -e "\n${RED}Shutting down servers...${NC}"
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    exit 0
}

# Set up trap to catch Ctrl+C and other termination signals
trap cleanup SIGINT SIGTERM

# Start backend
echo -e "${GREEN}Starting backend server on port $BACKEND_PORT...${NC}"
(cd backend && uv run uvicorn trackai.api.main:app --reload --port $BACKEND_PORT) &
BACKEND_PID=$!

# Give backend a moment to start
sleep 2

# Start frontend
echo -e "${GREEN}Starting frontend dev server on port $FRONTEND_PORT...${NC}"
(cd frontend && VITE_BACKEND_URL="http://localhost:$BACKEND_PORT" npm run dev -- --port $FRONTEND_PORT) &
FRONTEND_PID=$!

echo -e "\n${BLUE}Both servers are running!${NC}"
echo -e "Backend API: ${YELLOW}http://localhost:$BACKEND_PORT${NC}"
echo -e "Frontend: ${YELLOW}http://localhost:$FRONTEND_PORT${NC}"
echo -e "\n${RED}Press Ctrl+C to stop both servers${NC}\n"

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID
