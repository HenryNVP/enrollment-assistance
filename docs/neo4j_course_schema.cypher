// Neo4j schema for course prerequisite graph (MS AI focused)
// Usage:
// 1) Open Neo4j Browser and run this file top-to-bottom, or
// 2) Use cypher-shell: cypher-shell -f docs/neo4j_course_schema.cypher

// -----------------------------
// Constraints (idempotent)
// -----------------------------

CREATE CONSTRAINT course_entity_id_unique IF NOT EXISTS
FOR (c:Course) REQUIRE c.entity_id IS UNIQUE;

CREATE CONSTRAINT course_code_unique IF NOT EXISTS
FOR (c:Course) REQUIRE c.course_code IS UNIQUE;

CREATE CONSTRAINT program_entity_id_unique IF NOT EXISTS
FOR (p:Program) REQUIRE p.entity_id IS UNIQUE;

CREATE CONSTRAINT department_entity_id_unique IF NOT EXISTS
FOR (d:Department) REQUIRE d.entity_id IS UNIQUE;

CREATE CONSTRAINT evidence_entity_id_unique IF NOT EXISTS
FOR (e:Evidence) REQUIRE e.entity_id IS UNIQUE;

CREATE CONSTRAINT specialization_entity_id_unique IF NOT EXISTS
FOR (s:Specialization) REQUIRE s.entity_id IS UNIQUE;

CREATE CONSTRAINT core_group_entity_id_unique IF NOT EXISTS
FOR (g:CoreCourseGroup) REQUIRE g.entity_id IS UNIQUE;

CREATE CONSTRAINT elective_group_entity_id_unique IF NOT EXISTS
FOR (g:ElectiveCourseGroup) REQUIRE g.entity_id IS UNIQUE;

CREATE CONSTRAINT requirement_group_entity_id_unique IF NOT EXISTS
FOR (g:RequirementGroup) REQUIRE g.entity_id IS UNIQUE;

// -----------------------------
// Indexes (idempotent)
// -----------------------------

CREATE INDEX course_code_idx IF NOT EXISTS
FOR (c:Course) ON (c.course_code);

CREATE INDEX course_title_idx IF NOT EXISTS
FOR (c:Course) ON (c.title);

CREATE INDEX evidence_source_file_idx IF NOT EXISTS
FOR (e:Evidence) ON (e.source_file);

CREATE INDEX specialization_name_idx IF NOT EXISTS
FOR (s:Specialization) ON (s.name);

// -----------------------------
// Relationship conventions
// -----------------------------
// (Course)-[:REQUIRES {confidence, source_file, evidence_text, updated_at}]->(Course)
// (Course)-[:CO_REQUIRES {confidence, source_file, evidence_text, updated_at}]->(Course)
// (Course)-[:OFFERED_BY]->(Department)
// (Course)-[:PART_OF]->(Program)
// (Course)-[:HAS_EVIDENCE]->(Evidence)
// (Program)-[:HAS_CORE_GROUP]->(CoreCourseGroup)
// (Program)-[:HAS_ELECTIVE_GROUP]->(ElectiveCourseGroup)
// (Program)-[:HAS_REQUIREMENT_GROUP]->(RequirementGroup)
// (Program)-[:HAS_SPECIALIZATION]->(Specialization)
// (Specialization)-[:HAS_CORE_GROUP]->(CoreCourseGroup)
// (Specialization)-[:HAS_ELECTIVE_GROUP]->(ElectiveCourseGroup)
// (Course)-[:IN_CORE_GROUP]->(CoreCourseGroup)
// (Course)-[:IN_ELECTIVE_GROUP]->(ElectiveCourseGroup)
// (Course)-[:IN_REQUIREMENT_GROUP]->(RequirementGroup)
// (Course)-[:IN_SPECIALIZATION]->(Specialization)

// -----------------------------
// Starter reference data (optional)
// -----------------------------
// Comment out this block if you only want schema objects.

MERGE (p:Program {entity_id: "MSAI"})
SET p.name = "MS in Artificial Intelligence";

MERGE (core:CoreCourseGroup {entity_id: "MSAI_CORE"})
SET core.name = "Core Courses",
    core.min_units = 0;

MERGE (elective:ElectiveCourseGroup {entity_id: "MSAI_ELECTIVE"})
SET elective.name = "Elective Courses",
    elective.min_units = 0;

MERGE (specAuto:Specialization {entity_id: "MSAI_SPEC_AUTONOMOUS_SYSTEMS"})
SET specAuto.name = "Autonomous Systems";

MERGE (specDL:Specialization {entity_id: "MSAI_SPEC_DATA_SCIENCE"})
SET specDL.name = "Data Science";

MERGE (p)-[:HAS_CORE_GROUP]->(core);
MERGE (p)-[:HAS_ELECTIVE_GROUP]->(elective);
MERGE (p)-[:HAS_SPECIALIZATION]->(specAuto);
MERGE (p)-[:HAS_SPECIALIZATION]->(specDL);

MERGE (d:Department {entity_id: "CMPE"})
SET d.name = "Computer Engineering";

// Example course nodes
MERGE (c249:Course {entity_id: "CMPE-249"})
SET c249.course_code = "CMPE-249",
    c249.title = "Deep Learning";

MERGE (c255:Course {entity_id: "CMPE-255"})
SET c255.course_code = "CMPE-255",
    c255.title = "Advanced Machine Learning";

MERGE (c249)-[:OFFERED_BY]->(d);
MERGE (c249)-[:PART_OF]->(p);
MERGE (c249)-[:IN_CORE_GROUP]->(core);
MERGE (c249)-[:IN_SPECIALIZATION]->(specDL);
MERGE (c255)-[:OFFERED_BY]->(d);
MERGE (c255)-[:PART_OF]->(p);
MERGE (c255)-[:IN_ELECTIVE_GROUP]->(elective);
MERGE (c255)-[:IN_SPECIALIZATION]->(specDL);

// Example prerequisite edge
MERGE (c249)-[r:REQUIRES]->(c255)
SET r.confidence = 0.9,
    r.source_file = "prerequisites.txt",
    r.evidence_text = "CMPE-249 requires CMPE-255",
    r.updated_at = datetime();

// -----------------------------
// Useful verification queries
// -----------------------------
// Direct prerequisites:
// MATCH (c:Course {course_code: "CMPE-249"})-[:REQUIRES]->(p:Course)
// RETURN p.course_code, p.title;
//
// Transitive prerequisites (up to 3 hops):
// MATCH (c:Course {course_code: "CMPE-249"})-[:REQUIRES*1..3]->(p:Course)
// RETURN DISTINCT p.course_code, p.title;
