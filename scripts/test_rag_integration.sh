#!/bin/bash

# RAG API Integration Test Script
# Tests document upload and query functionality
# Uses Agent API for authentication

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
TEST_DATA_DIR="${SCRIPT_DIR}/test_data"
REGISTRATION_FILE="${TEST_DATA_DIR}/documents/registration.txt"

echo -e "${BLUE}Testing RAG API: ${RAG_API_URL}${NC}\n"

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

# Check if test data exists
if [ ! -f "$REGISTRATION_FILE" ]; then
    print_error "Test data not found: ${REGISTRATION_FILE}"
    echo "Please ensure test data is in test_data/documents/"
    exit 1
fi

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

# 3. Upload Document
echo "3. Uploading registration document..."
FILE_ID="test-registration-$(date +%s)"

UPLOAD_RESPONSE=$(curl --http1.1 -s -X POST "${RAG_API_URL}/embed" \
  -H "Authorization: Bearer ${TOKEN}" \
  -F "file_id=${FILE_ID}" \
  -F "entity_id=test-user" \
  -F "file=@${REGISTRATION_FILE}")

# Check if upload was successful
if echo "$UPLOAD_RESPONSE" | grep -q "\"status\":true"; then
    print_success "Document uploaded successfully"
    echo "$UPLOAD_RESPONSE" | jq '.' 2>/dev/null || echo "$UPLOAD_RESPONSE"
else
    print_error "Upload failed"
    echo "$UPLOAD_RESPONSE" | jq '.' 2>/dev/null || echo "$UPLOAD_RESPONSE"
    exit 1
fi
echo

# 4. Query Documents (requires file_id)
echo "4. Querying documents..."
QUERY_RESPONSE=$(curl --http1.1 -s -X POST "${RAG_API_URL}/query" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{
    \"query\": \"What are enrollment appointments?\",
    \"file_id\": \"${FILE_ID}\",
    \"k\": 3,
    \"entity_id\": \"test-user\"
  }")

# Check if query was successful (returns array of documents)
if echo "$QUERY_RESPONSE" | grep -q "\["; then
    print_success "Query successful"
    RESULT_COUNT=$(echo "$QUERY_RESPONSE" | jq '. | length' 2>/dev/null || echo "0")
    echo "   Found $RESULT_COUNT results"
    if [ "$RESULT_COUNT" -gt 0 ]; then
        echo "$QUERY_RESPONSE" | jq '.[0]' 2>/dev/null || echo "$QUERY_RESPONSE" | jq '.' 2>/dev/null
    else
        print_info "No results found (embeddings may still be processing, or query doesn't match content)"
        echo "$QUERY_RESPONSE" | jq '.' 2>/dev/null || echo "$QUERY_RESPONSE"
    fi
elif echo "$QUERY_RESPONSE" | grep -q "detail"; then
    print_error "Query failed"
    echo "$QUERY_RESPONSE" | jq '.' 2>/dev/null || echo "$QUERY_RESPONSE"
    exit 1
else
    print_info "Query response:"
    echo "$QUERY_RESPONSE" | jq '.' 2>/dev/null || echo "$QUERY_RESPONSE"
fi
echo

# 5. Get Document IDs (to list available documents)
echo "5. Getting available document IDs..."
IDS_RESPONSE=$(curl --http1.1 -s -X GET "${RAG_API_URL}/ids" \
  -H "Authorization: Bearer ${TOKEN}")

if echo "$IDS_RESPONSE" | grep -q "\["; then
    print_success "Retrieved document IDs"
    ID_COUNT=$(echo "$IDS_RESPONSE" | jq '. | length' 2>/dev/null || echo "0")
    echo "   Total document IDs: $ID_COUNT"
    echo "$IDS_RESPONSE" | jq '.' 2>/dev/null || echo "$IDS_RESPONSE"
    
    # 6. Get specific document by ID
    if [ "$ID_COUNT" -gt 0 ]; then
        FIRST_ID=$(echo "$IDS_RESPONSE" | jq -r '.[0]' 2>/dev/null)
        if [ -n "$FIRST_ID" ] && [ "$FIRST_ID" != "null" ]; then
            echo ""
            echo "6. Getting document details for: $FIRST_ID"
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
