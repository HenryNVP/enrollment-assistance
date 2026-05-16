# Architecture Graph Explanations (Simple)

This document gives a plain-language explanation of each graph in `docs/architecture`.

- One entry covers the same graph topic even when there are both **simple** and **detailed** versions.
- For example: `A2_01_*_simple` and `A2_01_*_detailed` share one explanation below.

---

## Layer 0: Overviews

### `A0_00_overview_minimal`
The smallest possible picture of the system.

What it explains:
- Who uses the platform (students/staff and campus systems)
- That the platform depends on university data and AI services
- The value path at a business level (question in, guidance out)

What it intentionally hides:
- Service names (`agent_ai`, `rag_api`, `rag_graph`)
- Network or deployment details (ports, load balancer, storage engines)
- Internal processing steps

### `A0_01_overview_simplified`
A high-level technical map of the running platform.

Components shown:
- Client: React web app
- Edge: load balancer (optional in dev; clients may hit Agent directly)
- Core services: Agent, `rag_api`, `rag_graph`
- Storage: Postgres/pgvector and Neo4j
- External dependencies: OpenAI + observability

Main idea:
- Public traffic enters through edge, then flows to Agent.
- Agent orchestrates RAG and graph lookups.
- Data and AI providers are consumed behind the service layer.

### `A0_02_overview_detailed`
A full top-level architecture map for implementation and review.

Component detail includes:
- API-level surfaces (`/auth`, `/chatbot`, `/documents`, `/query`, `/prereqs`, `/program`)
- Service internals (LangGraph, workers, middleware)
- Data boundaries (application state vs vector store vs graph store)
- Cross-service request paths and planned extensions

Use this when:
- You need to trace one end-to-end request
- You are validating service ownership boundaries
- You are checking whether a new feature belongs in Agent, `rag_api`, or `rag_graph`

### `A0_03_overview_enrollment_assistance`
An enrollment-focused architecture lens.

What it emphasizes:
- Enrollment-specific outcomes (audit, planning, transfer, budget)
- Source systems feeding enrollment data (SIS, finance, transfer)
- Where those inputs are consumed in runtime flows

Why this graph exists:
- To keep product/domain conversations focused on enrollment workflows
- To separate enrollment roadmap discussion from lower-level infra detail

---

## Layer 1: Client

### `A1_layer_client`
Shows the entry surface and request path from user-facing channels.

Component responsibilities:
- React app: session state, chat UX, upload UX
- External clients: programmatic API consumers
- Edge: traffic control and policy checks before backend entry
- Agent API endpoints: primary backend contract for client-facing actions

Typical use:
- Clarifying who can call what
- Reviewing public vs internal API boundaries

---

## Layer 2: Services

### `A2_layer_service_microservices`
Service topology and dependency map.

Per-service role summary:
- Agent: orchestration, conversation state, tool invocation
- `rag_api`: document ingestion + vector retrieval
- `rag_graph`: structured curriculum graph reads
- Enrollment service (planned): future domain engines

It answers:
- Which service calls which
- Which store each service owns/uses
- What is implemented now vs planned

### `A2_01_component_agent_service` (simple + detailed)
Deep view of the Agent service as the orchestration core.

Key components:
- API controllers for auth/chat/doc proxy
- Middleware for cross-cutting concerns (auth/rate limit/CORS/logging)
- LangGraph orchestrator for intent + tool routing
- Session and memory/state persistence in Postgres
- Outbound integrations: `rag_api`, `rag_graph`, OpenAI, observability

What to verify in this graph:
- Whether a feature belongs in API layer vs graph/tool layer
- Whether state should be persisted in checkpoints vs request-time context
- Where failures/retries/timeouts should be handled

### `A2_02_component_rag_service` (simple + detailed)
Deep view of `rag_api` as the vector RAG pipeline.

Pipeline stages:
- Ingestion: load, extract, clean, chunk
- Embedding: call embedding provider, batch/process
- Storage: persist chunks + vectors (pgvector by default)
- Query: vector search and result assembly

Boundaries:
- Owns vector/document retrieval concerns
- Does not own curriculum graph query logic (that is `rag_graph`)

### `A2_03_component_rag_graph` (simple + detailed)
Deep view of `rag_graph` as a focused graph-read gateway.

Key components:
- HTTP endpoints (`/health`, `/prereqs`, `/program`)
- Input normalization and curated query functions
- Neo4j driver/session lifecycle

Why separate service:
- Keeps graph query semantics independent from vector RAG concerns
- Gives Agent stable, structured curriculum responses
- Makes graph-specific scaling/observability easier

### `A2_04_component_enrollment_service` (simple + detailed, planned)
Target design for the future enrollment domain engine.

Planned engines:
- Degree audit and requirement matching
- Scenario comparison and schedule optimization
- Transfer equivalency checks
- Budget and deadline-related calculations

Current status:
- Diagram is design guidance only; no runtime service package in repo yet

---

## Layer 3: Knowledge/Data

### `A3_layer_knowledge_data` (simple + detailed)
Storage ownership and usage matrix.

What it separates:
- Relational application/domain data in Postgres
- Vector search artifacts in pgvector
- Curriculum relationships in Neo4j

Why it matters:
- Prevents accidental overlap of data responsibilities
- Clarifies backup, migration, and performance tuning boundaries

### `A3_01_component_neo4j_graph` (simple + detailed)
Neo4j model and query behavior reference.

Focus areas:
- Node/edge concepts for curriculum structures
- Query intents (prerequisite traversal, program decomposition)
- Integration path through `rag_graph`

Use this when:
- Updating graph schema/loader logic
- Debugging unexpected prerequisite/program answers

### `A3_02_component_enrollment_database` (simple + detailed)
Domain-oriented relational model for enrollment operations.

Main data groups:
- Academic catalog/structure
- Requirement definitions
- Enrollment/scheduling state
- Financial/tuition/cost structures
- Transfer mapping data
- People and accessibility context

Use this when:
- Defining enrollment API inputs/outputs
- Validating where new enrollment attributes belong

### `A3_03_component_enrollment_database_detailed`
The most schema-oriented enrollment DB diagram.

Intended audience:
- Engineers doing SQL modeling, migrations, ETL mapping, or analytics planning

Practical use:
- Table-level impact analysis before changing enrollment-domain contracts

---

## Layer 4: Runtime Flows

### `A4_00_flow_overview` (simple + detailed)
**Session setup:** The student logs in or asks for a session; the Agent writes session state to Postgres and returns a token to the browser. That token rides along on later calls so the Agent can load the right user and thread before doing any work. **Chat:** The student sends a question. The Agent may call `rag_api`, which runs similarity search over pgvector-backed chunks and returns ranked passages; it may call `rag_graph`, which executes Cypher on Neo4j and returns JSON for prerequisites or whole-program structure. Those outputs are folded into the orchestrator’s prompt (along with tool routing and the LLM), and the composed answer flows back to the student. Dashed **planned** arrows show a future Enrollment service that would also read Postgres and Neo4j for audits and similar jobs—the overview marks where that parallel path would attach.

**Document upload:** The student uploads a file; the UI forwards it to the Agent, which passes it to `rag_api` for ingest; vectors land in Postgres and an acknowledgment returns through the Agent to the UI. The **detailed** diagram spells out finer steps—portal → Agent API → LangGraph, document proxy → embed/query endpoints, optional streaming chat, checkpoint writes, observability—so one can read the diagram top-to-bottom as time order: establish identity, optionally ingest, then loop on chat turns with optional RAG, optional graph tools, optional enrollment calls, LLM generation, persist state, emit telemetry.

### `A4_01_flow_ingestion`
The user chooses a document in the Web UI; the UI POSTs it to the Agent, which immediately relays the bytes to the RAG service so ingestion shares the same authenticated edge as chat. Inside RAG the pipeline runs in sequence: open the file, extract raw text, normalize it, split into chunks—only then does the service call OpenAI to embed each chunk, run entity extraction over the text, and commit rows for chunks, embedding vectors, and entities into storage.

If those writes succeed, RAG signals success upstream to the Agent, which responds to the UI and the UI tells the user processing finished. This path does not answer a question in natural language; it only prepares retrievable material so a **later** chat request can hit `rag_api`’s query endpoint and surface those chunks.

### `A4_02_flow_session_auth`
**Guest:** On first load the UI requests a session from the Agent; the Agent creates a guest user and session row in the database, receives identifiers back, and returns a JWT that the browser stores locally. **Login:** The user submits credentials; the Agent validates them against the database, opens a new session on success, and issues another JWT—typically replacing the anonymous credential.

**Authenticated use:** Each subsequent API call from the UI includes that JWT in headers; the Agent resolves it to an active session row before executing chat, uploads, or history endpoints. **Logout:** The client sends a logout request with the same token; the Agent deletes the session record, returns OK, and the UI clears the stored JWT so the next interaction starts clean unless the user signs in or creates a guest session again.

### `A4_03_flow_chat`
For one turn the user types in the UI; the client sends the message plus JWT to the Agent and requests a streamed response. The Agent asks RAG for relevant chunks (vector search), then streams tokens from the LLM through to the UI in a tight loop—each chunk of text appears as it is generated. After the stream completes, the Agent saves the user message and assistant reply to storage so the thread remains durable across refreshes.

When the user opens **history**, the UI fetches messages from the Agent, which reads them from storage and returns the ordered conversation. **Clear history** issues a delete: the Agent wipes persisted messages for that thread while leaving the session itself intact, so the user keeps logging in but starts an empty transcript.

### `A4_04_flow_enrollment` (simple + detailed, planned)
For **degree audit**, the student’s question goes Agent → Enrollment service: Enrollment loads completed coursework from Postgres, reads major requirements from Neo4j, matches courses to rules, computes progress, and returns a structured audit that the Agent turns into a summary. **Scenario comparison** follows the same spine—Agent hands constraints and scenario labels to Enrollment, which pulls schedule and cost inputs from Postgres, checks prerequisite feasibility against Neo4j, builds competing timelines or loads, and ships back a matrix the Agent can narrate.

**Transfer** flows add a lookup in relational transfer tables plus an equivalency walk in Neo4j; the detailed diagram also pulls policy snippets via RAG before answering whether an external course maps to an SJSU requirement. Schedule optimization and budget calculation reuse that pattern: Enrollment aggregates authoritative numbers from Postgres, structural constraints from Neo4j, sometimes policy text from RAG, then returns ranked schedules or cost breakdowns while the Agent stays a thin conversational layer. These sequences describe **intended** end-state wiring; the live product may implement only parts of this today.

---

## Quick "Which graph should I open?"

- Need a non-technical overview: `A0_00`
- Need one-slide technical overview: `A0_01`
- Need full architecture map: `A0_02`
- Need service internals: `A2_01` / `A2_02` / `A2_03`
- Need storage model: `A3_layer`, `A3_01`, `A3_02`
- Need runtime behavior: `A4_00` then `A4_01`/`A4_02`/`A4_03`
