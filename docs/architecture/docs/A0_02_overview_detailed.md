# A0_02 Overview Detailed

**Diagram Files:**
- Simple: `00_overview/A0_01_overview_simplified.puml`
- Detailed: `00_overview/A0_02_overview_detailed.puml`
- Enrollment Focus: `00_overview/A0_03_overview_enrollment_assistance.puml`

---

## Purpose

The overview diagrams provide high-level architecture views of the entire SJSU Enrollment Assistance system. They show all layers, services, and their interactions.

---

## Minimal view (A0_00)

**When to use:** One-slide or executive summary; no internal service names.

**Shows:** Clients → load balancer → backend blob → Postgres/Neo4j → OpenAI.

---

## Simplified view (A0_01)

**When to use:** Quick understanding, presentations, stakeholder overview

**Shows:**
- Three layers: Client, Service, Knowledge/Data
- **Implemented** services: Agent (`agent_ai`), RAG API (`rag_api`), Prerequisite gateway (`rag_graph`)
- **Planned** service: Enrollment microservice (diagrams show target behavior)
- Storage: Postgres (app + vectors), Neo4j (curriculum via `rag_graph` only in current code)
- External: OpenAI, observability (Prometheus, Grafana, Langfuse, etc.)

**Key Features:**
- Minimal detail, maximum clarity
- Easy to understand at a glance
- Shows service-to-service interactions

---

## Detailed View (A0_02)

**When to Use:** Implementation planning, detailed architecture review

**Shows:**
- Complete component breakdown
- Individual API endpoints
- Internal service components
- Detailed data flows
- All external integrations

**Key Components:**

### Agent Service
- Auth & Session API (`/api/v1/auth/*`)
- Chatbot API (`/api/v1/chatbot/*`)
- Document Proxy API (`/api/v1/documents/*`)
- LangGraph Agent (orchestration)
- Metrics & Tracing

### RAG API (`rag_api`)
- Upload and chunking (`/embed`, `/embed-upload`, …)
- Vector search (`/query`, `/query_multiple`, …)
- Security middleware (JWT validation)
- Async workers; **no Neo4j driver** in this service

### Prerequisite gateway (`rag_graph`)
- HTTP: `/prereqs`, `/program`, `/health`
- Neo4j read-only access for curated curriculum data

### Enrollment Service (planned)
- Degree Audit Engine
- Scenario Comparison Engine
- Schedule Optimization Engine
- Transfer Equivalency Engine
- Budget Calculator

### Data Layer
- Postgres: Application Data, Enrollment Domain Data, Financial Data, Vector Store
- Neo4j: Prerequisites Graph, Requirements Graph, Transfer Equivalencies, Course Relationships

---

## Enrollment Focus View (A0_03)

**When to Use:** Enrollment assistance specific discussions

**Shows:**
- External data sources (SJSU SIS, Financial Systems, Transfer Center)
- Enrollment-specific data flows
- Focus on enrollment capabilities

**Key Features:**
- Shows ETL pipelines from external systems
- Enrollment Service capabilities highlighted
- Data integration points

---

## Data Flows

### Edge (production)
- **Load balancer** — TLS, health checks, traffic distribution; forwards to Agent `/api/v1/*`

### Client to service
- Web UI / mobile / API clients → load balancer → Agent Service (chat, auth, document proxy)

### Service to service
- Agent → `rag_api` (`rag_search` tool, document proxy)
- Agent → `rag_graph` (`course_prereqs`, `program_requirements` tools)
- Enrollment → RAG (context retrieval): **planned**

### Service to storage
- Agent Service → Postgres (sessions, checkpoints)
- RAG API → Postgres (vectors)
- `rag_graph` → Neo4j (curriculum graph)
- Enrollment Service → Postgres / Neo4j: **planned**

### External
- Agent Service → OpenAI (LLM)
- RAG Service → OpenAI (embeddings)
- All Services → Observability (metrics, traces)

---

## Key Differences

| Aspect | Simple | Detailed |
|--------|--------|----------|
| Components | 3 services as boxes | Individual APIs and engines |
| Data Storage | High-level categories | Specific data types and tables |
| Connections | Main flows only | All connections shown |
| External Systems | Basic list | Detailed integrations |
| Use Case | Quick reference | Implementation guide |

---

## Related Diagrams

- **Service Details:** `02_service/A2_layer_service_microservices.png`
- **Component Details:** `02_service/{service}/A2_XX_component_{service}_*.png`
- **Data Details:** `03_knowledge/A3_layer_knowledge_data_*.png`
- **Flows:** `04_flows/A4_00_flow_overview_*.png`




