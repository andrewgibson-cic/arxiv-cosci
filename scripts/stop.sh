#!/bin/bash

# ArXiv AI Co-Scientist - Stop Script
# Gracefully stops all running services

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}Stopping ArXiv AI Co-Scientist services...${NC}"
echo ""

# Stop API server
if [ -f logs/api.pid ]; then
    API_PID=$(cat logs/api.pid)
    if kill -0 $API_PID 2>/dev/null; then
        echo -n "   Stopping API server..."
        kill $API_PID
        echo -e " ${GREEN}✓${NC}"
    fi
    rm logs/api.pid
fi

# Stop Frontend
if [ -f logs/frontend.pid ]; then
    FRONTEND_PID=$(cat logs/frontend.pid)
    if kill -0 $FRONTEND_PID 2>/dev/null; then
        echo -n "   Stopping Frontend..."
        kill $FRONTEND_PID
        echo -e " ${GREEN}✓${NC}"
    fi
    rm logs/frontend.pid
fi

# Stop Docker services
echo -n "   Stopping Docker services..."
docker compose stop >/dev/null 2>&1
echo -e " ${GREEN}✓${NC}"

echo ""
echo -e "${GREEN}All services stopped${NC}"
echo ""
echo -e "To start again: ${BLUE}npm run start${NC}"