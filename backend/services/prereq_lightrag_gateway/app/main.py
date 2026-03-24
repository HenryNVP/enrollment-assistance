from __future__ import annotations

import asyncio
from typing import Any, Optional, Dict, List, Set, Tuple
import os
import re
import logging
from collections import deque

from fastapi import FastAPI, HTTPException
import httpx
from neo4j import GraphDatabase

from .models import (
    IngestRequest,
    IngestResponse,
    PrereqsRequest,
    PrereqsResponse,
)
from .services.light_rag_client import LightRagClient
from .services.neo4j_curated import (
    curated_graph_enabled,
    fetch_curated_prereqs_sync,
    neo4j_driver_config,
)

logger = logging.getLogger("prereq_lightrag_gateway")

DEFAULT_LIGHTRAG_BASE_URL = os.getenv("LIGHTRAG_BASE_URL", "http://lightrag:9621")
LIGHTRAG_API_KEY = os.getenv("LIGHTRAG_API_KEY", "").strip() or None
DEFAULT_AUTO_INGEST = os.getenv("AUTO_SCAN_ON_STARTUP", "false").lower() in ("1", "true", "yes")


def _default_lightrag_workspace() -> Optional[str]:
    """Must match LightRAG's Neo4j workspace (often NEO4J_WORKSPACE in LightRAG .env)."""
    w = (os.getenv("LIGHTRAG_WORKSPACE") or os.getenv("NEO4J_WORKSPACE") or "").strip()
    return w or None

# Light heuristic keywords. LightRAG relation text varies by dataset, so we filter on broad terms.
PREREQ_KEYWORDS = [
    "prerequisite",
    "prereq",
    "pre-requisite",
    "requires",
    "required",
    "requirement",
    "must take",
    "take before",
    "one of",  # catalog: "one of CMPE 252, CMPE 255, or CMPE 257"
    "prior",
    "depend",
]


def normalize_course_code(code: str) -> str:
    """Normalize user input and graph node labels to a canonical form like CMPE-260."""
    code = code.strip().upper()
    code = code.replace("/", "-")
    # Pull SUBJECT-NNN from noisy LLM labels, e.g. "Course CMPE-260", "CMPE 260".
    m = re.search(r"\b([A-Z]{2,6})[-\s]?(\d{3}[A-Z]?)\b", code)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    code = re.sub(r"\s+", "", code)
    # Insert hyphen between subject and first digit if missing (e.g., CMPE295A -> CMPE-295A)
    code = re.sub(r"^([A-Z]{2,6})(\d)", r"\1-\2", code)
    return code


def _dedupe_preserve(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in items:
        if not x or x in seen:
            continue
        seen.add(x)
        out.append(x)
    return out


def _entity_id_candidates(course_code: str, course_code_norm: str) -> list[str]:
    """Labels LightRAG Neo4j often uses for courses (entity_id), e.g. 'Course CMPE-255'."""
    raw = course_code.strip()
    spaced = course_code_norm.replace("-", " ")  # CMPE 260
    return _dedupe_preserve(
        [
            course_code_norm,
            spaced,
            raw,
            f"Course {course_code_norm}",
            f"Course {spaced}",
        ]
    )


async def _get_lightrag_graph(
    client: LightRagClient,
    workspace: Optional[str],
    label: str,
    depth: int,
    max_nodes: int,
) -> dict[str, Any]:
    return await client.get_graph(
        label=label,
        max_depth=depth,
        max_nodes=max_nodes,
        workspace=workspace,
    )


async def _resolve_course_subgraph(
    client: LightRagClient,
    workspace: Optional[str],
    course_code: str,
    course_code_norm: str,
    depth: int,
    max_nodes: int,
) -> tuple[dict[str, Any], str]:
    """
    Find a non-empty subgraph for a course. LightRAG full-text label search often misses
    queries like 'CMPE 260' when entity_id is 'Course CMPE-260', so we try explicit labels.
    """
    search_queries = _dedupe_preserve(
        [
            course_code.strip(),
            course_code_norm,
            f"Course {course_code_norm}",
        ]
    )
    seen_labels: set[str] = set()
    for q in search_queries:
        try:
            matches = await client.label_search(q=q, limit=10, workspace=workspace)
        except Exception:
            matches = []
        for lab in matches:
            if lab in seen_labels:
                continue
            seen_labels.add(lab)
            graph = await _get_lightrag_graph(
                client, workspace, lab, depth, max_nodes
            )
            if graph.get("nodes"):
                return graph, lab

    for lab in _entity_id_candidates(course_code, course_code_norm):
        if lab in seen_labels:
            continue
        seen_labels.add(lab)
        graph = await _get_lightrag_graph(client, workspace, lab, depth, max_nodes)
        if graph.get("nodes"):
            return graph, lab

    # Last attempt: canonical code (may be empty; caller handles)
    fallback = course_code_norm
    graph = await _get_lightrag_graph(
        client, workspace, fallback, depth, max_nodes
    )
    return graph, fallback


def _prereqs_lightrag_response(
    course_code: str,
    depth: int,
    label_used: str,
    direct: list[str],
    transitive: list[str],
) -> PrereqsResponse:
    return PrereqsResponse(
        course_code=course_code,
        depth=depth,
        label_used=label_used,
        direct=direct,
        transitive=transitive,
        source="lightrag",
        requires_one_of=None,
    )


def _prereqs_lightrag_unavailable(
    course_code: str, depth: int, label_used: str
) -> PrereqsResponse:
    return PrereqsResponse(
        course_code=course_code,
        depth=depth,
        label_used=label_used,
        direct=[],
        transitive=[],
        source="lightrag_unavailable",
        requires_one_of=None,
    )


def _edge_text(edge_properties: dict[str, Any]) -> str:
    description = edge_properties.get("description") or edge_properties.get("description_text") or ""
    keywords = edge_properties.get("keywords") or ""
    return f"{description} {keywords}".lower()


def _contains_any(text: str, keywords: List[str]) -> bool:
    for kw in keywords:
        if kw in text:
            return True
    return False


def _bfs_distances(
    adjacency: Dict[str, Set[str]],
    start_nodes: Set[str],
    max_depth: int,
) -> Dict[str, int]:
    if not start_nodes:
        return {}
    visited: Dict[str, int] = {}
    q: deque[Tuple[str, int]] = deque()
    for s in start_nodes:
        visited[s] = 0
        q.append((s, 0))
    while q:
        node, depth = q.popleft()
        if depth >= max_depth:
            continue
        for nbr in adjacency.get(node, set()):
            if nbr in visited:
                continue
            visited[nbr] = depth + 1
            q.append((nbr, depth + 1))
    return visited


app = FastAPI(title="Prereq LightRAG Gateway", version="1.0.0")


@app.on_event("startup")
async def _startup() -> None:
    base_url = DEFAULT_LIGHTRAG_BASE_URL
    app.state.lightrag = LightRagClient(base_url=base_url, api_key=LIGHTRAG_API_KEY)
    app.state.auto_scan = DEFAULT_AUTO_INGEST
    app.state.default_workspace = _default_lightrag_workspace()
    app.state.neo4j_driver = None
    if curated_graph_enabled():
        cfg = neo4j_driver_config()
        if cfg["password"]:
            try:
                app.state.neo4j_driver = GraphDatabase.driver(
                    cfg["uri"],
                    auth=(cfg["user"], cfg["password"]),
                )
                logger.info("neo4j_curated_driver_ready uri=%s", cfg["uri"])
            except Exception as e:
                logger.warning("neo4j_curated_driver_failed: %s", e, exc_info=True)
        else:
            logger.warning(
                "CURATED_GRAPH_ENABLED but NEO4J_PASSWORD empty; curated prereqs disabled"
            )
    if app.state.default_workspace:
        logger.info("LighRAG workspace default=%s", app.state.default_workspace)
    if app.state.auto_scan:
        try:
            res = await app.state.lightrag.scan_for_new_documents(
                workspace=app.state.default_workspace
            )
            logger.info("auto_scan_started track_id=%s", res.get("track_id"))
        except Exception as e:
            logger.warning("auto_scan_failed: %s", str(e), exc_info=True)


@app.on_event("shutdown")
async def _shutdown() -> None:
    lr = getattr(app.state, "lightrag", None)
    if lr is not None:
        try:
            await lr.aclose()
        except Exception:
            pass
    drv = getattr(app.state, "neo4j_driver", None)
    if drv is not None:
        try:
            drv.close()
        except Exception:
            pass


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "UP"}


@app.post("/ingest", response_model=IngestResponse)
async def ingest(req: IngestRequest) -> IngestResponse:
    """
    Trigger LightRAG document scanning into its knowledge graph.

    Assumes LightRAG's `INPUT_DIR` already contains the prerequisite source documents.
    If `force_rebuild` is true, LightRAG's document store is cleared first.
    """
    try:
        client: LightRagClient = app.state.lightrag
        ws = req.workspace or app.state.default_workspace

        if req.force_rebuild:
            await client.clear_documents(workspace=ws)

        scan = await client.scan_for_new_documents(workspace=ws)
        return IngestResponse(
            cleared=bool(req.force_rebuild),
            scan_track_id=scan.get("track_id"),
        )
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        logger.exception("ingest_failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/prereqs", response_model=PrereqsResponse)
async def prereqs(req: PrereqsRequest) -> PrereqsResponse:
    """
    Look up direct/transitive prereqs for a course code using LightRAG's KG subgraph.

    This gateway filters relationships using prerequisite-like keywords.
    """
    client: LightRagClient = app.state.lightrag

    depth = min(req.depth, 6)
    max_nodes = 500

    course_code_norm = normalize_course_code(req.course_code)
    try:
        drv = getattr(app.state, "neo4j_driver", None)
        if drv is not None:

            def _curated_lookup() -> Optional[dict[str, Any]]:
                with drv.session() as session:
                    return fetch_curated_prereqs_sync(
                        session, course_code_norm, depth, req.course_code
                    )

            try:
                curated = await asyncio.to_thread(_curated_lookup)
            except Exception as e:
                logger.warning("curated_prereqs_failed: %s", e, exc_info=True)
                curated = None
            if curated is not None:
                return PrereqsResponse(**curated)

        workspace = req.workspace or app.state.default_workspace
        try:
            graph, label_used = await _resolve_course_subgraph(
                client,
                workspace,
                req.course_code,
                course_code_norm,
                depth,
                max_nodes,
            )
        except httpx.HTTPError as e:
            logger.warning("lightrag_prereqs_unavailable: %s", e, exc_info=True)
            return PrereqsResponse(
                course_code=req.course_code,
                depth=depth,
                label_used=course_code_norm,
                direct=[],
                transitive=[],
                source="lightrag_unavailable",
                requires_one_of=None,
            )

        nodes = graph.get("nodes") or []
        edges = graph.get("edges") or []

        if not nodes:
            return _prereqs_lightrag_response(
                req.course_code, depth, label_used, [], []
            )

        # Build node id -> normalized course code for matching.
        node_norm: Dict[str, str] = {}
        for n in nodes:
            node_id = str(n.get("id", ""))
            if not node_id:
                continue
            node_norm[node_id] = normalize_course_code(node_id)

        start_nodes: Set[str] = {nid for nid, norm in node_norm.items() if norm == course_code_norm}
        if not start_nodes:
            # Fallback: match by raw label_used (sometimes entity_id already equals label)
            start_nodes = {str(x.get("id")) for x in nodes if str(x.get("id")) == str(label_used)}

        # Filter edges into prereq-like adjacency.
        prereq_adj: Dict[str, Set[str]] = {}
        prereq_kw = PREREQ_KEYWORDS

        for e in edges:
            src = str(e.get("source", ""))
            tgt = str(e.get("target", ""))
            props = e.get("properties") or {}
            if not src or not tgt:
                continue

            edge_txt = _edge_text(props)
            is_prereq = _contains_any(edge_txt, prereq_kw)

            if is_prereq:
                prereq_adj.setdefault(src, set()).add(tgt)
                prereq_adj.setdefault(tgt, set()).add(src)

        distances = _bfs_distances(prereq_adj, start_nodes, max_depth=depth)
        direct = [node for node, d in distances.items() if d == 1]
        transitive = [node for node, d in distances.items() if 1 <= d <= depth]

        # Convert back to normalized course codes.
        direct_norm = sorted({node_norm.get(n, n) for n in direct})
        transitive_norm = sorted({node_norm.get(n, n) for n in transitive})

        return _prereqs_lightrag_response(
            req.course_code, depth, label_used, direct_norm, transitive_norm
        )
    except Exception as e:
        logger.exception("prereqs_failed", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

