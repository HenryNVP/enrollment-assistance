from __future__ import annotations

from typing import Optional, List, Any

from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    force_rebuild: bool = Field(
        default=False,
        description="If true, clears all LightRAG documents before scanning.",
    )
    workspace: Optional[str] = Field(
        default=None,
        description="Optional LightRAG workspace identifier to use via LIGHTRAG-WORKSPACE header.",
    )


class IngestResponse(BaseModel):
    cleared: bool = Field(
        default=False,
        description="Whether LightRAG documents were cleared.",
    )
    scan_track_id: Optional[str] = Field(
        default=None,
        description="LightRAG scan tracking id (if scan started).",
    )


class PrereqsRequest(BaseModel):
    course_code: str = Field(
        ...,
        min_length=2,
        description="Course code to look up (e.g., CMPE-295A).",
    )
    depth: int = Field(
        default=2,
        ge=1,
        le=6,
        description="Max hop depth in the prereq-like graph (1=direct, >1=transitive).",
    )
    workspace: Optional[str] = Field(
        default=None,
        description="Optional LightRAG workspace identifier to use via LIGHTRAG-WORKSPACE header.",
    )


class PrereqsResponse(BaseModel):
    course_code: str
    depth: int
    label_used: str

    direct: List[str] = Field(default_factory=list)
    transitive: List[str] = Field(default_factory=list)

