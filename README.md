# SAM-E: Enrollment Assistant

**SAM-E** is an AI-powered enrollment assistance tool specialized for San Jose State University (SJSU). The system helps students with enrollment decisions, budgeting, scheduling, multi-term planning, degree audits, and scenario comparisons through an intelligent conversational interface.


## Key Capabilities

- **Enrollment Questions**: Course availability, deadlines, prerequisites, capacity limits
- **Degree Audits**: Progress tracking by major, minor, and concentration
- **Budget Planning**: Tuition, fees, books, housing, and commuting cost calculations
- **Schedule Optimization**: Optimal course scheduling with conflict detection
- **Transfer Assistance**: Course equivalency lookups and transfer policy information
- **Scenario Comparisons**: Full-time vs. part-time enrollment, delivery mode comparisons

## Architecture

SAM-E follows a **microservices architecture** with three core services:

1. **Agent Service** (Port 8000) - LangGraph-powered conversational interface
2. **RAG Service** (Port 8010) - Policy document processing and knowledge retrieval
3. **Enrollment Service** (Port 8090) - Enrollment domain logic and assistance engines *(planned)*

## Repository Structure

```
SAM-E/
├── backend/                    # Backend microservices
│   ├── services/              # Individual services
│   │   ├── agent_ai/          # Agent Service (port 8000)
│   │   └── rag_api/           # RAG Service (port 8010)
│   └── shared/                # Shared backend code (future)
│
├── docs/                       # All documentation
│   ├── architecture/         # Architecture diagrams
│   ├── design/                # Design specifications
│   ├── guides/                # User guides
│   ├── REPO_ORGANIZATION.md   # Collaboration guide
│   ├── CONTRIBUTING.md        # Contribution guidelines
│   └── README.md              # Documentation index
│
├── infrastructure/             # Infrastructure configs
│   └── docker/
│       └── docker_compose.yml # Docker Compose for all services
│
└── .github/                    # GitHub templates & workflows
```

## Running the System

```bash
# Start all services
docker compose -f infrastructure/docker/docker_compose.yml up --build

# Or start individual services
cd backend/services/agent_ai
docker compose up
```

## Key Directories

| Directory | Purpose |
|-----------|---------|
| `backend/services/` | Backend microservices code |
| `backend/shared/` | Shared backend utilities (future) |
| `docs/guides/` | User-facing documentation |
| `docs/design/` | Architecture and design specs |
| `docs/architecture/` | Architecture diagrams |
| `infrastructure/docker/` | Docker Compose configurations |

## Credits
This project builds on the following upstream open-source repositories:
- [`danny-avila/rag_api`](https://github.com/danny-avila/rag_api)
- [`wassim249/fastapi-langgraph-agent-production-ready-template`](https://github.com/wassim249/fastapi-langgraph-agent-production-ready-template)

