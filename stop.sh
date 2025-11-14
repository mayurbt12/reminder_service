#!/bin/bash
# Stop script for Reminder Service
# Stops all services (via main.py)

# Change to script directory
cd "$(dirname "$0")"

# Activate virtual environment (for any cleanup tasks)
if [ -f .venv/bin/activate ]; then
    source .venv/bin/activate
fi

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "========================================="
echo "  Reminder Service - Shutdown"
echo "========================================="
echo ""

STOPPED=0
ERRORS=0

# Stop main process
echo "Stopping Reminder Service..."
if [ -f .pids/main.pid ]; then
    MAIN_PID=$(cat .pids/main.pid)

    if ps -p $MAIN_PID > /dev/null 2>&1; then
        echo "  Sending SIGTERM to main process (PID: $MAIN_PID)..."
        kill $MAIN_PID 2>/dev/null

        # Wait for graceful shutdown (max 10 seconds)
        for i in {1..10}; do
            if ! ps -p $MAIN_PID > /dev/null 2>&1; then
                echo -e "  ${GREEN}✓${NC} Service stopped gracefully"
                rm -f .pids/main.pid
                STOPPED=$((STOPPED + 1))
                break
            fi
            sleep 1
        done

        # Force kill if still running
        if ps -p $MAIN_PID > /dev/null 2>&1; then
            echo "  Forcing shutdown with SIGKILL..."
            kill -9 $MAIN_PID 2>/dev/null
            sleep 2
            if ! ps -p $MAIN_PID > /dev/null 2>&1; then
                echo -e "  ${GREEN}✓${NC} Service stopped (forced)"
                rm -f .pids/main.pid
                STOPPED=$((STOPPED + 1))
            else
                echo -e "  ${RED}✗${NC} Failed to stop service"
                ERRORS=$((ERRORS + 1))
            fi
        fi
    else
        echo -e "  ${YELLOW}⚠${NC} Service not running (cleaning up PID file)"
        rm -f .pids/main.pid
    fi
else
    # Try to find and kill by process name
    MAIN_PIDS=$(pgrep -f "python3 main.py")
    if [ -n "$MAIN_PIDS" ]; then
        echo "  Found service by name, stopping..."
        echo "$MAIN_PIDS" | xargs kill 2>/dev/null
        sleep 2
        echo -e "  ${GREEN}✓${NC} Service stopped"
        STOPPED=$((STOPPED + 1))
    else
        echo "  Service not running"
    fi
fi

echo ""

# Clean up any remaining PID files
if [ -d .pids ]; then
    rm -f .pids/*.pid 2>/dev/null
fi

echo "========================================="
if [ $ERRORS -eq 0 ]; then
    if [ $STOPPED -eq 0 ]; then
        echo -e "${YELLOW}⚠ No services were running${NC}"
    else
        echo -e "${GREEN}✓ Reminder Service stopped successfully!${NC}"
    fi
else
    echo -e "${RED}✗ Failed to stop service${NC}"
    echo "  You may need to manually kill processes"
fi
echo "========================================="
echo ""
