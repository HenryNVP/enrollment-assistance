"""Prerequisite Gateway — serves curated course prerequisites and program structure from Neo4j."""

from __future__ import annotations

import asyncio
from typing import Any, Optional
import logging

from fastapi import FastAPI, HTTPException
from neo4j import GraphDatabase

from .models import (
    PrereqsRequest,
    PrereqsResponse,
    ProgramRequest,
    ProgramResponse,
)
from .services.neo4j_curated import (
    fetch_curated_prereqs_sync,
    fetch_program_structure_sync,
    neo4j_driver_config,
    normalize_course_code,
)

logger = logging.getLogger("rag_graph")

app = FastAPI(title="Prerequisite Gateway", version="2.0.0")


@app.on_event("startup")
async def _startup() -> None:
    app.state.neo4j_driver = None
    app.state.neo4j_database = None
    cfg = neo4j_driver_config()
    if cfg["password"]:
        try:
            app.state.neo4j_driver = GraphDatabase.driver(
                cfg["uri"],
                auth=(cfg["user"], cfg["password"]),
            )
            app.state.neo4j_database = cfg["database"]
            logger.info("neo4j_driver_ready uri=%s database=%s", cfg["uri"], cfg["database"])
        except Exception as e:
            logger.error("neo4j_driver_failed: %s", e, exc_info=True)
    else:
        logger.error("NEO4J_PASSWORD not set; gateway will return errors")


@app.on_event("shutdown")
async def _shutdown() -> None:
    drv = getattr(app.state, "neo4j_driver", None)
    if drv is not None:
        try:
            drv.close()
        except Exception:
            pass


def _require_neo4j() -> Any:
    drv = getattr(app.state, "neo4j_driver", None)
    if drv is None:
        raise HTTPException(status_code=503, detail="Neo4j not available")
    return drv


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "UP"}


@app.post("/prereqs", response_model=PrereqsResponse)
async def prereqs(req: PrereqsRequest) -> PrereqsResponse:
    """Look up direct and transitive prerequisites for a single course."""
    drv = _require_neo4j()
    course_code_norm = normalize_course_code(req.course_code)
    depth = min(req.depth, 6)

    db = app.state.neo4j_database

    def _lookup() -> Optional[dict[str, Any]]:
        with drv.session(database=db) as session:
            return fetch_curated_prereqs_sync(session, course_code_norm, depth, req.course_code)

    try:
        result = await asyncio.to_thread(_lookup)
    except Exception as e:
        logger.exception("prereqs_failed")
        raise HTTPException(status_code=500, detail=str(e))

    if result is None:
        return PrereqsResponse(
            course_code=req.course_code,
            depth=depth,
            direct=[],
            transitive=[],
            source="curated",
            requires_one_of=None,
        )

    return PrereqsResponse(**result)


@app.post("/program", response_model=ProgramResponse)
async def program(req: ProgramRequest) -> ProgramResponse:
    """Return the full program structure: courses, groups, prereqs, specializations."""
    drv = _require_neo4j()

    db = app.state.neo4j_database

    def _lookup() -> Optional[dict[str, Any]]:
        with drv.session(database=db) as session:
            return fetch_program_structure_sync(session, req.program_id)

    try:
        result = await asyncio.to_thread(_lookup)
    except Exception as e:
        logger.exception("program_lookup_failed")
        raise HTTPException(status_code=500, detail=str(e))

    if result is None:
        raise HTTPException(status_code=404, detail=f"Program '{req.program_id}' not found")

    return ProgramResponse(**result)
