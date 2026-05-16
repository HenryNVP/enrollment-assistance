# Architecture Diagrams

This directory contains the architecture documentation for SAM-E (Strategic Planning Assistant for Enrollment), an enrollment assistance system for San Jose State University, organized hierarchically for easy navigation.

## 📁 Diagram Organization

Files use a hierarchical numbering system:
- **x** = Layer number (0, 1, 2, 3, etc.)
- **x_yy** = Component within that layer

### 🌐 High-Level Overview (Layer 0)
Start here to understand the overall system architecture.

| File | Description |
|------|-------------|
| `A0_00_overview_minimal` | **Minimal one-screen overview** — users & campus systems → platform → data & AI |
| `A0_01_overview_simplified` | **Simplified system overview** — layers + **load balancer** in front of Agent |
| `A0_02_overview_detailed` | **Detailed architecture** — clients, edge (load balancer), services, storage |

---

### 🔷 Layer 1: Client Layer
User-facing components and external integrations.

| File | Description |
|------|-------------|
| `A1_layer_client` | **Client Layer** - User interfaces, web dashboard, external integrations |

---

### 🔷 Layer 2: Service Layer (Microservices)
Core business logic microservices - one overview + details for each service.

| File | Description |
|------|-------------|
| `A2_layer_service_microservices` | **Microservices overview** — agent, `rag_api`, `rag_graph`, planned enrollment |
| `A2_01_component_agent_service` | **Agent service** — LangGraph, APIs, tools (`rag_search`, prereqs/program, web) |
| `A2_02_component_rag_service` | **RAG API (`rag_api`)** — ingest + vector search (pgvector / optional Mongo); **no Neo4j** |
| `A2_03_component_rag_graph` | **Prerequisite gateway** — `rag_graph` → Neo4j (`/prereqs`, `/program`) |
| `A2_04_component_enrollment_service` | **Enrollment service (target)** — not implemented in repo; design diagrams only |

---

### 🔷 Layer 3: Knowledge/Data Layer
**Storage components only** - No processing logic, just data storage.

| File | Description |
|------|-------------|
| `A3_layer_knowledge_data` | **Storage Overview** - Postgres (relational + vector) + Neo4j (graph) |
| `A3_01_component_neo4j_graph` | **Neo4j Knowledge Graph** - Graph schema, operations, queries |
| `A3_02_component_enrollment_database` | **Enrollment / domain DB (Postgres)** — target schema; vectors live in same Postgres for `rag_api` |

---

### 🔄 Layer 4: Flows & Sequences
**Runtime flows** - Simplified view of how services interact.

| File | Description |
|------|-------------|
| `A4_00_flow_overview` | **Overview** - All flows combined (detailed reference) |
| `A4_01_flow_ingestion` | **Document Upload** - User → RAG → Storage |
| `A4_02_flow_session_auth` | **Session & Auth** - Login, JWT, logout |
| `A4_03_flow_chat` | **Chat** - Sync, streaming, & history (all-in-one) |
| `A4_04_flow_analysis` | **Analysis** - Strategic workflow execution |

---

## 🎯 Quick Navigation Guide

### 📍 **"I want the smallest possible picture"**
→ Start with: `A0_00_overview_minimal`

### 📍 **"I want to understand the overall system"**
→ Then: `A0_01_overview_simplified` (adds edge: load balancer → Agent)

### 📍 **"I need to see all components and connections"**
→ Look at: `A0_02_overview_detailed`

### 📍 **"I'm implementing the microservices"**
→ Start: `A2_layer_service_microservices` (overview)  
→ Then: `A2_01` (agent), `A2_02` (`rag_api`), `A2_03` (`rag_graph`), `A2_04` (enrollment — planned)

### 📍 **"I'm working on document processing"**
→ Flow: `A4_01_flow_ingestion` (RAG API processing)
→ Storage: `A3_layer_knowledge_data` (shows where data is stored)

### 📍 **"I need to understand the knowledge graph"**
→ See: `A3_01_component_neo4j_graph`

### 📍 **"I need to understand Postgres / domain data layout"**
→ See: `A3_02_component_enrollment_database`

### 📍 **"I want to trace user request flows"**
→ **Quick reference** (simplified):
  - **Login**: `A4_02_flow_session_auth`
  - **Chat**: `A4_03_flow_chat` (sync, stream, history)
  - **Document Upload**: `A4_01_flow_ingestion`
  - **Enrollment (target)**: `A4_04_flow_enrollment` (future degree audit, scenarios, scheduling)
→ **Detailed reference**: `A4_00_flow_overview` (all flows combined)
→ **Very detailed**: See `_detailed_backup/` folder

---

## 🏗️ Architecture Layers

```
┌─────────────────────────────────────────┐
│   Edge (often drawn above Layer 1)      │  Load balancer → Agent
├─────────────────────────────────────────┤
│   Layer 1: Client Layer                 │  Web UI, External Consumers
├─────────────────────────────────────────┤
│   Layer 2: Service Layer                │  Runtimes in repo:
│   ├─ A2_01: Agent (8000)                │  - LangGraph + tools
│   ├─ A2_02: RAG API (8010 host)         │  - Vectors / ingest
│   ├─ A2_03: rag_graph (8102 host)       │  - Neo4j gateway
│   └─ A2_04: Enrollment (8090)         │  - Planned only
├─────────────────────────────────────────┤
│   Layer 3: Knowledge/Data Layer         │  Storage Only:
│   ├─ Postgres (relational + vector)     │  - App data, domain data
│   │  ├─ A3_02: Enrollment DB (Postgres) │  - Domain + vectors
│   └─ Neo4j (graph)                      │  
│      └─ A3_01: Knowledge Graph          │  - Entity relationships
├─────────────────────────────────────────┤
│   Layer 4: Flows (Simplified)           │  How services work:
│   ├─ A4_01: Document upload             │  - User → Storage
│   ├─ A4_02: Session & auth              │  - Login & JWT
│   ├─ A4_03: Chat                        │  - Sync/stream/history
│   └─ A4_04: Enrollment                  │  - Degree audit, scenarios, scheduling
└─────────────────────────────────────────┘
```

---

## 🛠️ Generating Diagrams

[Download](https://plantuml.com/download) plantuml.jar file and put in architecture/tools.
To regenerate PNG images from PlantUML source files:

```bash
# Generate all diagrams
java -jar plantuml.jar -tpng *.puml

# Generate specific diagram
java -jar plantuml.jar -tpng A0_01_overview_simplified.puml

# Generate high-level diagrams only
java -jar plantuml.jar -tpng A0_*.puml
```

---

## 📋 File Naming Convention

```
Hierarchical numbering:
  Ax              = Layer number (e.g., A1, A2, A3)
  Ax_yy           = Component within that layer
  
Examples:
  A0_00           = Overview level (minimal)
  A0_01           = Overview level (simplified)
  A0_02           = Overview level (detailed)
  A1              = Client layer
  A2              = Service layer
  A2_01           = Component within service layer (Agent service)
  A2_02           = Component: RAG API (rag_api)
  A2_03           = Component: Prerequisite gateway (rag_graph)
  A3              = Knowledge/data layer (storage only)
  A3_01           = Component: Neo4j Knowledge Graph
  A3_02           = Component: Postgres enrollment / domain DB
  A4              = Flows & sequences (how services work)
  A4_01           = Flow: document ingestion (RAG API)
```

### Categories in Names:
- **overview** - High-level system views (A0_00, A0_01, A0_02)
- **layer** - Architectural layer (A1, A2, A3)
- **component** - Specific component within a layer (Ax_yy)
- **sequence** - Runtime sequence diagrams (A4+)

---

## 🎨 Diagram Standards

All diagrams follow these conventions:
- **No colored backgrounds** - Clean, document-ready
- **Black borders (1px)** - Professional appearance
- **Arial font (11pt)** - Readable in documents
- **Clear labels** - Descriptive names and annotations
- **Notes sections** - Key information highlighted

---

## 📊 Technology Stack Shown

### Services
- **Agent (`agent_ai`)**: FastAPI, LangGraph, SQLModel, Postgres
- **RAG API (`rag_api`)**: FastAPI, LangChain loaders, pgvector (default) or Atlas Mongo vectors
- **Prerequisite gateway (`rag_graph`)**: FastAPI, official Neo4j Python driver
- **Enrollment service**: not in repository (design / PlantUML only)

### Data storage
- **Postgres + pgvector**: Agent sessions/checkpoints, RAG chunks and embeddings (same DB in root compose)
- **Neo4j**: Curriculum graph, read via **`rag_graph`** only in current wiring
- **Redis**: Optional / future (not required by the diagrams above to match compose)

### External Services
- **OpenAI**: LLM completions, embeddings
- **Prometheus**: Metrics collection
- **Grafana**: Metrics visualization
- **Langfuse**: LLM tracing

---

## 🔄 Update Process

When updating architecture:
1. Edit the `.puml` source file
2. Regenerate PNG: `java -jar plantuml.jar -tpng [filename].puml`
3. Verify the output looks correct
4. Update this README if adding new diagrams

---

## Related documentation

- [`architecture.md`](architecture.md) — Written architecture (design + repo snapshot)
- [`GRAPH_EXPLANATIONS_SIMPLE.md`](GRAPH_EXPLANATIONS_SIMPLE.md) — Plain-language explanation of every graph
- [`/README.md`](../../../README.md) — Project README
- [`/backend/services/agent_ai/README.md`](../../../backend/services/agent_ai/README.md) — Agent service
- [`/backend/services/rag_api/README.md`](../../../backend/services/rag_api/README.md) — RAG API

---

## Best practices

1. **Start High-Level** - Begin with overview diagrams
2. **Drill Down** - Move to layer and component details
3. **Follow Sequences** - Use sequence diagrams to understand flows
4. **Cross-Reference** - Use multiple diagrams for complete understanding
5. **Keep Updated** - Update diagrams when architecture changes

---

**Last updated:** 2026-04-27  
**Architecture version:** 1.1 (repo-aligned service split: `rag_api` vs `rag_graph`)
