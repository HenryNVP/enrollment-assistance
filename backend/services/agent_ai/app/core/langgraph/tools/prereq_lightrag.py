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
    """Get course prerequisites (direct + transitive) from LightRAG.

    Returns a JSON string with:
    - direct
    - transitive
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

