#!/bin/bash

# Medical Education Application Launcher
# Created by Claude AI Assistant

# Color codes for terminal output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Medical Education Application Launcher ===${NC}"

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
echo -e "${GREEN}Changing to application directory:${NC} $SCRIPT_DIR"
cd "$SCRIPT_DIR"

# Check if virtual environment exists and activate it
if [ -d "venv" ]; then
    echo -e "${GREEN}Activating virtual environment...${NC}"
    source venv/bin/activate
elif [ -d ".venv" ]; then
    echo -e "${GREEN}Activating virtual environment...${NC}"
    source .venv/bin/activate
else
    echo -e "${BLUE}No virtual environment found. Using system Python.${NC}"
fi

# Make the script executable if it's not already
chmod +x "$0"

# Check if uvicorn is installed
if ! command -v uvicorn &> /dev/null; then
    echo -e "${RED}uvicorn is not installed. Installing now...${NC}"
    pip install uvicorn
fi

# Start the server
echo -e "${GREEN}Starting the server...${NC}"
echo -e "${BLUE}The server will be available at:${NC} http://localhost:8000"

# Start in background to allow the script to continue
uvicorn app.main:app --reload &
SERVER_PID=$!

# Wait for the server to start
echo -e "${GREEN}Waiting for server to start...${NC}"
sleep 3

# Open the browser
echo -e "${GREEN}Opening application in your default browser...${NC}"
open http://localhost:8000

# Instructions for terminating
echo -e "\n${BLUE}=== Server is running ===${NC}"
echo -e "Press ${RED}Ctrl+C${NC} to stop the server"
echo -e "Or run: ${RED}kill $SERVER_PID${NC}"

# Keep the script running to keep output visible and allow Ctrl+C to stop
trap "kill $SERVER_PID; echo -e '${RED}Server stopped.${NC}'; exit" INT
wait $SERVER_PID 