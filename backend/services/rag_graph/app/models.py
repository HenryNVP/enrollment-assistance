from __future__ import annotations

from typing import Optional, List

from pydantic import BaseModel, Field


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
        description="Max hop depth for transitive prereqs (1=direct only, >1=transitive).",
    )


class PrereqsResponse(BaseModel):
    course_code: str
    depth: int
    direct: List[str] = Field(default_factory=list)
    transitive: List[str] = Field(default_factory=list)
    requires_one_of: Optional[List[str]] = Field(
        default=None,
        description="OR-style alternatives: satisfy any one of these courses.",
    )
    source: str = Field(default="curated")


class ProgramRequest(BaseModel):
    program_id: str = Field(
        default="MSAI",
        description="Program entity_id in Neo4j (e.g. MSAI).",
    )


class ProgramCourse(BaseModel):
    course_code: str
    title: str
    units: float
    requires_all: List[str] = Field(default_factory=list)
    requires_one_of: List[str] = Field(default_factory=list)


class CourseGroup(BaseModel):
    group_id: str
    name: str
    min_units: Optional[float] = None
    courses: List[ProgramCourse] = Field(default_factory=list)


class SpecializationInfo(BaseModel):
    specialization_id: str
    name: str
    courses: List[str] = Field(default_factory=list)


class ProgramResponse(BaseModel):
    program_id: str
    program_name: str
    total_units: Optional[float] = None
    core: CourseGroup
    electives: CourseGroup
    requirement_groups: List[CourseGroup] = Field(default_factory=list)
    specializations: List[SpecializationInfo] = Field(default_factory=list)
    bridge_courses: List[ProgramCourse] = Field(
        default_factory=list,
        description="Courses not in the program but required as prerequisites.",
    )
