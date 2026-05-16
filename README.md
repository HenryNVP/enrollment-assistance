# SAM-E: Enrollment Assistant

**SAM-E** is an AI-powered enrollment assistant for San Jose State University. It combines a conversational agent, document retrieval, and a curated prerequisite graph to help answer questions about enrollment, program requirements, schedules, and planning.

![SAM-E enrollment assistant](docs/sam-e.png)

## What It Does

- Answers enrollment and program questions through a FastAPI/LangGraph agent.
- Retrieves policy and program information from a PostgreSQL/pgvector RAG service.
- Looks up curated course prerequisites and program structure from Neo4j.
- Supports document scraping and ingestion for SJSU source material.
- Includes integration and end-to-end tests for the Agent API and RAG API.

## Services

- `backend/services/agent_ai` - main chat and auth API, exposed on port `8000`.
- `backend/services/rag_api` - document ingestion and vector search API.
- `backend/services/rag_graph` - prerequisite/program gateway backed by Neo4j.

## Repository Layout

```text
backend/services/agent_ai/   FastAPI + LangGraph agent service
backend/services/rag_api/    RAG API with PostgreSQL/pgvector storage
backend/services/rag_graph/  Neo4j prerequisite gateway
data/                        Curated curriculum YAML data
docs/architecture/           PlantUML diagrams and architecture notes
infrastructure/              Docker Compose and AWS deployment files
tests/                       Root integration and E2E tests
tools/                       Scraping and RAG ingestion utilities
```

## Quick Start

Run the Agent API locally:

```bash
cd backend/services/agent_ai
cp .env.example .env.development
uv sync
make dev
```

Run the RAG API locally:

```bash
cd backend/services/rag_api
docker compose up --build
```

For EC2-style deployments, see the compose files in `infrastructure/aws/`.

## Testing

Install root test dependencies, then run the top-level tests:

```bash
pip install -r tests/requirements.txt
pytest
```

The root tests default to:

- Agent API: `http://localhost:8000`
- RAG API: `http://localhost:8010`

Override with `AGENT_API_URL` and `RAG_API_URL` when needed. See `TESTING.md` for curl examples and more complete test setup.

## More Docs

- `backend/services/agent_ai/README.md` - agent service setup and evaluation commands.
- `backend/services/rag_api/README.md` - RAG API setup, environment variables, and ingestion behavior.
- `docs/architecture/docs/README.md` - architecture documentation.
- `tools/README.md` - scraper and RAG ingestion utilities.

## Credits

This project builds on:

- [`danny-avila/rag_api`](https://github.com/danny-avila/rag_api)
- [`wassim249/fastapi-langgraph-agent-production-ready-template`](https://github.com/wassim249/fastapi-langgraph-agent-production-ready-template)
