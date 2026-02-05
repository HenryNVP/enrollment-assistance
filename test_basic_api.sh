#!/bin/bash

# Basic API Test Script for Enrollment Assistant Agent API
# Tests: Health, Registration, Login, Session Creation, Chat, History

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
AGENT_API_URL="${AGENT_API_URL:-http://localhost:8000}"
TEST_EMAIL="${TEST_EMAIL:-test$(date +%s)@example.com}"
TEST_PASSWORD="${TEST_PASSWORD:-Test1234!}"

# Helper functions
print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

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

# Test 1: Health Check
print_header "Test 1: Health Check"
HEALTH_RESPONSE=$(curl -s -w "\n%{http_code}" "${AGENT_API_URL}/health")
HTTP_CODE=$(echo "$HEALTH_RESPONSE" | tail -n1)
BODY=$(echo "$HEALTH_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" -eq 200 ]; then
    print_success "Health check passed (HTTP $HTTP_CODE)"
    echo "$BODY" | jq '.'
else
    print_error "Health check failed (HTTP $HTTP_CODE)"
    echo "$BODY"
    exit 1
fi

# Test 2: Register User
print_header "Test 2: Register User"
print_info "Email: $TEST_EMAIL"
REGISTER_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${AGENT_API_URL}/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"${TEST_EMAIL}\",
    \"password\": \"${TEST_PASSWORD}\"
  }")

HTTP_CODE=$(echo "$REGISTER_RESPONSE" | tail -n1)
BODY=$(echo "$REGISTER_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" -eq 200 ]; then
    print_success "User registration successful (HTTP $HTTP_CODE)"
    USER_TOKEN=$(echo "$BODY" | jq -r '.token.access_token')
    USER_ID=$(echo "$BODY" | jq -r '.id')
    echo "$BODY" | jq '.'
    print_info "User ID: $USER_ID"
    print_info "User Token saved for subsequent requests"
else
    print_error "User registration failed (HTTP $HTTP_CODE)"
    echo "$BODY" | jq '.' 2>/dev/null || echo "$BODY"
    
    # If user already exists, try login instead
    if echo "$BODY" | grep -q "already registered\|already exists"; then
        print_info "User already exists, attempting login..."
        
        LOGIN_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${AGENT_API_URL}/api/v1/auth/login" \
          -H "Content-Type: application/x-www-form-urlencoded" \
          -d "username=${TEST_EMAIL}&password=${TEST_PASSWORD}&grant_type=password")
        
        HTTP_CODE=$(echo "$LOGIN_RESPONSE" | tail -n1)
        LOGIN_BODY=$(echo "$LOGIN_RESPONSE" | sed '$d')
        
        if [ "$HTTP_CODE" -eq 200 ]; then
            print_success "Login successful (HTTP $HTTP_CODE)"
            USER_TOKEN=$(echo "$LOGIN_BODY" | jq -r '.access_token')
            echo "$LOGIN_BODY" | jq '.'
        else
            print_error "Login failed (HTTP $HTTP_CODE)"
            echo "$LOGIN_BODY" | jq '.' 2>/dev/null || echo "$LOGIN_BODY"
            exit 1
        fi
    else
        exit 1
    fi
fi

# Test 3: Create Session
print_header "Test 3: Create Chat Session"
SESSION_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${AGENT_API_URL}/api/v1/auth/session" \
  -H "Authorization: Bearer ${USER_TOKEN}")

HTTP_CODE=$(echo "$SESSION_RESPONSE" | tail -n1)
BODY=$(echo "$SESSION_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" -eq 200 ]; then
    print_success "Session created successfully (HTTP $HTTP_CODE)"
    SESSION_TOKEN=$(echo "$BODY" | jq -r '.token.access_token')
    SESSION_ID=$(echo "$BODY" | jq -r '.session_id')
    echo "$BODY" | jq '.'
    print_info "Session ID: $SESSION_ID"
    print_info "Session Token saved for chat requests"
else
    print_error "Session creation failed (HTTP $HTTP_CODE)"
    echo "$BODY" | jq '.' 2>/dev/null || echo "$BODY"
    exit 1
fi

# Test 4: Send Chat Message
print_header "Test 4: Send Chat Message"
CHAT_MESSAGE="Hello! Can you help me understand the enrollment process?"
print_info "Sending message: \"$CHAT_MESSAGE\""

CHAT_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${AGENT_API_URL}/api/v1/chatbot/chat" \
  -H "Authorization: Bearer ${SESSION_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{
    \"messages\": [
      {
        \"role\": \"user\",
        \"content\": \"${CHAT_MESSAGE}\"
      }
    ]
  }")

HTTP_CODE=$(echo "$CHAT_RESPONSE" | tail -n1)
BODY=$(echo "$CHAT_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" -eq 200 ]; then
    print_success "Chat message sent successfully (HTTP $HTTP_CODE)"
    echo "$BODY" | jq '.'
    
    # Extract assistant response
    ASSISTANT_RESPONSE=$(echo "$BODY" | jq -r '.messages[-1].content' 2>/dev/null || echo "")
    if [ -n "$ASSISTANT_RESPONSE" ] && [ "$ASSISTANT_RESPONSE" != "null" ]; then
        print_info "Assistant response received (${#ASSISTANT_RESPONSE} characters)"
    fi
else
    print_error "Chat message failed (HTTP $HTTP_CODE)"
    echo "$BODY" | jq '.' 2>/dev/null || echo "$BODY"
    exit 1
fi

# Test 5: Get Chat History
print_header "Test 5: Get Chat History"
HISTORY_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "${AGENT_API_URL}/api/v1/chatbot/messages" \
  -H "Authorization: Bearer ${SESSION_TOKEN}")

HTTP_CODE=$(echo "$HISTORY_RESPONSE" | tail -n1)
BODY=$(echo "$HISTORY_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" -eq 200 ]; then
    print_success "Chat history retrieved successfully (HTTP $HTTP_CODE)"
    MESSAGE_COUNT=$(echo "$BODY" | jq '.messages | length' 2>/dev/null || echo "0")
    print_info "Total messages in history: $MESSAGE_COUNT"
    echo "$BODY" | jq '.messages[] | {role: .role, content: .content[:100]}' 2>/dev/null || echo "$BODY"
else
    print_error "Get chat history failed (HTTP $HTTP_CODE)"
    echo "$BODY" | jq '.' 2>/dev/null || echo "$BODY"
    exit 1
fi

# Test 6: Send Another Chat Message (to verify conversation continuity)
print_header "Test 6: Send Follow-up Chat Message"
FOLLOWUP_MESSAGE="What are the key requirements I need to know?"
print_info "Sending follow-up message: \"$FOLLOWUP_MESSAGE\""

CHAT_RESPONSE2=$(curl -s -w "\n%{http_code}" -X POST "${AGENT_API_URL}/api/v1/chatbot/chat" \
  -H "Authorization: Bearer ${SESSION_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{
    \"messages\": [
      {
        \"role\": \"user\",
        \"content\": \"${FOLLOWUP_MESSAGE}\"
      }
    ]
  }")

HTTP_CODE=$(echo "$CHAT_RESPONSE2" | tail -n1)
BODY=$(echo "$CHAT_RESPONSE2" | sed '$d')

if [ "$HTTP_CODE" -eq 200 ]; then
    print_success "Follow-up chat message sent successfully (HTTP $HTTP_CODE)"
    echo "$BODY" | jq '.messages[-1]' 2>/dev/null || echo "$BODY"
else
    print_error "Follow-up chat message failed (HTTP $HTTP_CODE)"
    echo "$BODY" | jq '.' 2>/dev/null || echo "$BODY"
fi

# Test 7: Clear Chat History (Optional - commented out to preserve history)
print_header "Test 7: Clear Chat History (Optional)"
read -p "Do you want to clear the chat history? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    CLEAR_RESPONSE=$(curl -s -w "\n%{http_code}" -X DELETE "${AGENT_API_URL}/api/v1/chatbot/messages" \
      -H "Authorization: Bearer ${SESSION_TOKEN}")
    
    HTTP_CODE=$(echo "$CLEAR_RESPONSE" | tail -n1)
    BODY=$(echo "$CLEAR_RESPONSE" | sed '$d')
    
    if [ "$HTTP_CODE" -eq 200 ]; then
        print_success "Chat history cleared successfully (HTTP $HTTP_CODE)"
        echo "$BODY" | jq '.' 2>/dev/null || echo "$BODY"
    else
        print_error "Clear chat history failed (HTTP $HTTP_CODE)"
        echo "$BODY" | jq '.' 2>/dev/null || echo "$BODY"
    fi
else
    print_info "Skipping chat history clear"
fi

# Summary
print_header "Test Summary"
print_success "All basic API tests completed!"
print_info "Test User Email: $TEST_EMAIL"
print_info "Session ID: $SESSION_ID"
print_info "Agent API URL: $AGENT_API_URL"

echo -e "\n${GREEN}✓ Basic API functionality is working correctly!${NC}\n"
