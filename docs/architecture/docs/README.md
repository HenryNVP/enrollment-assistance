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
| `A0_01_overview_simplified` | **Simplified system overview** - Best starting point, shows major layers |
| `A0_02_overview_detailed` | **Detailed architecture** - Complete system view with all components |

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
| `A2_layer_service_microservices` | **Microservices Overview** - Compact view of all 3 services |
| `A2_01_component_agent_service` | **Agent Service Detail** - LangGraph orchestration, APIs, enrollment tools |
| `A2_02_component_rag_service` | **RAG Service Detail** - Policy document processing, vector + graph storage |
| `A2_04_component_enrollment_service` | **Enrollment Service Detail** - Degree audits, scenario comparisons, schedule optimization |

---

### 🔷 Layer 3: Knowledge/Data Layer
**Storage components only** - No processing logic, just data storage.

| File | Description |
|------|-------------|
| `A3_layer_knowledge_data` | **Storage Overview** - Postgres (relational + vector) + Neo4j (graph) |
| `A3_01_component_neo4j_graph` | **Neo4j Knowledge Graph** - Graph schema, operations, queries |
| `A3_02_component_enrollment_database` | **Enrollment Database** - Domain data schema for enrollment assistance |

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

### 📍 **"I want to understand the overall system"**
→ Start with: `A0_01_overview_simplified`

### 📍 **"I need to see all components and connections"**
→ Look at: `A0_02_overview_detailed`

### 📍 **"I'm implementing the microservices"**
→ Start: `A2_layer_service_microservices` (overview)
→ Then: `A2_01` (Agent), `A2_02` (RAG), `A2_04` (Enrollment)

### 📍 **"I'm working on document processing"**
→ Flow: `A4_01_flow_ingestion_pipeline` (shows RAG Service processing)
→ Storage: `A3_layer_knowledge_data` (shows where data is stored)

### 📍 **"I need to understand the knowledge graph"**
→ See: `A3_01_component_neo4j_graph`

### 📍 **"I need to understand university data structure"**
→ See: `A3_02_component_university_database`

### 📍 **"I want to trace user request flows"**
→ **Quick reference** (simplified):
  - **Login**: `A4_02_flow_session_auth`
  - **Chat**: `A4_03_flow_chat` (sync, stream, history)
  - **Document Upload**: `A4_01_flow_ingestion`
  - **Enrollment**: `A4_04_flow_enrollment` (degree audit, scenario comparison, schedule optimization)
→ **Detailed reference**: `A4_00_flow_overview` (all flows combined)
→ **Very detailed**: See `_detailed_backup/` folder

---

## 🏗️ Architecture Layers

```
┌─────────────────────────────────────────┐
│   Layer 1: Client Layer                 │  Web UI, External Consumers
├─────────────────────────────────────────┤
│   Layer 2: Service Layer                │  Microservices:
│   ├─ A2_01: Agent Service (8000)        │  - Main orchestration
│   ├─ A2_02: RAG Service (8080)          │  - Policy document processing  
│   └─ A2_04: Enrollment Service (8090)   │  - Enrollment assistance
├─────────────────────────────────────────┤
│   Layer 3: Knowledge/Data Layer         │  Storage Only:
│   ├─ Postgres (relational + vector)     │  - App data, domain data
│   │  ├─ A3_02: University Database      │  - Vector embeddings
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
  A0_01           = Overview level (simplified)
  A0_02           = Overview level (detailed)
  A1              = Client layer
  A2              = Service layer
  A2_01           = Component within service layer (Agent service)
  A2_02           = Component within service layer (RAG service)
  A2_03           = Component within service layer (Analysis service)
  A3              = Knowledge/data layer (storage only)
  A3_01           = Component: Neo4j Knowledge Graph
  A3_02           = Component: University Database
  A4              = Flows & sequences (how services work)
  A4_01           = Flow: RAG Service ingestion pipeline
```

### Categories in Names:
- **overview** - High-level system views (A0_01, A0_02)
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
- **Agent Service**: FastAPI, LangGraph, SQLModel
- **RAG Service**: FastAPI, LangChain, pgvector, Neo4j
- **Enrollment Service**: FastAPI, Postgres, Neo4j

### Data Storage
- **Postgres + pgvector**: Vector embeddings, sessions, state
- **Neo4j**: Knowledge graph (entities, relationships)
- **Redis**: Task queue, caching

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

## 📚 Related Documentation

- `/MICROSERVICES_OVERVIEW.md` - Detailed microservices documentation
- `/README.md` - Project README
- `/backend/services/agent_ai/README.md` - Agent service documentation
- `/backend/services/rag_api/README.md` - RAG service documentation

---

## 🏆 Best Practices

1. **Start High-Level** - Begin with overview diagrams
2. **Drill Down** - Move to layer and component details
3. **Follow Sequences** - Use sequence diagrams to understand flows
4. **Cross-Reference** - Use multiple diagrams for complete understanding
5. **Keep Updated** - Update diagrams when architecture changes

---

**Last Updated**: 2025-01-27
**Architecture Version**: 1.0
**Maintained By**: SAM-E Enrollment Assistance Team
