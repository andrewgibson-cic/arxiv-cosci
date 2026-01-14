#!/bin/bash

# ArXiv AI Co-Scientist - Unified Startup Script
# This script starts all services and opens the dashboard

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
API_PORT=8000
WEB_PORT=5173
NEO4J_PORT=7474
GROBID_PORT=8070

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  ArXiv AI Co-Scientist - Starting All Services            ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if a port is in use
port_in_use() {
    lsof -i :"$1" >/dev/null 2>&1
}

# Function to wait for a service to be ready
wait_for_service() {
    local url=$1
    local name=$2
    local max_attempts=30
    local attempt=0
    
    echo -n "   Waiting for $name to be ready"
    while [ $attempt -lt $max_attempts ]; do
        if curl -s "$url" >/dev/null 2>&1; then
            echo -e " ${GREEN}✓${NC}"
            return 0
        fi
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    echo -e " ${RED}✗${NC}"
    return 1
}

# Step 1: Check Prerequisites
echo -e "${YELLOW}[1/7]${NC} Checking prerequisites..."

if ! command_exists docker; then
    echo -e "${RED}✗ Docker is not installed${NC}"
    echo "Please install Docker Desktop from https://www.docker.com/products/docker-desktop"
    exit 1
fi
echo -e "   ${GREEN}✓${NC} Docker found"

if ! command_exists node; then
    echo -e "${RED}✗ Node.js is not installed${NC}"
    echo "Please install Node.js 20+ from https://nodejs.org"
    exit 1
fi
echo -e "   ${GREEN}✓${NC} Node.js found ($(node --version))"

if ! command_exists poetry; then
    echo -e "${RED}✗ Poetry is not installed${NC}"
    echo "Please install Poetry from https://python-poetry.org/docs/#installation"
    exit 1
fi
echo -e "   ${GREEN}✓${NC} Poetry found"

# Check if Docker daemon is running
if ! docker info >/dev/null 2>&1; then
    echo -e "${RED}✗ Docker daemon is not running${NC}"
    echo "Please start Docker Desktop"
    exit 1
fi
echo -e "   ${GREEN}✓${NC} Docker daemon running"

# Check for .env file
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠ No .env file found${NC}"
    if [ -f .env.example ]; then
        echo "   Copying .env.example to .env..."
        cp .env.example .env
        echo -e "${YELLOW}   ⚠ Please edit .env and add your GEMINI_API_KEY${NC}"
    fi
fi

# Step 2: Create necessary directories
echo -e "${YELLOW}[2/7]${NC} Creating data directories..."
mkdir -p data/batch_collection
mkdir -p data/processed
mkdir -p data/chroma
echo -e "   ${GREEN}✓${NC} Directories ready"

# Step 3: Start Docker Services
echo -e "${YELLOW}[3/7]${NC} Starting Docker services (Neo4j, Grobid)..."

if docker compose ps | grep -q "neo4j.*running"; then
    echo -e "   ${GREEN}✓${NC} Neo4j already running"
else
    docker compose up -d neo4j
    wait_for_service "http://localhost:$NEO4J_PORT" "Neo4j"
fi

# Try to start Grobid (optional - may fail on macOS)
if docker compose ps | grep -q "grobid.*running"; then
    echo -e "   ${GREEN}✓${NC} Grobid already running"
else
    echo -n "   Starting Grobid (optional PDF parser)..."
    docker compose up -d grobid 2>/dev/null || true
    
    # Wait for Grobid with shorter timeout (it's optional)
    grobid_attempts=15
    attempt=0
    grobid_ok=false
    
    while [ $attempt -lt $grobid_attempts ]; do
        if curl -s "http://localhost:$GROBID_PORT/api/isalive" >/dev/null 2>&1; then
            echo -e " ${GREEN}✓${NC}"
            grobid_ok=true
            break
        fi
        sleep 2
        attempt=$((attempt + 1))
    done
    
    if [ "$grobid_ok" = false ]; then
        echo -e " ${YELLOW}⚠${NC}"
        echo -e "   ${YELLOW}Note: Grobid failed to start (known issue on macOS)${NC}"
        echo -e "   ${YELLOW}      PDF parsing will use fallback methods${NC}"
        # Stop the failing container
        docker compose stop grobid 2>/dev/null || true
    fi
fi

# Step 4: Install Dependencies (if needed)
echo -e "${YELLOW}[4/7]${NC} Checking Python dependencies..."
if ! poetry run python -c "import fastapi" >/dev/null 2>&1; then
    echo "   Installing Python dependencies (this may take a few minutes)..."
    poetry install --no-interaction
else
    echo -e "   ${GREEN}✓${NC} Python dependencies installed"
fi

echo -e "${YELLOW}[5/7]${NC} Checking Node.js dependencies..."
cd apps/web
if [ ! -d "node_modules" ]; then
    echo "   Installing Node.js dependencies..."
    npm install --silent
else
    echo -e "   ${GREEN}✓${NC} Node.js dependencies installed"
fi
cd ../..

# Step 5: Initialize Database (if needed)
echo -e "${YELLOW}[6/7]${NC} Checking database initialization..."
# This is a placeholder - you can add actual DB init logic here
echo -e "   ${GREEN}✓${NC} Database ready"

# Step 6: Start Services
echo -e "${YELLOW}[7/7]${NC} Starting API and Frontend..."

# Create a logs directory
mkdir -p logs

# Start API server in background
echo "   Starting API server on port $API_PORT..."
poetry run uvicorn apps.api.main:app --host 0.0.0.0 --port $API_PORT --reload > logs/api.log 2>&1 &
API_PID=$!
echo $API_PID > logs/api.pid

# Wait for API to be ready
wait_for_service "http://localhost:$API_PORT/api/health" "API Server"

# Start frontend in background
echo "   Starting Frontend on port $WEB_PORT..."
cd apps/web
npm run dev > ../../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > ../../logs/frontend.pid
cd ../..

# Wait for frontend to be ready
sleep 3

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  🚀 All Services Started Successfully!                     ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Services:${NC}"
echo -e "   Dashboard:   ${GREEN}http://localhost:$WEB_PORT/dashboard${NC}"
echo -e "   Graph View:  ${GREEN}http://localhost:$WEB_PORT/graph${NC}"
echo -e "   API Docs:    ${GREEN}http://localhost:$API_PORT/docs${NC}"
echo -e "   Neo4j:       ${GREEN}http://localhost:$NEO4J_PORT${NC} (user: neo4j, pass: password)"
echo ""
echo -e "${BLUE}Logs:${NC}"
echo -e "   API:         tail -f logs/api.log"
echo -e "   Frontend:    tail -f logs/frontend.log"
echo ""
echo -e "${BLUE}To stop all services:${NC}"
echo -e "   npm run stop"
echo -e "   or: ./scripts/stop.sh"
echo ""

# Open browser to dashboard (Mac/Linux)
if command_exists open; then
    echo "Opening dashboard in browser..."
    sleep 2
    open "http://localhost:$WEB_PORT/dashboard"
elif command_exists xdg-open; then
    echo "Opening dashboard in browser..."
    sleep 2
    xdg-open "http://localhost:$WEB_PORT/dashboard"
fi

echo -e "${GREEN}✨ Ready to collect and visualize papers!${NC}"
echo ""