#!/bin/bash
# Health check script - verifies all 5 services are ready
# If any service is not ready, returns non-zero exit code
# If all ready, returns 0 and prints "All services ready!"

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'  # No Color

PORTS=(9001 9002 9003 9004 8000)
SERVICES=("Applicant DB" "Risk Rules" "Decision Synthesis" "Notification" "FastAPI")
MAX_ATTEMPTS=60
ATTEMPT_DELAY=1

check_port() {
    local port=$1
    local service_name=$2

    for attempt in $(seq 1 $MAX_ATTEMPTS); do
        response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$port/health 2>/dev/null || echo "000")

        if [ "$response" = "200" ]; then
            echo -e "${GREEN}✅ Port $port ($service_name): healthy${NC}"
            return 0
        fi

        if [ $attempt -lt $MAX_ATTEMPTS ]; then
            sleep $ATTEMPT_DELAY
        fi
    done

    echo -e "${RED}❌ Port $port ($service_name): NOT READY${NC}"
    return 1
}

echo -e "${YELLOW}Checking all 5 services...${NC}"
echo ""

all_ready=true
for i in "${!PORTS[@]}"; do
    port=${PORTS[$i]}
    service=${SERVICES[$i]}

    if ! check_port $port "$service"; then
        all_ready=false
    fi
done

echo ""
if [ "$all_ready" = true ]; then
    echo -e "${GREEN}All services ready!${NC}"
    exit 0
else
    echo -e "${RED}Some services are not ready. Please wait or restart.${NC}"
    exit 1
fi
