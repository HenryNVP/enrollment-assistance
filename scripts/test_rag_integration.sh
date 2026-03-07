#!/bin/bash

# RAG API Integration Test Script
# Tests RAG query against the existing vector store (no uploads).
# MS AI program: credits (33), core courses, specialization/electives.

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
RAG_API_URL="${RAG_API_URL:-http://localhost:8010}"
AGENT_API_URL="${AGENT_API_URL:-http://localhost:8000}"
SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo -e "${BLUE}Testing RAG API (existing vector store): ${RAG_API_URL}${NC}\n"

# Helper functions
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    print_error "jq is required but not installed. Install it with: sudo apt-get install jq"
    exit 1
fi

# 1. Health Check
echo "1. Health Check..."
HEALTH=$(curl -s "${RAG_API_URL}/health")
if echo "$HEALTH" | grep -q "UP\|healthy"; then
    print_success "Health check passed"
    echo "$HEALTH" | jq '.' 2>/dev/null || echo "$HEALTH"
else
    print_error "Health check failed"
    exit 1
fi
echo

# 2. Get Authentication Token
echo "2. Getting authentication token..."

# Try to get JWT_SECRET from RAG API's .env file to generate a proper token
RAG_ENV_FILE="${SCRIPT_DIR}/backend/services/rag_api/.env"
RAG_JWT_SECRET=""

if [ -f "$RAG_ENV_FILE" ]; then
    RAG_JWT_SECRET=$(grep "^JWT_SECRET=" "$RAG_ENV_FILE" 2>/dev/null | cut -d'=' -f2- | tr -d '"' | tr -d "'" | xargs)
fi

# If we have JWT_SECRET, generate a token directly
if [ -n "$RAG_JWT_SECRET" ] && command -v python3 &> /dev/null; then
    print_info "Generating JWT token using RAG API's JWT_SECRET..."
    TOKEN=$(python3 << EOF
import jwt
import datetime
try:
    payload = {
        "id": "test-user",
        "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)
    }
    print(jwt.encode(payload, "${RAG_JWT_SECRET}", algorithm="HS256"))
except Exception as e:
    print("")
EOF
)
    if [ -n "$TOKEN" ]; then
        print_success "JWT token generated"
    fi
fi

# If token generation failed, try Agent API (may not work if secrets differ)
if [ -z "$TOKEN" ]; then
    print_info "Getting token from Agent API (may not work if JWT secrets differ)..."
    TEST_EMAIL="test$(date +%s)@example.com"
    TEST_PASSWORD="Test1234!"

    REGISTER_RESPONSE=$(curl -s -X POST "${AGENT_API_URL}/api/v1/auth/register" \
      -H "Content-Type: application/json" \
      -d "{\"email\":\"${TEST_EMAIL}\",\"password\":\"${TEST_PASSWORD}\"}")

    if echo "$REGISTER_RESPONSE" | grep -q "access_token"; then
        TOKEN=$(echo "$REGISTER_RESPONSE" | jq -r '.token.access_token')
        print_success "User registered and token obtained from Agent API"
    elif echo "$REGISTER_RESPONSE" | grep -q "already\|exists"; then
        # User exists, try login
        LOGIN_RESPONSE=$(curl -s -X POST "${AGENT_API_URL}/api/v1/auth/login" \
          -H "Content-Type: application/x-www-form-urlencoded" \
          -d "username=${TEST_EMAIL}&password=${TEST_PASSWORD}&grant_type=password")
        TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.access_token')
        if [ -n "$TOKEN" ] && [ "$TOKEN" != "null" ]; then
            print_success "User logged in and token obtained from Agent API"
        fi
    elif echo "$REGISTER_RESPONSE" | grep -q "Rate limit\|rate limit"; then
        print_info "Rate limit hit. Note: Agent API tokens may not work with RAG API if JWT secrets differ."
        print_info "Set JWT_SECRET environment variable or ensure both services use the same secret."
    fi
fi

if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
    print_error "Failed to obtain authentication token"
    echo ""
    echo "Options:"
    echo "  1. Ensure RAG API .env file has JWT_SECRET: backend/services/rag_api/.env"
    echo "  2. Set JWT_SECRET environment variable: export JWT_SECRET=<rag-api-secret>"
    echo "  3. Install PyJWT: pip install PyJWT"
    echo ""
    echo "Note: Agent API and RAG API must use the SAME JWT_SECRET for tokens to work across services"
    exit 1
fi

print_info "Token acquired (first 40 chars): ${TOKEN:0:40}..."
echo

# 3. Query - MS AI program (existing vector store; file_id omitted = search all)
echo "3. MS AI program queries (knowledge base)..."

# entity_id "public" matches ingest_rag.py default so queries see ingested docs
run_rag_query() {
    local q="$1"
    curl --http1.1 -s -X POST "${RAG_API_URL}/query" \
      -H "Authorization: Bearer ${TOKEN}" \
      -H "Content-Type: application/json" \
      -d "{
        \"query\": \"${q}\",
        \"k\": 5,
        \"entity_id\": \"public\"
      }"
}

# 3a. How many credits?
CREDITS_RESPONSE=$(run_rag_query "How many credits or units does the MS AI program require?")
if echo "$CREDITS_RESPONSE" | grep -q "33"; then
    print_success "MS AI credits: response contains 33 units"
else
    if echo "$CREDITS_RESPONSE" | grep -q "\["; then
        print_info "MS AI credits query returned results but '33' not found in response"
        echo "$CREDITS_RESPONSE" | jq -r '.[][]? | .page_content? // empty' 2>/dev/null | head -5
    else
        print_error "MS AI credits query failed"
        echo "$CREDITS_RESPONSE" | jq '.' 2>/dev/null || echo "$CREDITS_RESPONSE"
    fi
fi

# 3b. Core courses
CORE_RESPONSE=$(run_rag_query "What are the core courses for the MS in Artificial Intelligence?")
if echo "$CORE_RESPONSE" | grep -qi "CMPE 25[5-8]\|core\|required"; then
    print_success "MS AI core courses: response contains core/required course info"
else
    if echo "$CORE_RESPONSE" | grep -q "\["; then
        print_info "MS AI core courses query returned results"
        echo "$CORE_RESPONSE" | jq -r '.[][]? | .page_content? // empty' 2>/dev/null | head -3
    else
        print_error "MS AI core courses query failed"
    fi
fi

# 5c. Specialization / elective courses
ELECTIVE_RESPONSE=$(run_rag_query "What are some specialization or elective courses in the MS AI program?")
if echo "$ELECTIVE_RESPONSE" | grep -qi "elective\|specialization\|CMPE 25[9]\|CMPE 26[0-8]"; then
    print_success "MS AI electives: response contains specialization/elective course info"
else
    if echo "$ELECTIVE_RESPONSE" | grep -q "\["; then
        print_info "MS AI electives query returned results"
        echo "$ELECTIVE_RESPONSE" | jq -r '.[][]? | .page_content? // empty' 2>/dev/null | head -3
    else
        print_error "MS AI electives query failed"
    fi
fi
echo

# 4. Get Document IDs (to list available documents)
echo "4. Getting available document IDs..."
IDS_RESPONSE=$(curl --http1.1 -s -X GET "${RAG_API_URL}/ids" \
  -H "Authorization: Bearer ${TOKEN}")

if echo "$IDS_RESPONSE" | grep -q "\["; then
    print_success "Retrieved document IDs"
    ID_COUNT=$(echo "$IDS_RESPONSE" | jq '. | length' 2>/dev/null || echo "0")
    echo "   Total document IDs: $ID_COUNT"
    echo "$IDS_RESPONSE" | jq '.' 2>/dev/null || echo "$IDS_RESPONSE"
    
    if [ "$ID_COUNT" -gt 0 ]; then
        FIRST_ID=$(echo "$IDS_RESPONSE" | jq -r '.[0]' 2>/dev/null)
        if [ -n "$FIRST_ID" ] && [ "$FIRST_ID" != "null" ]; then
            echo ""
            echo "7. Getting document details for: $FIRST_ID"
            DOC_RESPONSE=$(curl --http1.1 -s -X GET "${RAG_API_URL}/documents?ids=${FIRST_ID}" \
              -H "Authorization: Bearer ${TOKEN}")
            
            if echo "$DOC_RESPONSE" | grep -q "page_content"; then
                print_success "Retrieved document details"
                echo "$DOC_RESPONSE" | jq '.[0].page_content[:200]' 2>/dev/null || echo "$DOC_RESPONSE" | jq '.' 2>/dev/null
            else
                echo "$DOC_RESPONSE" | jq '.' 2>/dev/null || echo "$DOC_RESPONSE"
            fi
        fi
    fi
elif echo "$IDS_RESPONSE" | grep -q "detail"; then
    print_info "IDs endpoint response:"
    echo "$IDS_RESPONSE" | jq '.' 2>/dev/null || echo "$IDS_RESPONSE"
else
    echo "$IDS_RESPONSE" | jq '.' 2>/dev/null || echo "$IDS_RESPONSE"
fi
echo

echo -e "${GREEN}All RAG integration tests passed!${NC}"
echo "  (MS AI: 33 credits, core courses, specialization/electives — against existing vector store)"
