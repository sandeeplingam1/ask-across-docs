#!/bin/bash

# Audit App - Stop Script
# This script stops both backend and frontend development servers

set -e

echo "Stopping Audit App servers..."

# Function to stop process by PID
stop_process() {
    local pid=$1
    local name=$2
    
    if [ ! -z "$pid" ] && ps -p $pid > /dev/null 2>&1; then
        echo "Stopping $name (PID: $pid)..."
        kill $pid 2>/dev/null || true
        sleep 1
        
        # Force kill if still running
        if ps -p $pid > /dev/null 2>&1; then
            echo "Force stopping $name..."
            kill -9 $pid 2>/dev/null || true
        fi
        echo "$name stopped"
    else
        echo "$name not running (PID: $pid)"
    fi
}

# Stop backend
if [ -f .backend.pid ]; then
    BACKEND_PID=$(cat .backend.pid)
    stop_process $BACKEND_PID "Backend"
    rm .backend.pid
fi

# Stop frontend
if [ -f .frontend.pid ]; then
    FRONTEND_PID=$(cat .frontend.pid)
    stop_process $FRONTEND_PID "Frontend"
    rm .frontend.pid
fi

# Also kill any processes on the ports as backup
echo "Checking for remaining processes on ports..."
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
lsof -ti:5173 | xargs kill -9 2>/dev/null || true

echo "All servers stopped"
