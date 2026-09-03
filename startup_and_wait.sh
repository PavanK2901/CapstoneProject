#!/bin/bash
# Automatic startup script - starts all services and waits until they're all ready
# Usage: bash startup_and_wait.sh

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}       Loan Approval System - Automatic Startup${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# Step 1: Clean old data
echo -e "${YELLOW}[1/4] Cleaning old database...${NC}"
rm -f data/audit.db
echo -e "${GREEN}✅ Old data cleaned${NC}"
echo ""

# Step 2: Kill any existing processes
echo -e "${YELLOW}[2/4] Stopping any running services...${NC}"
pkill -9 -f "python3.*run_all.py" 2>/dev/null || true
pkill -9 -f "mcp_servers" 2>/dev/null || true
pkill -9 -f "api/main.py" 2>/dev/null || true
sleep 1
echo -e "${GREEN}✅ Old services stopped${NC}"
echo ""

# Step 3: Start services
echo -e "${YELLOW}[3/4] Starting all services...${NC}"
python3 run_all.py > /tmp/services.log 2>&1 &
SERVICE_PID=$!
echo -e "${GREEN}✅ Services starting (PID: $SERVICE_PID)${NC}"
echo ""

# Step 4: Wait for all services to be ready
echo -e "${YELLOW}[4/4] Waiting for all 5 services to initialize...${NC}"
echo "      (This may take 10-15 seconds...)"
echo ""

# Wait for all ports to be healthy
PORTS=(9001 9002 9003 9004 8000)
SERVICES=("Applicant DB" "Risk Rules" "Decision Synthesis" "Notification" "FastAPI")
MAX_WAIT=120
ELAPSED=0
INTERVAL=2

all_ready=false
while [ $ELAPSED -lt $MAX_WAIT ]; do
    all_healthy=true

    for i in "${!PORTS[@]}"; do
        port=${PORTS[$i]}
        response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$port/health 2>/dev/null || echo "000")

        if [ "$response" != "200" ]; then
            all_healthy=false
            break
        fi
    done

    if [ "$all_healthy" = true ]; then
        all_ready=true
        break
    fi

    sleep $INTERVAL
    ELAPSED=$((ELAPSED + INTERVAL))
    echo -n "."
done

echo ""
echo ""

if [ "$all_ready" = true ]; then
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}       ✅ ALL SERVICES READY! (Ready in ~${ELAPSED}s)${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${BLUE}You can now submit applications:${NC}"
    echo ""
    echo "  curl -X POST http://localhost:8000/applications \\"
    echo "    -H 'Content-Type: application/json' \\"
    echo "    -d '{\"applicant_id\":\"TEST001\",\"age\":32,\"income\":85000,...}'"
    echo ""
    echo -e "${BLUE}Or use the Streamlit UI:${NC}"
    echo "  streamlit run ui/app.py"
    echo ""
    exit 0
else
    echo -e "${RED}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${RED}       ❌ STARTUP TIMEOUT - Services did not fully initialize${NC}"
    echo -e "${RED}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${RED}Debug info:${NC}"
    echo "  Service logs: tail -50 /tmp/services.log"
    echo "  Check ports: lsof -i :8000 -i :9001 -i :9002 -i :9003 -i :9004"
    echo ""
    pkill -9 -f "python3.*run_all.py" 2>/dev/null || true
    exit 1
fi
