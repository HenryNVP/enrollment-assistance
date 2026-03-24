from __future__ import annotations

import json
import httpx
from langchain_core.tools import tool

from app.core.config import settings
from app.core.logging import logger


@tool
def course_prereqs(
    course_code: str,
    depth: int = 2,
) -> str:
    """Look up prerequisites for a specific SJSU course (CMPE/ISE/etc.).

    Call this whenever the user names a course and asks about prereqs, requirements to
    enroll, or what to take first — do not rely on rag_search alone for that.

    Pass a normal course code (e.g. "CMPE-260", "CMPE 260", "ISE-201"). Response JSON
    includes: direct (AND prereqs), requires_one_of (OR alternatives — if direct is empty
    but requires_one_of is set, the OR list is still the answer), transitive, source.

    Uses prereq_gateway: curated Neo4j when CURATED_GRAPH_ENABLED, else LightRAG subgraph.
    """
    try:
        prereq_url = f"{settings.PREREQ_GATEWAY_BASE_URL}/prereqs"

        request_body = {
            "course_code": course_code,
            "depth": depth,
        }

        with httpx.Client(timeout=60.0) as client:
            response = client.post(prereq_url, json=request_body)
            response.raise_for_status()

            payload = response.json()

        # Keep the tool output as JSON so the agent can parse it if needed.
        return json.dumps(payload)
    except httpx.HTTPStatusError as e:
        error_msg = f"Prereq gateway error {e.response.status_code}: {e.response.text}"
        logger.error("course_prereqs_http_error", error=error_msg, course_code=course_code)
        return f"Error: {error_msg}"
    except httpx.RequestError as e:
        error_msg = f"Failed to connect to prereq gateway: {str(e)}"
        logger.error("course_prereqs_connection_error", error=error_msg, course_code=course_code)
        return "Error: Could not connect to the prereq gateway. Check PREREQ_GATEWAY_BASE_URL."
    except Exception as e:
        logger.exception("course_prereqs_failed", course_code=course_code)
        return f"Error: {str(e)}"


course_prereqs_tool = course_prereqs

