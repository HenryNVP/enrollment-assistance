from __future__ import annotations

import json
import httpx
from langchain_core.tools import tool

from app.core.config import settings
from app.core.logging import logger


@tool
def program_requirements(
    program_id: str = "MSAI",
) -> str:
    """Retrieve the full degree program structure with all courses, prerequisites, and groups.

    Call this when the user asks about:
    - What courses are in the MS AI (or other) program
    - Degree requirements, unit counts, or what to take
    - Enrollment planning or course sequencing
    - Specialization options (Data Science, Autonomous Systems)
    - GWAR or culminating experience (thesis/project) requirements

    Returns JSON with: core courses, electives (with specialization tags),
    requirement groups (GWAR, culminating), bridge/prerequisite courses,
    and the requires_all / requires_one_of for every course.

    Use this as the starting point for any planning question, then call
    course_prereqs on individual courses only when deeper transitive chains
    are needed beyond what this response already provides.
    """
    try:
        url = f"{settings.RAG_GRAPH_BASE_URL}/program"

        with httpx.Client(timeout=60.0) as client:
            response = client.post(url, json={"program_id": program_id})
            response.raise_for_status()

            return json.dumps(response.json())
    except httpx.HTTPStatusError as e:
        error_msg = f"Program endpoint error {e.response.status_code}: {e.response.text}"
        logger.error("program_requirements_http_error", error=error_msg, program_id=program_id)
        return f"Error: {error_msg}"
    except httpx.RequestError as e:
        error_msg = f"Failed to connect to prereq gateway: {str(e)}"
        logger.error("program_requirements_connection_error", error=error_msg, program_id=program_id)
        return "Error: Could not connect to the rag_graph gateway."
    except Exception as e:
        logger.exception("program_requirements_failed", program_id=program_id)
        return f"Error: {str(e)}"


program_requirements_tool = program_requirements
