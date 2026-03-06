#!/bin/bash
# Smoke test script for SmartShop AI deployment validation
# Usage: ./scripts/smoke_test.sh <base_url>
# Exit codes: 0 = success, 1 = failure

set -euo pipefail

BASE_URL="${1:?Usage: $0 <base_url>}"
MAX_RETRIES=10
RETRY_DELAY=15

check_endpoint() {
    local url="$1"
    local name="$2"

    for i in $(seq 1 $MAX_RETRIES); do
        echo "[$name] Attempt $i/$MAX_RETRIES: GET $url"
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 15 "$url" || echo "000")

        if [ "$HTTP_CODE" = "200" ]; then
            echo "[$name] OK (HTTP $HTTP_CODE)"
            return 0
        fi

        echo "[$name] HTTP $HTTP_CODE — retrying in ${RETRY_DELAY}s..."
        sleep "$RETRY_DELAY"
    done

    echo "[$name] FAILED after $MAX_RETRIES attempts"
    return 1
}

echo "=== SmartShop AI Smoke Tests ==="
echo "Base URL: $BASE_URL"
echo ""

FAILED=0

check_endpoint "$BASE_URL/health" "Health" || FAILED=1
check_endpoint "$BASE_URL/health/metrics" "Metrics" || FAILED=1
check_endpoint "$BASE_URL/health/alerts" "Alerts" || FAILED=1

echo ""
if [ "$FAILED" -eq 0 ]; then
    echo "=== All smoke tests PASSED ==="
    exit 0
else
    echo "=== Some smoke tests FAILED ==="
    exit 1
fi
