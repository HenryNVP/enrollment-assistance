# A0_03 Overview Enrollment Assistance

**Diagram File:** `00_overview/A0_03_overview_enrollment_assistance.puml`

---

## Purpose

This diagram focuses specifically on enrollment assistance capabilities, showing external data sources, ETL pipelines, and enrollment-specific data flows.

---

## Key Features

### External Data Sources
- **SJSU SIS** - Student Information System (courses, sections, enrollments)
- **SJSU Financial Systems** - Tuition, fees, costs
- **SJSU Transfer Center** - Transfer course equivalencies

### Data Integration
- **ETL Pipelines** - Extract, transform, load from external systems
- **Data Synchronization** - Regular updates to enrollment database
- **Real-time Updates** - Section capacity during registration

### Enrollment Capabilities
- **Degree Audit** - Progress tracking by major, minor, concentration
- **Scenario Comparison** - Full-time vs. part-time, in-person vs. hybrid
- **Schedule Optimization** - Optimal course scheduling
- **Transfer Equivalency** - Transfer course lookup
- **Budget Calculation** - Cost estimation

---

## Data Flows

### External to System
- Course catalog → ETL → Postgres
- Financial data → ETL → Postgres
- Transfer data → ETL → Postgres + Neo4j

### Enrollment operations (today vs target)

**Implemented path:** Student → Agent (`agent_ai`) → **`rag_api`** (vectors) and/or **`rag_graph`** (Neo4j curriculum) → Agent → student.

**Target path (diagram):** Student → Agent → **Enrollment microservice** (not in repo) → Postgres + Neo4j → Agent → student.

---

## When to Use

- **Enrollment-specific discussions** - Focus on enrollment capabilities
- **Data integration planning** - Understanding external data sources
- **Enrollment feature design** - Designing new enrollment features
- **Stakeholder presentations** - Showing enrollment focus

---

## Related Diagrams

- **Simplified Overview:** `00_overview/A0_01_overview_simplified.puml`
- **Detailed Overview:** `00_overview/A0_02_overview_detailed.puml`
- **Enrollment service (planned):** `02_service/enrollment_service/A2_04_component_enrollment_service_*.puml`
- **Enrollment flows (planned):** `04_flows/A4_04_flow_enrollment_*.puml`




