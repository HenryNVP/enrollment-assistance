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
    file_id: str,
    k: int = 3,
) -> str:
    """Search documents using RAG (Retrieval Augmented Generation).

    Use this tool when you need to find information from uploaded documents.
    This tool queries the RAG API to retrieve relevant document chunks that
    match the user's query.

    Args:
        query: The search query/question to find relevant information
        file_id: The ID of the document/file to search within
        k: Number of relevant chunks to retrieve (default: 3)

    Returns:
        A formatted string containing the relevant document chunks, or an error message
    """
    try:
        # Get RAG API base URL from settings
        rag_url = f"{settings.RAG_BASE_URL}/query"

        # Get JWT secret for authentication (should match RAG API's JWT_SECRET)
        jwt_secret = settings.JWT_SECRET_KEY
        if not jwt_secret:
            logger.warning("JWT_SECRET_KEY not set, RAG queries may fail authentication")
            return "Error: RAG API authentication not configured. Please set JWT_SECRET_KEY."

        # Generate a simple JWT token for RAG API
        # Note: In production, you might want to use the actual user's token
        payload = {
            "id": "agent-api-user",  # Default user ID for agent-initiated queries
            "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1),
        }
        token = jwt.encode(payload, jwt_secret, algorithm="HS256")

        # Prepare request body
        # Note: entity_id can be used to scope documents to a specific user
        # For now, we'll use None to search all accessible documents
        request_body = {
            "query": query,
            "file_id": file_id,
            "k": k,
            "entity_id": None,  # Can be set to user_id if needed
        }

        # Make request to RAG API
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                rag_url,
                json=request_body,
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
            results = response.json()

        # Format results for the LLM
        if not results or len(results) == 0:
            return f"No relevant information found in document '{file_id}' for query: {query}"

        # RAG API returns array of [document, score] pairs
        formatted_chunks = []
        for result in results:
            if isinstance(result, list) and len(result) > 0:
                doc = result[0]
                score = result[1] if len(result) > 1 else None
                page_content = doc.get("page_content", "")
                if page_content:
                    score_str = f" (relevance: {score:.3f})" if score is not None else ""
                    formatted_chunks.append(f"{page_content}{score_str}")

        if not formatted_chunks:
            return f"No readable content found in document '{file_id}' for query: {query}"

        # Combine all chunks into a single response
        combined_content = "\n\n---\n\n".join(formatted_chunks)
        return f"Found {len(formatted_chunks)} relevant chunks from document '{file_id}':\n\n{combined_content}"

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
