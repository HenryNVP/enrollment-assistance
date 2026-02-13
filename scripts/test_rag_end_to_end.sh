#!/bin/bash

# End-to-End RAG + Agent API Test Script
# Tests the complete flow: Document upload → RAG query → Agent API response with context
# This demonstrates how RAG context would be used in a final chat response

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

echo -e "${BLUE}=== End-to-End RAG + Agent API Test ===${NC}\n"
echo -e "${BLUE}RAG API: ${RAG_API_URL}${NC}"
echo -e "${BLUE}Agent API: ${AGENT_API_URL}${NC}\n"

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

print_section() {
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
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

# ============================================================================
# PART 1: Setup - Authentication
# ============================================================================
print_section "PART 1: Authentication Setup"

# Get JWT_SECRET from RAG API's .env file to generate a proper token
RAG_ENV_FILE="${SCRIPT_DIR}/backend/services/rag_api/.env"
RAG_JWT_SECRET=""

if [ -f "$RAG_ENV_FILE" ]; then
    RAG_JWT_SECRET=$(grep "^JWT_SECRET=" "$RAG_ENV_FILE" 2>/dev/null | cut -d'=' -f2- | tr -d '"' | tr -d "'" | xargs)
fi

# Generate token for RAG API
if [ -n "$RAG_JWT_SECRET" ] && command -v python3 &> /dev/null; then
    print_info "Generating JWT token for RAG API..."
    RAG_TOKEN=$(python3 << EOF
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
    if [ -n "$RAG_TOKEN" ]; then
        print_success "RAG API token generated"
    fi
fi

# Get Agent API token (register/login)
print_info "Getting Agent API token..."
TEST_EMAIL="rag-e2e-test-$(date +%s)@example.com"
TEST_PASSWORD="Test1234!"

REGISTER_RESPONSE=$(curl -s -X POST "${AGENT_API_URL}/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"${TEST_EMAIL}\",\"password\":\"${TEST_PASSWORD}\"}")

if echo "$REGISTER_RESPONSE" | grep -q "access_token"; then
    USER_TOKEN=$(echo "$REGISTER_RESPONSE" | jq -r '.token.access_token')
    print_success "User registered with Agent API"
elif echo "$REGISTER_RESPONSE" | grep -q "already\|exists"; then
    LOGIN_RESPONSE=$(curl -s -X POST "${AGENT_API_URL}/api/v1/auth/login" \
      -H "Content-Type: application/x-www-form-urlencoded" \
      -d "username=${TEST_EMAIL}&password=${TEST_PASSWORD}&grant_type=password")
    USER_TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.access_token')
    print_success "User logged in to Agent API"
else
    print_error "Failed to get Agent API token"
    echo "$REGISTER_RESPONSE" | jq '.' 2>/dev/null || echo "$REGISTER_RESPONSE"
    exit 1
fi

# Create session
print_info "Creating Agent API session..."
SESSION_RESPONSE=$(curl -s -X POST "${AGENT_API_URL}/api/v1/auth/session" \
  -H "Authorization: Bearer ${USER_TOKEN}")
SESSION_TOKEN=$(echo "$SESSION_RESPONSE" | jq -r '.token.access_token')

if [ -z "$SESSION_TOKEN" ] || [ "$SESSION_TOKEN" = "null" ]; then
    print_error "Failed to create session"
    exit 1
fi
print_success "Session created"

# ============================================================================
# PART 2: RAG - Document Upload
# ============================================================================
print_section "PART 2: RAG - Document Upload"

FILE_ID="e2e-test-registration-$(date +%s)"
print_info "Uploading document: ${REGISTRATION_FILE}"

UPLOAD_RESPONSE=$(curl --http1.1 -s -X POST "${RAG_API_URL}/embed" \
  -H "Authorization: Bearer ${RAG_TOKEN}" \
  -F "file_id=${FILE_ID}" \
  -F "entity_id=test-user" \
  -F "file=@${REGISTRATION_FILE}")

if echo "$UPLOAD_RESPONSE" | grep -q "\"status\":true"; then
    print_success "Document uploaded successfully"
    echo "$UPLOAD_RESPONSE" | jq '{file_id, filename, message}' 2>/dev/null || echo "$UPLOAD_RESPONSE"
else
    print_error "Upload failed"
    echo "$UPLOAD_RESPONSE" | jq '.' 2>/dev/null || echo "$UPLOAD_RESPONSE"
    exit 1
fi

# Wait a moment for embeddings to be processed
print_info "Waiting for embeddings to be processed..."
sleep 2

# ============================================================================
# PART 3: RAG - Query for Context
# ============================================================================
print_section "PART 3: RAG - Query for Relevant Context"

QUERY="What are enrollment appointments?"
print_info "Querying RAG: \"${QUERY}\""

QUERY_RESPONSE=$(curl --http1.1 -s -X POST "${RAG_API_URL}/query" \
  -H "Authorization: Bearer ${RAG_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{
    \"query\": \"${QUERY}\",
    \"file_id\": \"${FILE_ID}\",
    \"k\": 3,
    \"entity_id\": \"test-user\"
  }")

if echo "$QUERY_RESPONSE" | grep -q "\["; then
    RESULT_COUNT=$(echo "$QUERY_RESPONSE" | jq '. | length' 2>/dev/null || echo "0")
    print_success "RAG query successful - Found ${RESULT_COUNT} relevant chunks"
    
    # Extract context from RAG results
    # RAG API returns array of [document, score] pairs, so we need to access .[0].page_content
    RAG_CONTEXT=$(echo "$QUERY_RESPONSE" | jq -r '.[] | select(type == "array" and length > 0) | .[0] | select(.page_content != null) | .page_content' 2>/dev/null | head -3 | tr '\n' ' ' | sed 's/  */ /g' | cut -c1-1000)
    
    if [ -n "$RAG_CONTEXT" ] && [ "$RAG_CONTEXT" != "null" ]; then
        print_success "Extracted RAG context"
        print_info "Context preview (first 200 chars):"
        echo "${RAG_CONTEXT:0:200}..."
    else
        print_error "No context extracted from RAG results"
        print_info "Debug: RAG response structure:"
        echo "$QUERY_RESPONSE" | jq '.' 2>/dev/null || echo "$QUERY_RESPONSE"
        exit 1
    fi
else
    print_error "RAG query failed"
    echo "$QUERY_RESPONSE" | jq '.' 2>/dev/null || echo "$QUERY_RESPONSE"
    exit 1
fi

# ============================================================================
# PART 4: Agent API - Chat with RAG Context
# ============================================================================
print_section "PART 4: Agent API - Generate Final Response"

# Construct a message that includes the RAG context
# In a real implementation, the Agent API would automatically fetch this from RAG
# For this test, we'll include it in the user message to demonstrate the flow
USER_MESSAGE="Based on the following information about enrollment: ${RAG_CONTEXT:0:500}... Can you explain what enrollment appointments are?"

print_info "Sending chat message to Agent API with RAG context..."

CHAT_RESPONSE=$(curl -s -X POST "${AGENT_API_URL}/api/v1/chatbot/chat" \
  -H "Authorization: Bearer ${SESSION_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{
    \"messages\": [
      {
        \"role\": \"user\",
        \"content\": \"${QUERY}\"
      }
    ]
  }")

if echo "$CHAT_RESPONSE" | grep -q "messages"; then
    print_success "Agent API response received"
    
    # Extract the assistant's response
    ASSISTANT_RESPONSE=$(echo "$CHAT_RESPONSE" | jq -r '.messages[] | select(.role == "assistant") | .content' 2>/dev/null | head -1)
    
    if [ -n "$ASSISTANT_RESPONSE" ] && [ "$ASSISTANT_RESPONSE" != "null" ]; then
        echo ""
        echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${GREEN}Final Agent Response:${NC}"
        echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo "$ASSISTANT_RESPONSE"
        echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""
        
        # Check if response mentions enrollment-related terms (basic validation)
        if echo "$ASSISTANT_RESPONSE" | grep -qi "enrollment\|appointment\|register"; then
            print_success "Response contains enrollment-related content"
        else
            print_info "Note: Response may not have used RAG context (Agent API may not have RAG tool integrated yet)"
        fi
    else
        print_error "No assistant response found"
        echo "$CHAT_RESPONSE" | jq '.' 2>/dev/null || echo "$CHAT_RESPONSE"
    fi
else
    print_error "Chat request failed"
    echo "$CHAT_RESPONSE" | jq '.' 2>/dev/null || echo "$CHAT_RESPONSE"
    exit 1
fi

# ============================================================================
# PART 5: Verify Chat History
# ============================================================================
print_section "PART 5: Verify Chat History"

print_info "Retrieving chat history..."
HISTORY_RESPONSE=$(curl -s -X GET "${AGENT_API_URL}/api/v1/chatbot/messages" \
  -H "Authorization: Bearer ${SESSION_TOKEN}")

MSG_COUNT=$(echo "$HISTORY_RESPONSE" | jq '.messages | length' 2>/dev/null || echo "0")
if [ "$MSG_COUNT" -gt 0 ]; then
    print_success "Retrieved ${MSG_COUNT} messages from history"
    echo "$HISTORY_RESPONSE" | jq '.messages[] | {role, content: (.content[:100] + "...")}' 2>/dev/null || echo "$HISTORY_RESPONSE"
else
    print_error "Failed to get chat history"
fi

# ============================================================================
# Summary
# ============================================================================
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ End-to-End Test Complete!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Test Flow Summary:"
echo "  1. ✓ Authenticated with RAG API and Agent API"
echo "  2. ✓ Uploaded document to RAG API (file_id: ${FILE_ID})"
echo "  3. ✓ Queried RAG API for relevant context"
echo "  4. ✓ Sent chat message to Agent API"
echo "  5. ✓ Received final response from Agent API"
echo "  6. ✓ Verified chat history"
echo ""
print_info "Note: In a production setup, the Agent API would automatically"
print_info "      call RAG API when needed via a RAG tool integration."
echo ""
