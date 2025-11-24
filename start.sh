#!/bin/bash

# Audit App - Startup Script
# This script starts both backend and frontend development servers

set -e

echo "=========================================="
echo "Audit App - Starting Development Servers"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if we're in the correct directory
if [ ! -d "backend" ] || [ ! -d "frontend" ]; then
    echo -e "${RED}Error: Must run this script from the Audit App root directory${NC}"
    echo "Current directory: $(pwd)"
    exit 1
fi

# Function to check if port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        echo -e "${YELLOW}Warning: Port $port is already in use${NC}"
        return 1
    fi
    return 0
}

# Check if backend virtual environment exists
if [ ! -d "backend/venv" ]; then
    echo -e "${RED}Error: Backend virtual environment not found${NC}"
    echo "Please run setup first:"
    echo "  cd backend"
    echo "  ./setup.sh"
    exit 1
fi

# Check if backend .env exists
if [ ! -f "backend/.env" ]; then
    echo -e "${RED}Error: Backend .env file not found${NC}"
    echo "Please copy .env.example to .env and configure it:"
    echo "  cd backend"
    echo "  cp .env.example .env"
    echo "  # Edit .env with your Azure OpenAI credentials"
    exit 1
fi

# Check if frontend node_modules exists
if [ ! -d "frontend/node_modules" ]; then
    echo -e "${YELLOW}Frontend dependencies not installed. Installing now...${NC}"
    cd frontend
    npm install
    cd ..
fi

# Check ports
echo "Checking ports..."
check_port 8000 || { echo "Please stop the process using port 8000 first"; exit 1; }
check_port 5173 || { echo "Please stop the process using port 5173 first"; exit 1; }
echo -e "${GREEN}Ports 8000 and 5173 are available${NC}"
echo ""

# Start backend
echo -e "${GREEN}Starting Backend Server...${NC}"
echo "Location: http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"
echo ""

cd backend
source venv/bin/activate

# Start backend in background
python -m uvicorn app.main:app --reload --port 8000 > ../backend.log 2>&1 &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"

# Wait for backend to start
echo "Waiting for backend to initialize..."
sleep 3

# Check if backend is running
if ! ps -p $BACKEND_PID > /dev/null; then
    echo -e "${RED}Failed to start backend. Check backend.log for errors${NC}"
    cat ../backend.log
    exit 1
fi

# Check if backend is responding
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo -e "${YELLOW}Backend started but not responding yet. Check backend.log${NC}"
else
    echo -e "${GREEN}Backend is running and healthy!${NC}"
fi

cd ..

# Start frontend
echo ""
echo -e "${GREEN}Starting Frontend Server...${NC}"
echo "Location: http://localhost:5173"
echo ""

cd frontend

# Start frontend in background
npm run dev > ../frontend.log 2>&1 &
FRONTEND_PID=$!
echo "Frontend PID: $FRONTEND_PID"

cd ..

# Save PIDs for cleanup
echo $BACKEND_PID > .backend.pid
echo $FRONTEND_PID > .frontend.pid

echo ""
echo "=========================================="
echo -e "${GREEN}Servers Started Successfully!${NC}"
echo "=========================================="
echo ""
echo "Access the application:"
echo "  Frontend: http://localhost:5173"
echo "  Backend:  http://localhost:8000"
echo "  API Docs: http://localhost:8000/docs"
echo ""
echo "Logs:"
echo "  Backend:  tail -f backend.log"
echo "  Frontend: tail -f frontend.log"
echo ""
echo "To stop the servers:"
echo "  ./stop.sh"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop this script (servers will keep running)${NC}"
echo "Or run ./stop.sh to stop all servers"
echo ""

# Keep script running to show logs
tail -f backend.log frontend.log
