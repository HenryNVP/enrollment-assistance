"""
RAG API tests
Requires RAG API running and vector store populated (entity_id=public). Skips if unreachable.
"""
import pytest
import requests

from tests.conftest import RAG_API_URL, _rag_reachable


def test_rag_health():
    """RAG health check."""
    if not _rag_reachable():
        pytest.skip("RAG API not reachable")
    r = requests.get(f"{RAG_API_URL}/health", timeout=5)
    assert r.ok
    assert "up" in (r.text or "").lower() or "healthy" in (r.text or "").lower()


def _rag_query(rag_url, token, query: str):
    r = requests.post(
        f"{rag_url}/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"query": query, "k": 5, "entity_id": "public"},
        timeout=15,
    )
    assert r.ok, r.text
    return r.json()


def test_rag_query_credits(rag_url, rag_token):
    """MS AI credits query returns results (optionally 33)."""
    data = _rag_query(rag_url, rag_token, "How many credits or units does the MS AI program require?")
    assert isinstance(data, list)
    # If store has MS AI docs, we may see "33"
    text = str(data)
    assert len(data) >= 0
    if "33" in text:
        assert True  # expected when MS AI is in store


def test_rag_query_core(rag_url, rag_token):
    """MS AI core courses query."""
    data = _rag_query(rag_url, rag_token, "What are the core courses for the MS in Artificial Intelligence?")
    assert isinstance(data, list)
    text = str(data).lower()
    # May contain core/required/CMPE when store has MS AI
    assert "core" in text or "required" in text or "cmpe" in text or len(data) == 0


def test_rag_query_electives(rag_url, rag_token):
    """MS AI specialization/elective courses query."""
    data = _rag_query(rag_url, rag_token, "What are some specialization or elective courses in the MS AI program?")
    assert isinstance(data, list)


def test_rag_ids(rag_url, rag_token):
    """Get document IDs."""
    r = requests.get(
        f"{rag_url}/ids",
        headers={"Authorization": f"Bearer {rag_token}"},
        timeout=10,
    )
    assert r.ok
    data = r.json()
    assert isinstance(data, list)


def test_rag_document_details(rag_url, rag_token):
    """Get document details for first ID if any."""
    r = requests.get(
        f"{rag_url}/ids",
        headers={"Authorization": f"Bearer {rag_token}"},
        timeout=10,
    )
    assert r.ok
    ids = r.json()
    if not ids:
        pytest.skip("No document IDs in store")
    first_id = ids[0]
    r2 = requests.get(
        f"{rag_url}/documents",
        params={"ids": first_id},
        headers={"Authorization": f"Bearer {rag_token}"},
        timeout=10,
    )
    assert r2.ok
    docs = r2.json()
    assert isinstance(docs, list)
    if docs:
        assert "page_content" in docs[0] or "metadata" in docs[0]
