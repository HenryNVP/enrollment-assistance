from __future__ import annotations

from typing import Any, Optional, Dict, List, Set, Tuple
import os
import re
import logging
from collections import deque

from fastapi import FastAPI, HTTPException
import httpx

from .models import (
    IngestRequest,
    IngestResponse,
    PrereqsRequest,
    PrereqsResponse,
)
from .services.light_rag_client import LightRagClient

logger = logging.getLogger("prereq_lightrag_gateway")

DEFAULT_LIGHTRAG_BASE_URL = os.getenv("LIGHTRAG_BASE_URL", "http://lightrag:9621")
LIGHTRAG_API_KEY = os.getenv("LIGHTRAG_API_KEY", "").strip() or None
DEFAULT_AUTO_INGEST = os.getenv("AUTO_SCAN_ON_STARTUP", "false").lower() in ("1", "true", "yes")

# Light heuristic keywords. LightRAG relation text varies by dataset, so we filter on broad terms.
PREREQ_KEYWORDS = [
    "prerequisite",
    "prereq",
    "requires",
    "required",
    "must take",
    "take before",
    "pre-requisite",
]


def normalize_course_code(code: str) -> str:
    code = code.strip().upper()
    code = code.replace("/", "-")
    code = re.sub(r"\s+", "", code)
    # Insert hyphen between subject and first digit if missing (e.g., CMPE295A -> CMPE-295A)
    code = re.sub(r"^([A-Z]{2,6})(\d)", r"\1-\2", code)
    return code


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
    if app.state.auto_scan:
        try:
            res = await app.state.lightrag.scan_for_new_documents()
            logger.info("auto_scan_started track_id=%s", res.get("track_id"))
        except Exception as e:
            logger.warning("auto_scan_failed: %s", str(e), exc_info=True)


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

        if req.force_rebuild:
            await client.clear_documents(workspace=req.workspace)

        scan = await client.scan_for_new_documents(workspace=req.workspace)
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
        # Try to find the closest label in LightRAG graph.
        matches = await client.label_search(
            q=req.course_code,
            limit=5,
            workspace=req.workspace,
        )
        label_used = matches[0] if matches else course_code_norm

        graph = await client.get_graph(
            label=label_used,
            max_depth=depth,
            max_nodes=max_nodes,
            workspace=req.workspace,
        )

        nodes = graph.get("nodes") or []
        edges = graph.get("edges") or []

        if not nodes:
            return PrereqsResponse(
                course_code=req.course_code,
                depth=depth,
                label_used=label_used,
                direct=[],
                transitive=[],
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

        return PrereqsResponse(
            course_code=req.course_code,
            depth=depth,
            label_used=label_used,
            direct=direct_norm,
            transitive=transitive_norm,
        )
    except Exception as e:
        logger.exception("prereqs_failed", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

