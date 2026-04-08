"""Curated MS-AI course graph in Neo4j — deterministic prereqs and program structure."""

from __future__ import annotations

import re
from typing import Any, Optional, Set, Tuple


def neo4j_driver_config() -> dict[str, str | None]:
    import os

    return {
        "uri": os.getenv("NEO4J_URI", os.getenv("NEO4J_URI_BOLT", "bolt://localhost:7687")),
        "user": os.getenv("NEO4J_USERNAME", os.getenv("NEO4J_USER", "neo4j")),
        "password": os.getenv("NEO4J_PASSWORD", ""),
        "database": os.getenv("NEO4J_DATABASE") or None,
    }


def normalize_course_code(code: str) -> str:
    """Normalize user input to a canonical form like CMPE-260."""
    code = code.strip().upper()
    code = code.replace("/", "-")
    m = re.search(r"\b([A-Z]{2,6})[-\s]?(\d{3}[A-Z]?)\b", code)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    code = re.sub(r"\s+", "", code)
    code = re.sub(r"^([A-Z]{2,6})(\d)", r"\1-\2", code)
    return code


# ---------------------------------------------------------------------------
# Single-course prerequisite lookup
# ---------------------------------------------------------------------------


def _requires_breakdown(session: Any, course_code: str) -> Tuple[Set[str], list[str]]:
    """Single round-trip: all immediate REQUIRES, split by OR vs non-OR edge."""
    result = session.run(
        """
        MATCH (c:Course {course_code: $code})-[r:REQUIRES]->(p:Course)
        RETURN p.course_code AS pc, coalesce(r.or_group, false) AS or_g
        """,
        code=course_code,
    )
    direct: Set[str] = set()
    or_alts: list[str] = []
    for rec in result:
        pc = str(rec["pc"])
        direct.add(pc)
        if rec["or_g"]:
            or_alts.append(pc)
    return direct, sorted(set(or_alts))


def _full_transitive(
    session: Any,
    course_code: str,
    depth: int,
) -> Set[str]:
    """All courses reachable via any REQUIRES edge (AND or OR) up to depth."""
    dmax = min(depth, 6)
    result = session.run(
        """
        MATCH path = (c:Course {course_code: $code})-[:REQUIRES*1..6]->(p:Course)
        WHERE length(path) <= $depth
        WITH p.course_code AS pc, length(path) AS plen
        WITH pc, min(plen) AS dlen
        WHERE dlen >= 1 AND dlen <= $depth
        RETURN pc
        """,
        code=course_code,
        depth=dmax,
    )
    return {str(rec["pc"]) for rec in result}


def fetch_curated_prereqs_sync(
    session: Any,
    course_code_norm: str,
    depth: int,
    course_code_for_response: str,
) -> Optional[dict[str, Any]]:
    """Returns a dict suitable for PrereqsResponse, or None if course not in graph."""
    row = session.run(
        """
        MATCH (c:Course {course_code: $code})
        RETURN c.course_code AS code, c.prereq_one_of AS one_of
        """,
        code=course_code_norm,
    ).single()
    if not row:
        return None

    prop_one_of = row["one_of"]
    if prop_one_of is None:
        prop_list: list[str] = []
    elif isinstance(prop_one_of, list):
        prop_list = [str(x) for x in prop_one_of]
    else:
        prop_list = []

    direct_set, edge_one_of = _requires_breakdown(session, course_code_norm)
    one_of_merged = sorted(set(edge_one_of) | set(prop_list))

    transitive_set = _full_transitive(session, course_code_norm, min(depth, 6))

    return {
        "course_code": course_code_for_response,
        "depth": depth,
        "direct": sorted(direct_set),
        "transitive": sorted(transitive_set),
        "source": "curated",
        "requires_one_of": one_of_merged if one_of_merged else None,
    }


# ---------------------------------------------------------------------------
# Full program structure
# ---------------------------------------------------------------------------


def fetch_program_structure_sync(
    session: Any,
    program_id: str,
) -> Optional[dict[str, Any]]:
    """Return the full program structure: courses, groups, prereqs, specializations."""

    prog = session.run(
        "MATCH (p:Program {entity_id: $pid}) RETURN p.name AS name, p.total_units AS total_units",
        pid=program_id,
    ).single()
    if not prog:
        return None

    total_units = float(prog["total_units"]) if prog["total_units"] is not None else None

    # -- Collect all prerequisite edges for courses related to this program ---
    prereq_map: dict[str, dict[str, list[str]]] = {}
    for rec in session.run(
        """
        MATCH (c:Course)-[r:REQUIRES]->(pre:Course)
        WHERE (c)-[:PART_OF]->(:Program {entity_id: $pid})
           OR (pre)-[:PART_OF]->(:Program {entity_id: $pid})
        RETURN c.course_code AS course, pre.course_code AS prereq,
               coalesce(r.or_group, false) AS is_or
        """,
        pid=program_id,
    ):
        cc = str(rec["course"])
        pre = str(rec["prereq"])
        if cc not in prereq_map:
            prereq_map[cc] = {"requires_all": [], "requires_one_of": []}
        if rec["is_or"]:
            prereq_map[cc]["requires_one_of"].append(pre)
        else:
            prereq_map[cc]["requires_all"].append(pre)

    def _course_dict(code: str, title: str, units: Any) -> dict[str, Any]:
        p = prereq_map.get(code, {"requires_all": [], "requires_one_of": []})
        return {
            "course_code": code,
            "title": title,
            "units": float(units or 0),
            "requires_all": sorted(set(p["requires_all"])),
            "requires_one_of": sorted(set(p["requires_one_of"])),
        }

    # -- Core courses --
    core_courses: list[dict] = []
    core_meta = {"group_id": "", "name": "Core Courses", "min_units": None}
    for rec in session.run(
        """
        MATCH (:Program {entity_id: $pid})-[:HAS_CORE_GROUP]->(g:CoreCourseGroup)
              <-[:IN_CORE_GROUP]-(c:Course)
        RETURN g.entity_id AS gid, g.name AS gname, g.min_units AS min_u,
               c.course_code AS code, c.title AS title, c.units AS units
        """,
        pid=program_id,
    ):
        core_meta = {
            "group_id": str(rec["gid"]),
            "name": str(rec["gname"]),
            "min_units": float(rec["min_u"]) if rec["min_u"] is not None else None,
        }
        core_courses.append(_course_dict(str(rec["code"]), str(rec["title"]), rec["units"]))

    # -- Elective courses --
    elective_courses: list[dict] = []
    elective_meta = {"group_id": "", "name": "Elective Courses", "min_units": None}
    for rec in session.run(
        """
        MATCH (:Program {entity_id: $pid})-[:HAS_ELECTIVE_GROUP]->(g:ElectiveCourseGroup)
              <-[:IN_ELECTIVE_GROUP]-(c:Course)
        RETURN g.entity_id AS gid, g.name AS gname, g.min_units AS min_u,
               c.course_code AS code, c.title AS title, c.units AS units
        """,
        pid=program_id,
    ):
        elective_meta = {
            "group_id": str(rec["gid"]),
            "name": str(rec["gname"]),
            "min_units": float(rec["min_u"]) if rec["min_u"] is not None else None,
        }
        elective_courses.append(_course_dict(str(rec["code"]), str(rec["title"]), rec["units"]))

    # -- Requirement groups (GWAR, culminating) --
    req_groups_map: dict[str, dict[str, Any]] = {}
    for rec in session.run(
        """
        MATCH (:Program {entity_id: $pid})-[:HAS_REQUIREMENT_GROUP]->(g:RequirementGroup)
              <-[:IN_REQUIREMENT_GROUP]-(c:Course)
        RETURN g.entity_id AS gid, g.name AS gname,
               c.course_code AS code, c.title AS title, c.units AS units
        """,
        pid=program_id,
    ):
        gid = str(rec["gid"])
        if gid not in req_groups_map:
            req_groups_map[gid] = {"group_id": gid, "name": str(rec["gname"]), "courses": []}
        req_groups_map[gid]["courses"].append(
            _course_dict(str(rec["code"]), str(rec["title"]), rec["units"])
        )

    # -- Specializations --
    spec_map: dict[str, dict[str, Any]] = {}
    for rec in session.run(
        """
        MATCH (:Program {entity_id: $pid})-[:HAS_SPECIALIZATION]->(s:Specialization)
              <-[:IN_SPECIALIZATION]-(c:Course)
        RETURN s.entity_id AS sid, s.name AS sname, c.course_code AS code
        """,
        pid=program_id,
    ):
        sid = str(rec["sid"])
        if sid not in spec_map:
            spec_map[sid] = {"specialization_id": sid, "name": str(rec["sname"]), "courses": []}
        spec_map[sid]["courses"].append(str(rec["code"]))

    # -- Bridge courses (required as prereqs but not part of the program) --
    bridge_courses: list[dict] = []
    for rec in session.run(
        """
        MATCH (pc:Course)-[:PART_OF]->(p:Program {entity_id: $pid})
        MATCH (pc)-[:REQUIRES]->(bridge:Course)
        WHERE NOT (bridge)-[:PART_OF]->(p)
        RETURN DISTINCT bridge.course_code AS code, bridge.title AS title, bridge.units AS units
        """,
        pid=program_id,
    ):
        bridge_courses.append(_course_dict(str(rec["code"]), str(rec["title"]), rec["units"]))

    return {
        "program_id": program_id,
        "program_name": str(prog["name"]),
        "total_units": total_units,
        "core": {**core_meta, "courses": core_courses},
        "electives": {**elective_meta, "courses": elective_courses},
        "requirement_groups": list(req_groups_map.values()),
        "specializations": list(spec_map.values()),
        "bridge_courses": bridge_courses,
    }
