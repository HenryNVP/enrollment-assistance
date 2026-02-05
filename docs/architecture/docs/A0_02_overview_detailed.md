# A0_02 Overview Detailed

**Diagram Files:**
- Simple: `00_overview/A0_01_overview_simplified.puml`
- Detailed: `00_overview/A0_02_overview_detailed.puml`
- Enrollment Focus: `00_overview/A0_03_overview_enrollment_assistance.puml`

---

## Purpose

The overview diagrams provide high-level architecture views of the entire SJSU Enrollment Assistance system. They show all layers, services, and their interactions.

---

## Simplified View (A0_01)

**When to Use:** Quick understanding, presentations, stakeholder overview

**Shows:**
- 3 main layers: Client, Service, Knowledge/Data
- 3 microservices: Agent, RAG, Enrollment
- Main data storage: Postgres, Neo4j
- External dependencies: OpenAI, Observability

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

### RAG Service
- Upload & Chunking (`/embed`, `/embed-upload`)
- Vector Search API (`/query`, `/query_multiple`)
- Security Middleware (JWT validation)
- Async Workers

### Enrollment Service
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

### Client to Service
- Web UI → Agent Service (chat, auth)
- Mobile App → Agent Service
- API Clients → Agent Service

### Service to Service
- Agent Service → RAG Service (policy search)
- Agent Service → Enrollment Service (enrollment tools)
- Enrollment Service → RAG Service (context retrieval)

### Service to Storage
- Agent Service → Postgres (sessions, checkpoints)
- RAG Service → Postgres (vectors)
- RAG Service → Neo4j (graph)
- Enrollment Service → Postgres (enrollment data)
- Enrollment Service → Neo4j (prerequisites, requirements)

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




