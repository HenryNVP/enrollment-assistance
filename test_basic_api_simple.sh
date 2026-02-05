#!/bin/bash

# Simple Basic API Test Script for Enrollment Assistant Agent API
# Quick test without interactive prompts

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

AGENT_API_URL="${AGENT_API_URL:-http://localhost:8000}"
TEST_EMAIL="test$(date +%s)@example.com"
TEST_PASSWORD="Test1234!"

echo -e "${BLUE}Testing Agent API: ${AGENT_API_URL}${NC}\n"

# 1. Health Check
echo "1. Health Check..."
HEALTH=$(curl -s "${AGENT_API_URL}/health")
if echo "$HEALTH" | grep -q "healthy"; then
    echo -e "${GREEN}✓ Health check passed${NC}"
else
    echo -e "${RED}✗ Health check failed${NC}"
    exit 1
fi

# 2. Register User
echo "2. Registering user..."
REGISTER=$(curl -s -X POST "${AGENT_API_URL}/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"${TEST_EMAIL}\",\"password\":\"${TEST_PASSWORD}\"}")

if echo "$REGISTER" | grep -q "access_token"; then
    USER_TOKEN=$(echo "$REGISTER" | jq -r '.token.access_token')
    echo -e "${GREEN}✓ User registered${NC}"
elif echo "$REGISTER" | grep -q "already"; then
    echo "User exists, logging in..."
    LOGIN=$(curl -s -X POST "${AGENT_API_URL}/api/v1/auth/login" \
      -H "Content-Type: application/x-www-form-urlencoded" \
      -d "username=${TEST_EMAIL}&password=${TEST_PASSWORD}&grant_type=password")
    USER_TOKEN=$(echo "$LOGIN" | jq -r '.access_token')
    echo -e "${GREEN}✓ User logged in${NC}"
else
    echo -e "${RED}✗ Registration failed${NC}"
    echo "$REGISTER" | jq '.' 2>/dev/null || echo "$REGISTER"
    exit 1
fi

# 3. Create Session
echo "3. Creating session..."
SESSION=$(curl -s -X POST "${AGENT_API_URL}/api/v1/auth/session" \
  -H "Authorization: Bearer ${USER_TOKEN}")
SESSION_TOKEN=$(echo "$SESSION" | jq -r '.token.access_token')
if [ "$SESSION_TOKEN" != "null" ] && [ -n "$SESSION_TOKEN" ]; then
    echo -e "${GREEN}✓ Session created${NC}"
else
    echo -e "${RED}✗ Session creation failed${NC}"
    exit 1
fi

# 4. Send Chat Message
echo "4. Sending chat message..."
CHAT=$(curl -s -X POST "${AGENT_API_URL}/api/v1/chatbot/chat" \
  -H "Authorization: Bearer ${SESSION_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Hello! Can you help me?"}]}')

if echo "$CHAT" | grep -q "messages"; then
    echo -e "${GREEN}✓ Chat message sent${NC}"
    ASSISTANT_MSG=$(echo "$CHAT" | jq -r '.messages[-1].content' 2>/dev/null)
    if [ -n "$ASSISTANT_MSG" ] && [ "$ASSISTANT_MSG" != "null" ]; then
        echo "   Assistant: ${ASSISTANT_MSG:0:100}..."
    fi
else
    echo -e "${RED}✗ Chat failed${NC}"
    echo "$CHAT" | jq '.' 2>/dev/null || echo "$CHAT"
    exit 1
fi

# 5. Get History
echo "5. Getting chat history..."
HISTORY=$(curl -s -X GET "${AGENT_API_URL}/api/v1/chatbot/messages" \
  -H "Authorization: Bearer ${SESSION_TOKEN}")
MSG_COUNT=$(echo "$HISTORY" | jq '.messages | length' 2>/dev/null || echo "0")
if [ "$MSG_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✓ Retrieved ${MSG_COUNT} messages${NC}"
else
    echo -e "${RED}✗ Failed to get history${NC}"
fi

echo -e "\n${GREEN}All basic tests passed!${NC}"
