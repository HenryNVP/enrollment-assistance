# SJSU Enrollment Assistance - Architecture Design

**Document Version:** 1.0  
**Last Updated:** 2025-01-27  
**Status:** Design Proposal

---

## Executive Summary

This document outlines the architecture for an AI-powered enrollment assistance system specifically designed for San Jose State University (SJSU). The system helps students with enrollment decisions, budgeting, scheduling, multi-term planning, degree audits, and scenario comparisons.

**Key Capabilities:**
- Answer enrollment-related questions (deadlines, prerequisites, capacity)
- Budget planning (tuition, fees, books, housing, commuting)
- Schedule optimization and conflict detection
- Multi-term academic planning
- Degree audit by major/minor/concentration
- Transfer course equivalency and policy lookup
- Scenario comparisons (full-time vs part-time, in-person vs hybrid)
- Course search with filters (location, time, professor, accessibility)

---

## 1. Architecture Overview

### 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Client Layer                              │
│  Web UI, Mobile App, API Clients (Student Portal Integration) │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                  Service Layer (Microservices)              │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │   Agent      │  │     RAG      │  │   Enrollment     │  │
│  │   Service    │  │   Service    │  │   Service        │  │
│  │  (Port 8000) │  │  (Port 8080) │  │  (Port 8090)     │  │
│  │              │  │              │  │                  │  │
│  │ • Chat API   │  │ • Document   │  │ • Degree Audit   │  │
│  │ • Auth       │  │   Processing │  │ • Scenario       │  │
│  │ • Tools      │  │ • Vector     │  │   Comparison     │  │
│  │ • LangGraph  │  │   Search     │  │ • Schedule       │  │
│  │              │  │ • Knowledge  │  │   Optimization   │  │
│  │              │  │   Graph      │  │ • Transfer       │  │
│  │              │  │              │  │   Equivalency    │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│              Knowledge/Data Layer (Storage)                  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Postgres (Relational + Vector)                     │   │
│  │  • Application Data (users, sessions)               │   │
│  │  • Enrollment Domain Data (courses, schedules)        │   │
│  │  • Financial Data (tuition, fees, costs)            │   │
│  │  • Vector Store (pgvector) - policy documents       │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Neo4j (Knowledge Graph)                             │   │
│  │  • Course prerequisites graph                         │   │
│  │  • Major/minor/concentration requirements            │   │
│  │  • Transfer equivalency mappings                     │   │
│  │  • Course relationships (co-requisites, conflicts)   │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Service Responsibilities

| Service | Port | Primary Responsibility |
|---------|------|------------------------|
| **Agent Service** | 8000 | Chat interface, user interaction, tool orchestration |
| **RAG Service** | 8080 | Policy document search, knowledge retrieval |
| **Enrollment Service** | 8090 | Degree audits, scenario comparisons, schedule optimization |

---

## 2. Enhanced Data Models

### 2.1 Enrollment Domain Database Schema

**Core Tables:**

```sql
-- Academic Structure
departments (id, code, name, college)
majors (id, code, name, department_id, degree_type)
minors (id, code, name, department_id)
concentrations (id, code, name, major_id)
courses (id, code, title, units, description, department_id)
course_sections (
  id, course_id, term, section_number,
  days, start_time, end_time, location,
  instructor_id, capacity, enrolled, waitlist,
  delivery_mode, accessibility_features
)
prerequisites (id, course_id, prerequisite_course_id, requirement_type)
co_requisites (id, course_id, co_requisite_course_id)

-- Major Requirements
major_requirements (
  id, major_id, course_id, requirement_type,
  min_units, min_grade, notes
)
minor_requirements (id, minor_id, course_id, requirement_type, min_units)
concentration_requirements (id, concentration_id, course_id, requirement_type)

-- Enrollment & Scheduling
enrollments (
  id, student_id, section_id, term,
  enrollment_date, status, grade, units
)
enrollment_deadlines (
  id, term, deadline_type, deadline_date, description
)
schedule_conflicts (
  id, section_id_1, section_id_2, conflict_type
)

-- Financial
tuition_rates (
  id, term, student_type, residency_status,
  units_min, units_max, tuition_amount
)
fees (
  id, fee_type, term, amount, description,
  required, waivable
)
course_costs (
  id, course_id, term, book_cost_estimate,
  material_cost_estimate, notes
)
housing_costs (
  id, term, housing_type, cost_per_term, description
)
commuting_zones (
  id, zone_name, distance_miles, estimated_cost_per_term
)

-- Transfer
transfer_institutions (id, name, type, state)
transfer_courses (
  id, transfer_institution_id, transfer_course_code,
  transfer_course_title, sjsu_course_id, equivalency_status,
  effective_date, expiration_date, notes
)
transfer_policies (
  id, policy_type, title, content, effective_date,
  applicable_to, tags
)

-- People
students (
  id, sjsu_id, email, first_name, last_name,
  residency_status, student_type, major_id, minor_id,
  concentration_id, enrollment_status, gpa
)
instructors (
  id, employee_id, first_name, last_name,
  department_id, email, office_location
)

-- Accessibility
accessibility_features (
  id, feature_type, description
)
section_accessibility (
  section_id, accessibility_feature_id
)
```

### 2.2 Knowledge Graph Schema (Neo4j)

**Node Types:**
- `Course` (code, title, units, department)
- `Major` (code, name, degree_type)
- `Minor` (code, name)
- `Concentration` (code, name)
- `Section` (section_number, term, days, time, location, instructor)
- `Student` (sjsu_id, name, major, minor)
- `Instructor` (name, department)
- `TransferCourse` (institution, code, title)
- `Policy` (type, title, content)

**Relationship Types:**
- `PREREQUISITE_FOR` (Course → Course)
- `CO_REQUISITE_OF` (Course ↔ Course)
- `REQUIRED_FOR` (Course → Major/Minor/Concentration)
- `ELECTIVE_FOR` (Course → Major/Minor/Concentration)
- `EQUIVALENT_TO` (TransferCourse → Course)
- `TAUGHT_BY` (Section → Instructor)
- `ENROLLED_IN` (Student → Section)
- `CONFLICTS_WITH` (Section ↔ Section)
- `REFERENCES` (Policy → Course/Major/Policy)

---

## 3. Service Layer Details

### 3.1 Agent Service Enhancements

**New Tools:**
1. **`enrollment_search`** - Search courses with filters (term, major, time, location, professor, accessibility)
2. **`degree_audit`** - Check progress toward major/minor/concentration requirements
3. **`scenario_compare`** - Compare enrollment scenarios (full-time vs part-time, delivery modes)
4. **`schedule_optimize`** - Find optimal schedule given constraints
5. **`transfer_check`** - Check transfer course equivalency
6. **`budget_calculate`** - Calculate total costs for a term/plan
7. **`deadline_check`** - Get enrollment deadlines for a term

**Enhanced LangGraph Workflow:**
```
User Query → Intent Classification
    ├─→ Enrollment Question → enrollment_search tool
    ├─→ Degree Progress → degree_audit tool
    ├─→ Scenario Planning → scenario_compare tool
    ├─→ Schedule Help → schedule_optimize tool
    ├─→ Transfer Question → transfer_check + RAG search
    ├─→ Budget Question → budget_calculate tool
    ├─→ Policy Question → RAG search (policies)
    └─→ General Question → RAG search + LLM reasoning
```

### 3.2 RAG Service Enhancements

**Document Types:**
- Academic policies (enrollment, transfer, graduation)
- Course catalogs and descriptions
- Financial aid policies
- Transfer articulation agreements
- Department-specific requirements
- Accessibility accommodations policies

**Enhanced Retrieval:**
- **Hybrid Search**: Vector similarity + keyword matching for policy documents
- **Graph-Enhanced RAG**: Use Neo4j to find related courses/policies, then retrieve relevant document chunks
- **Contextual Filtering**: Filter results by term, major, student type

### 3.3 Enrollment Service (New/Enhanced)

**Core Components:**

#### 3.3.1 Degree Audit Engine
- **Input**: Student ID, major/minor/concentration
- **Process**:
  1. Query student's completed courses and grades
  2. Query major/minor/concentration requirements from Neo4j
  3. Match completed courses to requirements
  4. Calculate progress (units completed, units remaining, GPA)
  5. Identify missing requirements and suggest courses
- **Output**: Detailed audit report with progress percentages

#### 3.3.2 Scenario Comparison Engine
- **Input**: Student constraints, scenario parameters (full-time/part-time, delivery mode, term)
- **Process**:
  1. Generate multiple enrollment scenarios
  2. For each scenario:
     - Calculate total units
     - Estimate costs (tuition, fees, books, housing, commuting)
     - Check schedule conflicts
     - Verify prerequisites
     - Calculate time to degree
  3. Compare scenarios across dimensions
- **Output**: Comparison matrix with recommendations

#### 3.3.3 Schedule Optimization Engine
- **Input**: Desired courses, time preferences, constraints (work schedule, accessibility needs)
- **Process**:
  1. Query available sections for desired courses
  2. Generate all valid schedule combinations
  3. Score each combination:
     - Time conflicts (penalty)
     - Time preferences (preference score)
     - Location proximity (minimize travel)
     - Accessibility match (bonus)
  4. Return top N optimal schedules
- **Output**: Ranked list of schedule options

#### 3.3.4 Transfer Equivalency Engine
- **Input**: Transfer institution, course code/title
- **Process**:
  1. Search transfer_courses table
  2. Query Neo4j for equivalent courses and relationships
  3. Check policy applicability (effective dates, student type)
  4. Return equivalency status and notes
- **Output**: Equivalency result with confidence level

#### 3.3.5 Budget Calculator
- **Input**: Term, units, student type, residency, housing choice, commuting zone
- **Process**:
  1. Calculate tuition based on units and rates
  2. Sum applicable fees
  3. Estimate book costs for enrolled courses
  4. Add housing costs (if applicable)
  5. Add commuting costs (if applicable)
  6. Apply financial aid estimates (if provided)
- **Output**: Detailed cost breakdown

**API Endpoints:**
```
POST /api/v1/enrollment/degree-audit
POST /api/v1/enrollment/scenario-compare
POST /api/v1/enrollment/schedule-optimize
POST /api/v1/enrollment/transfer-check
POST /api/v1/enrollment/budget-calculate
GET  /api/v1/enrollment/courses/search
GET  /api/v1/enrollment/deadlines
GET  /api/v1/enrollment/sections/{section_id}
```

---

## 4. Data Integration & ETL

### 4.1 Data Sources

**Primary Sources:**
1. **SJSU Student Information System (SIS)**
   - Course catalog
   - Section schedules
   - Student enrollments
   - Grades and transcripts
   - Instructor assignments

2. **SJSU Financial Systems**
   - Tuition rates
   - Fee schedules
   - Financial aid data

3. **SJSU Transfer Center**
   - Articulation agreements
   - Transfer course equivalencies
   - Transfer policies

4. **SJSU Academic Departments**
   - Major/minor/concentration requirements
   - Department-specific policies
   - Course prerequisites

5. **SJSU Accessibility Resource Center**
   - Accessibility features
   - Accommodation policies

### 4.2 ETL Pipeline Design

**Batch Updates (Daily/Weekly):**
- Course catalog and sections (daily during registration periods)
- Enrollment data (daily)
- Financial data (weekly)
- Transfer equivalencies (weekly)

**Real-Time Updates:**
- Section capacity and waitlist (real-time during registration)
- Enrollment deadlines (real-time)

**Initial Load:**
- Historical course data
- Historical transfer equivalencies
- Policy documents (one-time + updates)

---

## 5. Key Workflows

### 5.1 Enrollment Question Workflow

```
User: "What CS courses are available this fall?"
  ↓
Agent Service → Intent: enrollment_search
  ↓
Tool Call → Enrollment Service: /courses/search
  Parameters: {department: "CS", term: "Fall 2025"}
  ↓
Enrollment Service → Query Postgres
  Returns: List of courses with sections
  ↓
Agent Service → Format response with:
  - Course codes and titles
  - Available sections (times, locations, professors)
  - Capacity and enrollment status
  - Prerequisites
```

### 5.2 Degree Audit Workflow

```
User: "How am I doing with my CS major requirements?"
  ↓
Agent Service → Intent: degree_audit
  ↓
Tool Call → Enrollment Service: /degree-audit
  Parameters: {student_id: "12345", major: "CS"}
  ↓
Enrollment Service:
  1. Query student's completed courses
  2. Query CS major requirements (Neo4j)
  3. Match courses to requirements
  4. Calculate progress
  ↓
Returns: Audit report
  ↓
Agent Service → Present:
  - Overall progress (%)
  - Completed requirements
  - Remaining requirements
  - Suggested next courses
```

### 5.3 Scenario Comparison Workflow

```
User: "Compare full-time vs part-time enrollment for Fall 2025"
  ↓
Agent Service → Intent: scenario_compare
  ↓
Tool Call → Enrollment Service: /scenario-compare
  Parameters: {
    scenarios: [
      {units: 15, delivery_mode: "in-person"},
      {units: 6, delivery_mode: "hybrid"}
    ],
    student_id: "12345"
  }
  ↓
Enrollment Service:
  1. Generate scenarios
  2. Calculate costs for each
  3. Check schedule feasibility
  4. Estimate time to degree
  ↓
Returns: Comparison matrix
  ↓
Agent Service → Present:
  - Cost comparison
  - Schedule comparison
  - Time to degree
  - Recommendations
```

### 5.4 Transfer Equivalency Workflow

```
User: "Does MATH 30 at De Anza transfer to SJSU?"
  ↓
Agent Service → Intent: transfer_check
  ↓
Tool Call → Enrollment Service: /transfer-check
  Parameters: {
    institution: "De Anza College",
    course_code: "MATH 30"
  }
  ↓
Enrollment Service:
  1. Query transfer_courses table
  2. Query Neo4j for relationships
  3. Check policy applicability
  ↓
Returns: Equivalency result
  ↓
Agent Service → Present:
  - Equivalent SJSU course (if any)
  - Equivalency status
  - Applicable policies
  - Notes
```

---

## 6. Security & Privacy

### 6.1 Student Data Protection

- **Authentication**: JWT-based, integration with SJSU SSO (optional)
- **Authorization**: Role-based access (student, advisor, admin)
- **Data Isolation**: Students can only access their own enrollment data
- **PII Handling**: Redact sensitive data in logs
- **Compliance**: FERPA compliance for student records

### 6.2 API Security

- Rate limiting per user
- Input validation and sanitization
- SQL injection prevention (parameterized queries)
- Graph injection prevention (parameterized Cypher)

---

## 7. Observability

### 7.1 Key Metrics

**Agent Service:**
- Enrollment question types (counter by intent)
- Tool call latencies (histogram)
- Degree audit requests (counter)
- Scenario comparison requests (counter)

**Enrollment Service:**
- Degree audit execution time (histogram)
- Scenario comparison execution time (histogram)
- Schedule optimization execution time (histogram)
- Database query latencies (histogram)

**RAG Service:**
- Policy document searches (counter)
- Transfer policy lookups (counter)

### 7.2 Logging

- Structured logs with student_id (hashed), session_id, request_id
- Audit trail for degree audits and scenario comparisons
- Error tracking for failed queries

---

## 8. Implementation Phases

### Phase 1: Core Enrollment Data & Search (Weeks 1-4)
- Set up enrollment domain database schema
- Implement course/section search API
- Basic RAG for policy documents
- Simple chat interface for enrollment questions

### Phase 2: Degree Audit (Weeks 5-8)
- Implement degree audit engine
- Load major/minor/concentration requirements
- Build prerequisite graph in Neo4j
- Integrate degree audit tool into Agent Service

### Phase 3: Scenario Comparison & Budgeting (Weeks 9-12)
- Implement scenario comparison engine
- Build budget calculator
- Load financial data (tuition, fees, costs)
- Add scenario comparison tool to Agent Service

### Phase 4: Schedule Optimization (Weeks 13-16)
- Implement schedule optimization engine
- Build conflict detection
- Add accessibility filtering
- Integrate schedule optimization tool

### Phase 5: Transfer Equivalency (Weeks 17-20)
- Load transfer course data
- Build transfer equivalency engine
- Integrate transfer policies into RAG
- Add transfer check tool

### Phase 6: Multi-Term Planning & Polish (Weeks 21-24)
- Multi-term planning capabilities
- Enhanced UI/UX
- Performance optimization
- Comprehensive testing

---

## 9. Technology Stack

**Unchanged from Current:**
- FastAPI (all services)
- Postgres + pgvector
- Neo4j
- LangGraph (Agent Service)
- OpenAI (LLM + embeddings)
- Prometheus + Grafana
- Langfuse

**New/Enhanced:**
- **Optimization Libraries**: OR-Tools or scipy.optimize for schedule optimization
- **Graph Algorithms**: NetworkX for prerequisite graph analysis
- **ETL Tools**: Apache Airflow or Prefect for data pipelines
- **Caching**: Redis for frequently accessed data (course catalogs, schedules)

---

## 10. Open Questions & Decisions Needed

1. **Data Access**: Direct SIS integration vs. data export/import?
2. **Real-Time Updates**: How real-time should section capacity be?
3. **Student Authentication**: Use SJSU SSO or custom auth?
4. **Advisor Access**: Should advisors have access to student data?
5. **Historical Data**: How far back should we load historical course data?
6. **Transfer Data**: Manual entry vs. automated import from transfer center?
7. **Accessibility Data**: Integration with Accessibility Resource Center system?

---

## 11. Success Metrics

- **Accuracy**: Degree audit accuracy (compared to official audits)
- **Response Time**: < 2s for course search, < 5s for degree audit
- **User Satisfaction**: Survey scores on helpfulness
- **Adoption**: Number of students using the system
- **Cost Savings**: Reduction in advisor consultation time

---

**Next Steps:**
1. Review and approve architecture
2. Set up development environment
3. Begin Phase 1 implementation
4. Establish data integration agreements with SJSU IT

