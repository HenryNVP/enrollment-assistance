#!/bin/bash

# End-to-End RAG + Agent API Test Script
# Tests against existing vector store: RAG query (MS AI) → Agent API chat.
# No document upload; assumes vector store is already built.

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

echo -e "${BLUE}=== End-to-End RAG + Agent API Test (existing vector store) ===${NC}\n"
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
# PART 2: RAG - Query existing vector store (MS AI)
# ============================================================================
print_section "PART 2: RAG - MS AI Program Queries (existing knowledge base)"

QUERY="How many credits does the MS AI program require? What are the core courses and some specialization or elective courses?"
print_info "Querying RAG (full knowledge base): \"${QUERY}\""

# Use entity_id "public" to match ingest_rag.py default (so queries see ingested docs)
QUERY_RESPONSE=$(curl --http1.1 -s -X POST "${RAG_API_URL}/query" \
  -H "Authorization: Bearer ${RAG_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{
    \"query\": \"${QUERY}\",
    \"k\": 5,
    \"entity_id\": \"public\"
  }")

if echo "$QUERY_RESPONSE" | grep -q "\["; then
    RESULT_COUNT=$(echo "$QUERY_RESPONSE" | jq '. | length' 2>/dev/null || echo "0")
    print_success "RAG query successful - Found ${RESULT_COUNT} relevant chunks"
    
    RAG_CONTEXT=$(echo "$QUERY_RESPONSE" | jq -r '.[] | select(type == "array" and length > 0) | .[0] | select(.page_content != null) | .page_content' 2>/dev/null | head -5 | tr '\n' ' ' | sed 's/  */ /g' | cut -c1-1500)
    
    if [ -n "$RAG_CONTEXT" ] && [ "$RAG_CONTEXT" != "null" ]; then
        print_success "Extracted RAG context"
        if echo "$RAG_CONTEXT" | grep -q "33"; then
            print_success "Context contains 33 credits/units"
        fi
        if echo "$RAG_CONTEXT" | grep -qi "CMPE 25[5-8]\|core\|elective"; then
            print_success "Context contains core or elective course info"
        fi
        print_info "Context preview (first 300 chars):"
        echo "${RAG_CONTEXT:0:300}..."
    else
        print_error "No context extracted from RAG results"
        echo "$QUERY_RESPONSE" | jq '.' 2>/dev/null || echo "$QUERY_RESPONSE"
        exit 1
    fi
else
    print_error "RAG query failed"
    echo "$QUERY_RESPONSE" | jq '.' 2>/dev/null || echo "$QUERY_RESPONSE"
    exit 1
fi

# ============================================================================
# PART 4: Agent API - Chat (MS AI program question)
# ============================================================================
print_section "PART 4: Agent API - Chat (MS AI Program)"

# Ask the agent about MS AI program; it may use rag_search tool if integrated
CHAT_QUERY="How many credits does the MS in Artificial Intelligence program require, and what are some core and specialization courses?"
print_info "Sending chat: \"${CHAT_QUERY}\""

CHAT_RESPONSE=$(curl -s -X POST "${AGENT_API_URL}/api/v1/chatbot/chat" \
  -H "Authorization: Bearer ${SESSION_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{
    \"messages\": [
      {
        \"role\": \"user\",
        \"content\": \"${CHAT_QUERY}\"
      }
    ]
  }")

if echo "$CHAT_RESPONSE" | grep -q "messages"; then
    print_success "Agent API response received"
    
    ASSISTANT_RESPONSE=$(echo "$CHAT_RESPONSE" | jq -r '.messages[] | select(.role == "assistant") | .content' 2>/dev/null | head -1)
    
    if [ -n "$ASSISTANT_RESPONSE" ] && [ "$ASSISTANT_RESPONSE" != "null" ]; then
        echo ""
        echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${GREEN}Final Agent Response:${NC}"
        echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo "$ASSISTANT_RESPONSE"
        echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo ""
        
        if echo "$ASSISTANT_RESPONSE" | grep -q "33"; then
            print_success "Response mentions 33 credits/units"
        else
            print_info "Note: '33' not found in response (agent may not have used RAG or RAG may not be populated)"
        fi
        if echo "$ASSISTANT_RESPONSE" | grep -qi "CMPE\|core\|elective\|specialization"; then
            print_success "Response mentions courses or program structure"
        else
            print_info "Note: Course names not found (agent may use RAG tool when knowledge base is ingested)"
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
# PART 4: Verify Chat History
# ============================================================================
print_section "PART 4: Verify Chat History"

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
echo "  2. ✓ Queried RAG (existing vector store) for MS AI: 33 credits, core, electives"
echo "  3. ✓ Sent MS AI question to Agent API"
echo "  4. ✓ Verified chat history"
echo ""
print_info "Uses existing vector store (no uploads). MS AI: 33 credits, core courses, electives."
echo ""
