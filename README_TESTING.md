# API Testing Scripts

This directory contains test scripts for the Enrollment Assistant APIs.

## Available Scripts

### 1. `test_basic_api.sh` - Comprehensive Test Script

Full-featured test script with detailed output, error handling, and colored output.

**Features:**
- Health check
- User registration (with fallback to login if user exists)
- Session creation
- Chat message sending
- Chat history retrieval
- Follow-up chat message
- Optional chat history clearing

**Usage:**
```bash
./test_basic_api.sh
```

**Environment Variables:**
```bash
# Override defaults if needed
export AGENT_API_URL=http://localhost:8000
export TEST_EMAIL=myemail@example.com
export TEST_PASSWORD=MyPassword123!
./test_basic_api.sh
```

### 2. `test_basic_api_simple.sh` - Quick Test Script

Simplified version for quick testing without interactive prompts.

**Usage:**
```bash
./test_basic_api_simple.sh
```

**Requirements:**
- `jq` must be installed: `sudo apt-get install jq` or `brew install jq`
- Agent API must be running on `http://localhost:8000` (or set `AGENT_API_URL`)

## What Gets Tested

Both scripts test the following basic Agent API functionality:

1. ✅ **Health Check** - Verifies API is running
2. ✅ **User Registration** - Creates a new user account
3. ✅ **Session Creation** - Creates a chat session
4. ✅ **Chat Messaging** - Sends a message and receives response
5. ✅ **Chat History** - Retrieves conversation history

## Example Output

```
========================================
Test 1: Health Check
========================================

✓ Health check passed (HTTP 200)
{
  "status": "healthy",
  "version": "0.0.1",
  "environment": "development",
  "components": {
    "api": "healthy",
    "database": "healthy"
  }
}

========================================
Test 2: Register User
========================================

✓ User registration successful (HTTP 200)
...
```

## Troubleshooting

**Error: "jq: command not found"**
```bash
# Ubuntu/Debian
sudo apt-get install jq

# macOS
brew install jq

# Fedora
sudo dnf install jq
```

**Error: "Connection refused"**
- Make sure the Agent API is running: `docker ps | grep agent_api`
- Check the port: `curl http://localhost:8000/health`

**Error: "User already exists"**
- The script automatically falls back to login if registration fails due to existing user
- Or use a different email by setting `TEST_EMAIL` environment variable

## Next Steps

After basic API tests pass, you can:
- Test RAG API endpoints (document upload, query)
- Test streaming chat endpoint
- Test session management endpoints
- See `TESTING.md` for detailed curl examples
