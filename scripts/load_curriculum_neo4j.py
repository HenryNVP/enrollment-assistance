#!/usr/bin/env python3
"""
Load data/curriculum_msai.yaml into Neo4j using schema docs/neo4j_course_schema.cypher.

Prereqs:
  pip install neo4j pyyaml

Example:
  export NEO4J_URI=bolt://localhost:7687
  export NEO4J_USERNAME=neo4j
  export NEO4J_PASSWORD=your-neo4j-password
  python3 scripts/load_curriculum_neo4j.py --file data/curriculum_msai.yaml

If NEO4J_PASSWORD is unset, the script reads NEO4J_* from (in order):
  backend/services/LightRAG/.env, then ./.env
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
    from neo4j import GraphDatabase
    from neo4j.exceptions import AuthError
except ImportError as e:
    print("Install dependencies: pip install neo4j pyyaml", file=sys.stderr)
    raise e

SOURCE = "curriculum_msai.yaml"


def _parse_dotenv_neo4j(path: Path) -> dict[str, str]:
    """Read NEO4J_* keys from a .env-style file (no shell expansion)."""
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        if not key.startswith("NEO4J_"):
            continue
        val = val.strip()
        if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
            val = val[1:-1]
        out[key] = val
    return out


def _apply_neo4j_dotenv(repo_root: Path) -> None:
    """If NEO4J_PASSWORD is unset, try LightRAG .env then repo .env."""
    if os.getenv("NEO4J_PASSWORD"):
        return
    candidates = [
        repo_root / "backend" / "services" / "LightRAG" / ".env",
        repo_root / ".env",
    ]
    for p in candidates:
        for k, v in _parse_dotenv_neo4j(p).items():
            os.environ.setdefault(k, v)
        if os.getenv("NEO4J_PASSWORD"):
            break


def load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def merge_curriculum(driver: Any, data: dict) -> None:
    program = data["program"]
    departments = data["departments"]
    specializations = data["specializations"]
    groups = data["groups"]
    courses = data["courses"]

    with driver.session() as session:
        session.run(
            """
            MERGE (p:Program {entity_id: $eid})
            SET p.name = $name, p.total_units = $total_units
            """,
            eid=program["entity_id"],
            name=program["name"],
            total_units=program.get("total_units"),
        )

        for d in departments:
            session.run(
                """
                MERGE (x:Department {entity_id: $eid})
                SET x.name = $name
                """,
                eid=d["entity_id"],
                name=d["name"],
            )

        for s in specializations:
            session.run(
                """
                MERGE (x:Specialization {entity_id: $eid})
                SET x.name = $name
                """,
                eid=s["entity_id"],
                name=s["name"],
            )

        core = groups["core"]
        elective = groups["elective"]
        session.run(
            """
            MERGE (g:CoreCourseGroup {entity_id: $eid})
            SET g.name = $name, g.min_units = $min_u
            """,
            eid=core["entity_id"],
            name=core["name"],
            min_u=core.get("min_units", 0),
        )
        session.run(
            """
            MERGE (g:ElectiveCourseGroup {entity_id: $eid})
            SET g.name = $name, g.min_units = $min_u
            """,
            eid=elective["entity_id"],
            name=elective["name"],
            min_u=elective.get("min_units", 0),
        )

        for key in ("gwar", "culminating"):
            g = groups[key]
            session.run(
                """
                MERGE (x:RequirementGroup {entity_id: $eid})
                SET x.name = $name
                """,
                eid=g["entity_id"],
                name=g["name"],
            )

        pid = program["entity_id"]
        session.run(
            """
            MATCH (p:Program {entity_id: $pid})
            MATCH (c:CoreCourseGroup {entity_id: $cid})
            MERGE (p)-[:HAS_CORE_GROUP]->(c)
            """,
            pid=pid,
            cid=core["entity_id"],
        )
        session.run(
            """
            MATCH (p:Program {entity_id: $pid})
            MATCH (e:ElectiveCourseGroup {entity_id: $eid})
            MERGE (p)-[:HAS_ELECTIVE_GROUP]->(e)
            """,
            pid=pid,
            eid=elective["entity_id"],
        )
        for key in ("gwar", "culminating"):
            gid = groups[key]["entity_id"]
            session.run(
                """
                MATCH (p:Program {entity_id: $pid})
                MATCH (g:RequirementGroup {entity_id: $gid})
                MERGE (p)-[:HAS_REQUIREMENT_GROUP]->(g)
                """,
                pid=pid,
                gid=gid,
            )

        for s in specializations:
            session.run(
                """
                MATCH (p:Program {entity_id: $pid})
                MATCH (sp:Specialization {entity_id: $sid})
                MERGE (p)-[:HAS_SPECIALIZATION]->(sp)
                """,
                pid=pid,
                sid=s["entity_id"],
            )

        for c in courses:
            cc = c["course_code"]
            dept = c["department"]
            title = c["title"]
            units = float(c.get("units", 0))
            entity_id = cc
            part_of = c.get("part_of_program", True)

            session.run(
                """
                MERGE (co:Course {entity_id: $eid})
                SET co.course_code = $cc,
                    co.title = $title,
                    co.units = $units,
                    co.prereq_one_of = $one_of
                """,
                eid=entity_id,
                cc=cc,
                title=title,
                units=units,
                one_of=c.get("requires_one_of") or [],
            )

            session.run(
                """
                MATCH (co:Course {entity_id: $eid})
                MATCH (d:Department {entity_id: $did})
                MERGE (co)-[:OFFERED_BY]->(d)
                """,
                eid=entity_id,
                did=dept,
            )

            if part_of:
                session.run(
                    """
                    MATCH (co:Course {entity_id: $eid})
                    MATCH (p:Program {entity_id: $pid})
                    MERGE (co)-[:PART_OF]->(p)
                    """,
                    eid=entity_id,
                    pid=pid,
                )

            if c.get("in_core_group"):
                session.run(
                    """
                    MATCH (co:Course {entity_id: $eid})
                    MATCH (g:CoreCourseGroup {entity_id: $gid})
                    MERGE (co)-[:IN_CORE_GROUP]->(g)
                    """,
                    eid=entity_id,
                    gid=core["entity_id"],
                )

            if c.get("in_elective_group"):
                session.run(
                    """
                    MATCH (co:Course {entity_id: $eid})
                    MATCH (g:ElectiveCourseGroup {entity_id: $gid})
                    MERGE (co)-[:IN_ELECTIVE_GROUP]->(g)
                    """,
                    eid=entity_id,
                    gid=elective["entity_id"],
                )

            for sid in c.get("specializations") or []:
                session.run(
                    """
                    MATCH (co:Course {entity_id: $eid})
                    MATCH (s:Specialization {entity_id: $sid})
                    MERGE (co)-[:IN_SPECIALIZATION]->(s)
                    """,
                    eid=entity_id,
                    sid=sid,
                )

            for rgid in c.get("requirement_groups") or []:
                session.run(
                    """
                    MATCH (co:Course {entity_id: $eid})
                    MATCH (g:RequirementGroup {entity_id: $gid})
                    MERGE (co)-[:IN_REQUIREMENT_GROUP]->(g)
                    """,
                    eid=entity_id,
                    gid=rgid,
                )

        for c in courses:
            cc = c["course_code"]
            for pre in c.get("requires_all") or []:
                session.run(
                    """
                    MATCH (a:Course {entity_id: $aid})
                    MATCH (b:Course {entity_id: $bid})
                    MERGE (a)-[r:REQUIRES]->(b)
                    SET r.or_group = false,
                        r.confidence = 1.0,
                        r.source_file = $src,
                        r.evidence_text = $aid + ' requires ' + $bid + ' (AND)',
                        r.updated_at = datetime()
                    """,
                    aid=cc,
                    bid=pre,
                    src=SOURCE,
                )

        for c in courses:
            cc = c["course_code"]
            for pre in c.get("requires_one_of") or []:
                session.run(
                    """
                    MATCH (a:Course {entity_id: $aid})
                    MATCH (b:Course {entity_id: $bid})
                    MERGE (a)-[r:REQUIRES]->(b)
                    SET r.or_group = true,
                        r.confidence = 1.0,
                        r.source_file = $src,
                        r.evidence_text = $aid + ' requires one of: ' + $bid + ' (OR)',
                        r.updated_at = datetime()
                    """,
                    aid=cc,
                    bid=pre,
                    src=SOURCE,
                )


def main() -> None:
    parser = argparse.ArgumentParser(description="Load curriculum YAML into Neo4j")
    parser.add_argument(
        "--file",
        type=Path,
        default=Path("data/curriculum_msai.yaml"),
        help="Path to curriculum YAML",
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    path = args.file if args.file.is_absolute() else root / args.file
    if not path.exists():
        print(f"File not found: {path}", file=sys.stderr)
        sys.exit(1)

    _apply_neo4j_dotenv(root)

    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USERNAME", os.getenv("NEO4J_USER", "neo4j"))
    password = os.getenv("NEO4J_PASSWORD", "")
    if not password:
        print(
            "NEO4J_PASSWORD not set.\n"
            "  export NEO4J_PASSWORD='…'   # same password you use in Neo4j Browser\n"
            "  or add NEO4J_PASSWORD to backend/services/LightRAG/.env",
            file=sys.stderr,
        )
        sys.exit(1)

    data = load_yaml(path)
    driver = GraphDatabase.driver(uri, auth=(user, password))
    try:
        merge_curriculum(driver, data)
        print(f"Loaded curriculum from {path} into {uri}")
    except AuthError as e:
        print(
            f"Neo4j authentication failed ({e}).\n"
            f"  URI: {uri}\n"
            f"  User: {user}\n"
            "  Fix: use the password for this Neo4j instance (Browser login). "
            "If you use Docker, check NEO4J_AUTH or the container docs; "
            "defaults like 'neo4j/password' only apply if you never changed the password.",
            file=sys.stderr,
        )
        sys.exit(1)
    finally:
        driver.close()


if __name__ == "__main__":
    main()
