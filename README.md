# SAM-E: Enrollment Assistant

**SAM-E** is an AI-powered enrollment assistance tool specialized for San Jose State University (SJSU). The system helps students with enrollment decisions, budgeting, scheduling, multi-term planning, degree audits, and scenario comparisons through an intelligent conversational interface.

## Quick Links

### For Users
- **[docs/guides/QUICKSTART_RAG.md](docs/guides/QUICKSTART_RAG.md)** - Quick start guide for minimal RAG system ⚡
- **[docs/guides/QUICKSTART_AGENT.md](docs/guides/QUICKSTART_AGENT.md)** - Quick start guide for Agent AI service 🤖
- **[docs/guides/AGENT_RAG_INTEGRATION.md](docs/guides/AGENT_RAG_INTEGRATION.md)** - How Agent and RAG services work together 🔗
- **[docs/guides/GUIDE.md](docs/guides/GUIDE.md)** - Complete user guide and setup instructions
- **[docs/guides/DOCUMENTATION.md](docs/guides/DOCUMENTATION.md)** - Documentation organization and navigation
- **[docs/design/MICROSERVICES_OVERVIEW.md](docs/design/MICROSERVICES_OVERVIEW.md)** - Architecture overview
- **[docs/design/DESIGN_SPECS_SERVICE_LAYER.md](docs/design/DESIGN_SPECS_SERVICE_LAYER.md)** - Detailed service specifications
- **[docs/architecture/](docs/architecture/)** - Architecture diagrams and documentation

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

See [docs/design/MICROSERVICES_OVERVIEW.md](docs/design/MICROSERVICES_OVERVIEW.md) for detailed architecture information.

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

## Getting Started

- **Quick Start (RAG only)**: See [docs/guides/QUICKSTART_RAG.md](docs/guides/QUICKSTART_RAG.md) for minimal setup
- **Quick Start (Agent only)**: See [docs/guides/QUICKSTART_AGENT.md](docs/guides/QUICKSTART_AGENT.md) for Agent service setup
- **Quick Start (Agent only)**: See [docs/guides/QUICKSTART_AGENT.md](docs/guides/QUICKSTART_AGENT.md) for Agent service setup
- **Full System**: See [docs/guides/GUIDE.md](docs/guides/GUIDE.md) for complete setup and usage instructions

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

