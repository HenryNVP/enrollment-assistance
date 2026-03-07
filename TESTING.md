# Testing Guide - Basic Usage with curl

This guide provides curl commands to test the basic functionality of the enrollment assistant APIs.

## Prerequisites - Environment Setup

Before testing, ensure the required environment variables are set. The `agent_api` container requires:

1. **OPENAI_API_KEY** - Your OpenAI API key (get from https://platform.openai.com/api-keys)
2. **JWT_SECRET_KEY** - A secret key for JWT token signing

### Option 1: Create .env.development file (Recommended)

Create `backend/services/agent_ai/.env.development`:

```bash
# Required
OPENAI_API_KEY=your_openai_api_key_here
JWT_SECRET_KEY=dev-secret-key-change-in-production

# Optional - defaults are fine for testing
APP_ENV=development
DEFAULT_LLM_MODEL=gpt-4o-mini
```

### Option 2: Set Environment Variables

Export variables before running docker compose:

```bash
export OPENAI_API_KEY=your_openai_api_key_here
export JWT_SECRET_KEY=dev-secret-key-change-in-production
docker compose -f infrastructure/docker/docker_compose.yml up db rag_api agent_api --build
```

### Option 3: Pass Variables to docker compose

```bash
OPENAI_API_KEY=your_key JWT_SECRET_KEY=your_secret docker compose -f infrastructure/docker/docker_compose.yml up db rag_api agent_api --build
```

**Note**: The RAG API also needs `OPENAI_API_KEY` if you plan to use embedding features. You can set it in `backend/services/rag_api/.env` or pass it as an environment variable.

## Service Ports

- **Agent API**: `http://localhost:8000` (default)
- **RAG API**: `http://localhost:8010` (default)
- **PostgreSQL**: `localhost:55432` (default)

## 1. Health Checks

### Agent API Health Check
```bash
curl http://localhost:8000/health
```

### RAG API Health Check
```bash
curl http://localhost:8010/health
```

## 2. Agent API - Authentication Flow

### Register a New User
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "Test1234!"
  }'
```

**Response**: Returns user info with a token. Save the `token.access_token` for subsequent requests.

### Login (Alternative to Register)
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=Test1234!&grant_type=password"
```

**Response**: Returns `access_token`. Save this token.

### Create a Chat Session
```bash
# Replace YOUR_USER_TOKEN with the token from register/login
curl -X POST http://localhost:8000/api/v1/auth/session \
  -H "Authorization: Bearer YOUR_USER_TOKEN"
```

**Response**: Returns a session with `session_id` and `token.access_token`. Save the session token for chat requests.

## 3. Agent API - Chat Endpoints

### Send a Chat Message
```bash
# Replace YOUR_SESSION_TOKEN with the session token from step 2
curl -X POST http://localhost:8000/api/v1/chatbot/chat \
  -H "Authorization: Bearer YOUR_SESSION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "Hello, can you help me with enrollment?"
      }
    ]
  }'
```

### Get Chat History
```bash
curl -X GET http://localhost:8000/api/v1/chatbot/messages \
  -H "Authorization: Bearer YOUR_SESSION_TOKEN"
```

### Clear Chat History
```bash
curl -X DELETE http://localhost:8000/api/v1/chatbot/messages \
  -H "Authorization: Bearer YOUR_SESSION_TOKEN"
```

## 4. RAG API - Document Management

### Query Documents (RAG Search)
```bash
curl -X POST http://localhost:8010/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the enrollment requirements?",
    "top_k": 5
  }'
```

### Get All Documents
```bash
curl -X GET http://localhost:8010/documents
```

### Upload and Embed a Document
```bash
# Upload a PDF or text file
curl -X POST http://localhost:8010/embed \
  -F "file_id=test-doc-001" \
  -F "file=@/path/to/your/document.pdf"
```

### Extract Text from File
```bash
curl -X POST http://localhost:8010/text \
  -F "file_id=test-doc-001" \
  -F "file=@/path/to/your/document.pdf"
```

## 5. Complete Example Workflow

Here's a complete workflow from registration to chat:

```bash
# 1. Register a user
REGISTER_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "Test1234!"
  }')

# Extract user token (requires jq)
USER_TOKEN=$(echo $REGISTER_RESPONSE | jq -r '.token.access_token')

# 2. Create a session
SESSION_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/auth/session \
  -H "Authorization: Bearer $USER_TOKEN")

# Extract session token
SESSION_TOKEN=$(echo $SESSION_RESPONSE | jq -r '.token.access_token')

# 3. Send a chat message
curl -X POST http://localhost:8000/api/v1/chatbot/chat \
  -H "Authorization: Bearer $SESSION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "What courses are available for enrollment?"
      }
    ]
  }'

# 4. Get chat history
curl -X GET http://localhost:8000/api/v1/chatbot/messages \
  -H "Authorization: Bearer $SESSION_TOKEN"
```

## 6. Interactive API Documentation

Both APIs provide interactive documentation:

- **Agent API Swagger UI**: http://localhost:8000/docs
- **Agent API ReDoc**: http://localhost:8000/redoc
- **RAG API Swagger UI**: http://localhost:8010/docs (if available)

## 7. Python tests (CI/CD)

API tests are available as pytest scripts so CI can run them without shell scripts.

**Run all API tests** (from repo root; requires Agent API and optionally RAG API running):

```bash
pip install -r tests/requirements.txt
pytest tests/ -v
```

- **Integration** (`tests/integration/`): Agent API (health, register/session, chat, history) and RAG API (health, query, ids, document details). Skip if the service is down; RAG tests expect vector store populated (e.g. via `tools/ingest_rag.py`).
- **E2E** (`tests/e2e/`): RAG query then Agent chat; skip if either service is down.

Set base URLs if not using defaults: `AGENT_API_URL`, `RAG_API_URL`. For RAG tests, `JWT_SECRET` (or `backend/services/rag_api/.env`) is required to generate the RAG token.

## Notes

- Password requirements: At least 8 characters, must include uppercase, lowercase, number, and special character
- All chat endpoints require a valid session token (not user token)
- The RAG API may require `OPENAI_API_KEY` to be set for embedding operations
- Rate limiting may apply to certain endpoints
