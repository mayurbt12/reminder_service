#!/bin/bash
# Unified startup script for Reminder Service
# Starts all services via main.py

# Change to script directory
cd "$(dirname "$0")"

# Activate virtual environment
if [ -f .venv/bin/activate ]; then
    source .venv/bin/activate
else
    echo "Warning: Virtual environment not found at .venv/"
    echo "Please run: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "========================================="
echo "  Reminder Service - Unified Startup"
echo "========================================="
echo ""

# Create directories if they don't exist
mkdir -p .pids logs

# Check if service is already running
if [ -f .pids/main.pid ]; then
    MAIN_PID=$(cat .pids/main.pid)
    if ps -p $MAIN_PID > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠ Reminder Service already running (PID: $MAIN_PID)${NC}"
        echo ""
        echo "Available Services:"
        echo "  • REST API: http://127.0.0.1:8005"
        echo "  • API Docs: http://127.0.0.1:8005/docs"
        echo "  • MCP Server (SSE): http://127.0.0.1:8006/sse"
        echo "  • Background Worker: Active"
        echo ""
        echo "Commands:"
        echo "  • Stop services: ./stop.sh"
        echo "  • View logs: tail -f logs/main.log"
        exit 0
    else
        echo "Cleaning up stale PID file..."
        rm -f .pids/main.pid
    fi
fi

# Start unified service via main.py
echo "Starting Reminder Service (all components)..."
nohup python3 main.py > logs/main.log 2>&1 &
MAIN_PID=$!
echo $MAIN_PID > .pids/main.pid
echo "  ✓ Reminder Service started (PID: $MAIN_PID)"
echo ""

# Wait a moment for services to fully initialize
sleep 3

# Verify service is running
echo "Verifying services..."
ERRORS=0

if [ -f .pids/main.pid ]; then
    MAIN_PID=$(cat .pids/main.pid)
    if ps -p $MAIN_PID > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} Main process is running (PID: $MAIN_PID)"

        # Test API health endpoint
        if command -v curl &> /dev/null; then
            sleep 2  # Give services a moment to fully start
            if curl -s http://127.0.0.1:8005/health > /dev/null 2>&1; then
                echo -e "  ${GREEN}✓${NC} API server responding"
            else
                echo -e "  ${YELLOW}⚠${NC} API not responding yet (may still be starting)"
            fi

            # Test MCP SSE endpoint
            if curl -s http://127.0.0.1:8006/sse -m 2 > /dev/null 2>&1; then
                echo -e "  ${GREEN}✓${NC} MCP server responding"
            else
                echo -e "  ${YELLOW}⚠${NC} MCP not responding yet (may still be starting)"
            fi
        fi
    else
        echo -e "  ${RED}✗${NC} Service failed to start (check logs/main.log)"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo -e "  ${RED}✗${NC} PID file not found"
    ERRORS=$((ERRORS + 1))
fi

echo ""
echo ""
echo "========================================="
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✓ Reminder Service started successfully!${NC}"
    echo ""
    echo "Available Services:"
    echo "  • REST API: http://127.0.0.1:8005"
    echo "  • API Docs: http://127.0.0.1:8005/docs"
    echo "  • MCP Server (SSE): http://127.0.0.1:8006/sse"
    echo "  • Background Worker: Outgoing call automation"
    echo ""
    echo "Transport:"
    echo "  • REST API: HTTP (frontend access)"
    echo "  • MCP Protocol: SSE (AI agent access)"
    echo "  • Worker: Polls every 60s for due reminders"
else
    echo -e "${RED}✗ Service failed to start${NC}"
    echo "Check log file: logs/main.log"
fi
echo "========================================="
echo ""
echo "Commands:"
echo "  • Stop services: ./stop.sh"
echo "  • View logs: tail -f logs/main.log"
echo ""
