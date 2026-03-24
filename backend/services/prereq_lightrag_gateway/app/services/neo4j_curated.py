"""Curated MS-AI course graph in Neo4j (:Course, :REQUIRES) — deterministic prereqs."""

from __future__ import annotations

import os
from typing import Any, Optional, Set, Tuple

SOURCE_FILE = "curriculum_msai.yaml"


def curated_graph_enabled() -> bool:
    return os.getenv("CURATED_GRAPH_ENABLED", "").strip().lower() in ("1", "true", "yes")


def neo4j_driver_config() -> dict[str, str]:
    return {
        "uri": os.getenv("NEO4J_URI", os.getenv("NEO4J_URI_BOLT", "bolt://localhost:7687")),
        "user": os.getenv("NEO4J_USERNAME", os.getenv("NEO4J_USER", "neo4j")),
        "password": os.getenv("NEO4J_PASSWORD", ""),
    }


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


def _transitive_and_only(
    session: Any,
    course_code: str,
    depth: int,
) -> Set[str]:
    """
    Shortest AND-only chains (excludes OR edges). One Cypher query vs BFS per frontier.
    """
    dmax = min(depth, 6)
    result = session.run(
        """
        MATCH path = (c:Course {course_code: $code})-[:REQUIRES*1..6]->(p:Course)
        WHERE ALL(rel IN relationships(path) WHERE coalesce(rel.or_group, false) = false)
          AND length(path) <= $depth
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
    """
    Returns a dict suitable for PrereqsResponse, or None if course not in curated graph.
    """
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

    transitive_set = _transitive_and_only(session, course_code_norm, min(depth, 6))

    return {
        "course_code": course_code_for_response,
        "depth": depth,
        "label_used": f"curated:{course_code_norm}",
        "direct": sorted(direct_set),
        "transitive": sorted(transitive_set),
        "source": "curated",
        "requires_one_of": one_of_merged if one_of_merged else None,
    }
