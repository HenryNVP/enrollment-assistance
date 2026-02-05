# A4_00 Flow Overview

**Diagram Files:**
- Simple: `04_flows/A4_00_flow_overview_simple.puml`
- Detailed: `04_flows/A4_00_flow_overview_detailed.puml`

---

## Purpose

The Flow Overview diagrams show all runtime interactions and workflows in the enrollment assistance system. They illustrate how students interact with the system and how services coordinate to provide enrollment assistance.

---

## Simplified View

**When to Use:** Quick understanding of main flows

**Shows:**
- 3 main flows: Session Setup, Enrollment Question, Document Upload
- High-level interactions
- Key participants

**Key Flows:**
1. **Session Setup** - User authentication and session creation
2. **Enrollment Question** - Question handling with tool calls
3. **Document Upload** - Document processing

---

## Detailed View

**When to Use:** Implementation, debugging, complete flow understanding

**Shows:**
- All flow variations
- Complete enrollment tool workflows
- Streaming and history management
- All participants and interactions

### Main Flows

#### 1. Student Session Bootstrap
- Student opens enrollment portal
- Agent Service creates/validates session
- Postgres stores session and checkpoint thread
- Returns JWT session token

#### 2. Document Ingestion
- Student uploads document via Agent Service
- Agent proxies to RAG Service
- RAG Service processes document (chunking, embedding)
- Stores vectors in Postgres
- Returns document ID

#### 3. Enrollment Question (Main Flow)
- Student asks enrollment question
- Agent Service invokes LangGraph workflow
- LangGraph classifies intent
- If policy context needed: queries RAG Service
- If enrollment tool needed: calls Enrollment Service
- Enrollment Service queries Postgres and Neo4j
- Results returned to LangGraph
- LangGraph formats response with LLM
- Response sent to student

#### 4. Enrollment Tool Variations

**Degree Audit:**
- Enrollment Service queries student courses
- Queries major requirements from Neo4j
- Matches courses to requirements
- Calculates progress
- Returns audit report

**Scenario Comparison:**
- Enrollment Service generates scenarios
- Queries courses and costs
- Checks prerequisites
- Compares scenarios
- Returns comparison matrix

**Schedule Optimization:**
- Enrollment Service queries sections
- Queries conflicts from Neo4j
- Generates valid combinations
- Scores and ranks schedules
- Returns optimal options

**Transfer Check:**
- Enrollment Service queries transfer courses
- Queries equivalency graph from Neo4j
- Gets policy context from RAG Service
- Returns equivalency result

**Budget Calculation:**
- Enrollment Service queries tuition, fees, costs
- Calculates total costs
- Returns cost breakdown

#### 5. Streaming Responses
- Student requests streaming chat
- Agent Service streams tokens from LangGraph
- LangGraph streams from LLM
- Real-time token delivery via SSE

#### 6. History Management
- Student requests message history
- Agent Service loads checkpoints from Postgres
- Returns conversation history
- Student can delete history

#### 7. Monitoring
- All services emit metrics to Prometheus
- Langfuse traces LLM calls
- Grafana visualizes metrics

---

## Flow Patterns

### Synchronous Flow
```
Student → Agent → LangGraph → Tool → Service → Database → Response
```

### Streaming Flow
```
Student → Agent → LangGraph → LLM → [Stream tokens] → Student
```

### Async Flow (Document Processing)
```
Student → Agent → RAG Service → [Async workers] → Postgres
```

---

## Key Participants

- **Student** - End user
- **Agent Service** - Orchestration hub
- **RAG Service** - Document and policy search
- **Enrollment Service** - Enrollment assistance engines
- **Postgres** - Relational and vector data
- **Neo4j** - Knowledge graph
- **OpenAI** - LLM and embeddings

---

## Related Diagrams

- **Individual Flows:**
  - `A4_01_flow_ingestion.png` - Document upload details
  - `A4_02_flow_session_auth.png` - Authentication details
  - `A4_03_flow_chat.png` - Chat interaction details
  - `A4_04_flow_enrollment_*.png` - Enrollment workflows




