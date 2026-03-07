"""RAG search tool for LangGraph.

This module provides a RAG (Retrieval Augmented Generation) search tool that
queries the RAG API to retrieve relevant document chunks based on a user query.
"""

import datetime
from typing import Optional

import httpx
from jose import jwt
from langchain_core.tools import tool

from app.core.config import settings
from app.core.logging import logger


@tool
def rag_search(
    query: str,
    file_id: Optional[str] = None,
    k: int = 5,
) -> str:
    """Search the enrollment knowledge base using RAG (Retrieval Augmented Generation).

    Use this tool to find information from the enrollment document knowledge base.
    When you do not specify a file_id, the tool searches across all documents in the
    knowledge base and returns the most relevant chunks from any document. Use file_id
    only when the user asks about a specific known document.

    Args:
        query: The search query or question to find relevant information (e.g. deadlines, requirements, how to enroll).
        file_id: Optional. The ID of a specific document to search within. Omit to search all enrollment documents.
        k: Number of relevant chunks to retrieve (default: 5). Use more when searching all documents.

    Returns:
        A formatted string of relevant document chunks, or an error message.
    """
    try:
        rag_url = f"{settings.RAG_BASE_URL}/query"

        jwt_secret = settings.JWT_SECRET_KEY
        if not jwt_secret:
            logger.warning("JWT_SECRET_KEY not set, RAG queries may fail authentication")
            return "Error: RAG API authentication not configured. Please set JWT_SECRET_KEY."

        payload = {
            "id": "agent-api-user",
            "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1),
        }
        token = jwt.encode(payload, jwt_secret, algorithm="HS256")

        request_body = {
            "query": query,
            "k": k,
            "entity_id": None,
        }
        if file_id is not None:
            request_body["file_id"] = file_id

        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                rag_url,
                json=request_body,
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
            results = response.json()

        if not results or len(results) == 0:
            scope = f"document '{file_id}'" if file_id else "the knowledge base"
            return f"No relevant information found in {scope} for query: {query}"

        formatted_chunks = []
        for result in results:
            if isinstance(result, list) and len(result) > 0:
                doc = result[0]
                score = result[1] if len(result) > 1 else None
                page_content = doc.get("page_content", "")
                if page_content:
                    score_str = f" (relevance: {score:.3f})" if score is not None else ""
                    source = doc.get("metadata", {}).get("file_id", "")
                    source_str = f" [source: {source}]" if source else ""
                    formatted_chunks.append(f"{page_content}{score_str}{source_str}")

        if not formatted_chunks:
            scope = f"document '{file_id}'" if file_id else "the knowledge base"
            return f"No readable content found in {scope} for query: {query}"

        combined_content = "\n\n---\n\n".join(formatted_chunks)
        scope_label = f"document '{file_id}'" if file_id else "the knowledge base (multiple documents)"
        return f"Found {len(formatted_chunks)} relevant chunks from {scope_label}:\n\n{combined_content}"

    except httpx.HTTPStatusError as e:
        error_msg = f"RAG API returned error {e.response.status_code}: {e.response.text}"
        logger.error("rag_search_http_error", error=error_msg, query=query, file_id=file_id)
        return f"Error querying RAG API: {error_msg}"

    except httpx.RequestError as e:
        error_msg = f"Failed to connect to RAG API: {str(e)}"
        logger.error("rag_search_connection_error", error=error_msg, query=query, file_id=file_id)
        return f"Error: Could not connect to RAG API. Make sure RAG_BASE_URL is set correctly."

    except Exception as e:
        error_msg = f"Unexpected error in RAG search: {str(e)}"
        logger.error("rag_search_error", error=error_msg, query=query, file_id=file_id, exc_info=True)
        return f"Error: {error_msg}"


rag_search_tool = rag_search
