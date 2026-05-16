# Testing Guide - Basic Usage with curl

This guide provides curl commands to test the basic functionality of the enrollment assistant APIs.

## Prerequisites - Environment Setup

Before testing, ensure the required environment variables are set. The `agent_api` container requires:

1. **OPENAI_API_KEY** - Your OpenAI API key
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

- **Agent API (EC2, Docker default)**: port **8000** — not port 80. Set a base URL that includes the port, for example:
  ```bash
  export EC2_IP=http://35.93.133.15:8000
  ```
  If you use only the hostname or IP without `:8000`, curl uses **port 80** and you will see `Failed to connect ... port 80`.
- **Agent API (local compose)**: `http://localhost:8000`
- **RAG API**: `http://localhost:8010` (default)
- **PostgreSQL**: `localhost:55432` (default)

Ensure the EC2 **security group** allows inbound **TCP 8000** (and **8010** if you hit RAG from your machine) from your IP or VPN.

## 1. Health Checks

### Agent API Health Check
```bash
curl $EC2_IP/health
```

### RAG API Health Check
```bash
curl http://localhost:8010/health
```

## 2. Agent API - Authentication Flow

### Register a New User
```bash
curl -X POST $EC2_IP/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "Test1234!"
  }'
```

**Response**: Returns user info with a token. Save the `token.access_token` for subsequent requests.

### Login (Alternative to Register)
```bash
curl -X POST $EC2_IP/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=Test1234!&grant_type=password"
```

**Response**: Returns `access_token`. Save this token.

### Create a Chat Session
```bash
# Replace YOUR_USER_TOKEN with the token from register/login
curl -X POST $EC2_IP/api/v1/auth/session \
  -H "Authorization: Bearer YOUR_USER_TOKEN"
```

**Response**: Returns a session with `session_id` and `token.access_token`. Save the session token for chat requests.

## 3. Agent API - Chat Endpoints

### Send a Chat Message
```bash
# Replace YOUR_SESSION_TOKEN with the session token from step 2
curl -X POST $EC2_IP/api/v1/chatbot/chat \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
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
curl -X GET $EC2_IP/api/v1/chatbot/messages \
  -H "Authorization: Bearer YOUR_SESSION_TOKEN"
```

### Clear Chat History
```bash
curl -X DELETE $EC2_IP/api/v1/chatbot/messages \
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
Login

ACCESS_TOKEN="$(
  curl -sS -X POST $EC2_IP/api/v1/auth/login \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d 'username=test@example.com&password=Test1234!&grant_type=password' \
  | jq -r .access_token
)"
echo "access_token_is_null=$([ -z \"$ACCESS_TOKEN\" ] && echo true || echo false)"

Create session

SESSION_TOKEN="$(
  curl -sS -X POST $EC2_IP/api/v1/auth/session \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
  | jq -r .token.access_token
)"

Call chatbot

curl -sS -X POST $EC2_IP/api/v1/chatbot/chat \
  -H "Authorization: Bearer $SESSION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Hello, can you help me with enrollment?"}]}' | jq .

# 4. Get chat history
curl -X GET $EC2_IP/api/v1/chatbot/messages \
  -H "Authorization: Bearer $SESSION_TOKEN"
```

## 6. Interactive API Documentation

Both APIs provide interactive documentation:

- **Agent API Swagger UI**: $EC2_IP/docs
- **Agent API ReDoc**: $EC2_IP/redoc
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
