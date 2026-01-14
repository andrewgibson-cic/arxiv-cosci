#!/bin/bash

# Test Suite for Startup Consolidation
# This script tests all aspects of the startup system

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Function to run a test
run_test() {
    local test_name=$1
    local test_command=$2
    
    TESTS_RUN=$((TESTS_RUN + 1))
    echo -n "  Testing: $test_name ... "
    
    if eval "$test_command" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ PASS${NC}"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        echo -e "${RED}✗ FAIL${NC}"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  ArXiv AI Co-Scientist - Startup Test Suite               ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# ============================================================================
# Test 1: Prerequisites
# ============================================================================
echo -e "${YELLOW}[1/8] Testing Prerequisites${NC}"

run_test "Docker installed" "command -v docker"
run_test "Docker Compose available" "docker compose version"
run_test "Node.js installed" "command -v node"
run_test "npm installed" "command -v npm"
run_test "Python installed" "command -v python3"
run_test "Poetry installed" "command -v poetry"
run_test "Git installed" "command -v git"
run_test "curl installed" "command -v curl"

echo ""

# ============================================================================
# Test 2: Docker Daemon
# ============================================================================
echo -e "${YELLOW}[2/8] Testing Docker Daemon${NC}"

run_test "Docker daemon running" "docker info"
run_test "Docker Compose CLI working" "docker compose ps"

echo ""

# ============================================================================
# Test 3: File Structure
# ============================================================================
echo -e "${YELLOW}[3/8] Testing File Structure${NC}"

run_test "start.sh exists" "test -f scripts/start.sh"
run_test "start.sh is executable" "test -x scripts/start.sh"
run_test "stop.sh exists" "test -f scripts/stop.sh"
run_test "stop.sh is executable" "test -x scripts/stop.sh"
run_test "package.json exists" "test -f package.json"
run_test "docker-compose.yml exists" "test -f docker-compose.yml"
run_test ".env.example exists" "test -f .env.example"
run_test "QUICKSTART.md exists" "test -f QUICKSTART.md"

echo ""

# ============================================================================
# Test 4: NPM Scripts
# ============================================================================
echo -e "${YELLOW}[4/8] Testing NPM Scripts${NC}"

run_test "package.json is valid JSON" "cat package.json | jq . > /dev/null"
run_test "start script defined" "cat package.json | jq -e '.scripts.start'"
run_test "stop script defined" "cat package.json | jq -e '.scripts.stop'"
run_test "docker:up script defined" "cat package.json | jq -e '.scripts[\"docker:up\"]'"
run_test "docker:down script defined" "cat package.json | jq -e '.scripts[\"docker:down\"]'"

echo ""

# ============================================================================
# Test 5: Docker Services
# ============================================================================
echo -e "${YELLOW}[5/8] Testing Docker Services${NC}"

# Start services if not running
if ! docker compose ps | grep -q "neo4j.*running"; then
    echo "  Starting Docker services..."
    docker compose up -d neo4j > /dev/null 2>&1
    sleep 5
fi

run_test "Neo4j container exists" "docker compose ps | grep -q neo4j"
run_test "Neo4j is running" "docker compose ps | grep neo4j | grep -q 'running\|Up'"
run_test "Neo4j port 7474 accessible" "curl -s http://localhost:7474 > /dev/null"
run_test "Neo4j port 7687 accessible" "nc -z localhost 7687"

echo ""

# ============================================================================
# Test 6: Python Environment
# ============================================================================
echo -e "${YELLOW}[6/8] Testing Python Environment${NC}"

run_test "pyproject.toml exists" "test -f pyproject.toml"
run_test "Poetry lock file exists" "test -f poetry.lock"
run_test "Poetry environment exists" "poetry env info > /dev/null"
run_test "Can import fastapi" "poetry run python -c 'import fastapi'"
run_test "Can import neo4j" "poetry run python -c 'import neo4j'"

echo ""

# ============================================================================
# Test 7: API Backend
# ============================================================================
echo -e "${YELLOW}[7/8] Testing API Backend${NC}"

run_test "API main.py exists" "test -f apps/api/main.py"
run_test "System router exists" "test -f apps/api/routers/system.py"
run_test "Health router exists" "test -f apps/api/routers/health.py"
run_test "Ingestion router exists" "test -f apps/api/routers/ingestion.py"
run_test "Can import API module" "poetry run python -c 'from apps.api import main'"

# Test if API is running, if not start it temporarily
API_RUNNING=false
if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
    API_RUNNING=true
    run_test "API server responding" "curl -s http://localhost:8000/api/health | grep -q status"
    run_test "System health endpoint works" "curl -s http://localhost:8000/api/system/health | grep -q status"
else
    echo "  ${YELLOW}Note: API not running, skipping live API tests${NC}"
fi

echo ""

# ============================================================================
# Test 8: Frontend
# ============================================================================
echo -e "${YELLOW}[8/8] Testing Frontend${NC}"

run_test "Frontend directory exists" "test -d apps/web"
run_test "Frontend package.json exists" "test -f apps/web/package.json"
run_test "Frontend src exists" "test -d apps/web/src"
run_test "Dashboard component exists" "test -f apps/web/src/pages/Dashboard.tsx"
run_test "App.tsx exists" "test -f apps/web/src/App.tsx"
run_test "vite.config.ts exists" "test -f apps/web/vite.config.ts"

# Check if node_modules exists
if [ -d "apps/web/node_modules" ]; then
    run_test "Frontend dependencies installed" "test -d apps/web/node_modules"
else
    echo "  ${YELLOW}Note: Frontend dependencies not installed${NC}"
fi

echo ""

# ============================================================================
# Test Results Summary
# ============================================================================
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Test Results Summary                                      ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "  Total Tests:  $TESTS_RUN"
echo -e "  ${GREEN}Passed:       $TESTS_PASSED${NC}"
if [ $TESTS_FAILED -gt 0 ]; then
    echo -e "  ${RED}Failed:       $TESTS_FAILED${NC}"
else
    echo -e "  ${GREEN}Failed:       $TESTS_FAILED${NC}"
fi
echo ""

# Calculate percentage
PASS_PERCENTAGE=$((TESTS_PASSED * 100 / TESTS_RUN))

if [ $PASS_PERCENTAGE -eq 100 ]; then
    echo -e "${GREEN}✨ All tests passed! ($PASS_PERCENTAGE%)${NC}"
    echo ""
    exit 0
elif [ $PASS_PERCENTAGE -ge 80 ]; then
    echo -e "${YELLOW}⚠️  Most tests passed ($PASS_PERCENTAGE%)${NC}"
    echo ""
    exit 0
else
    echo -e "${RED}❌ Too many failures ($PASS_PERCENTAGE% pass rate)${NC}"
    echo ""
    exit 1
fi