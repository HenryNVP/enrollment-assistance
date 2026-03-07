"""
End-to-end: RAG query (existing store) + Agent chat
Requires both RAG API and Agent API running; vector store populated (entity_id=public).
"""
import pytest
import requests

from tests.conftest import _agent_reachable, _rag_reachable


def test_rag_then_agent_chat(agent_url, rag_url, rag_token, agent_session):
    """Query RAG for MS AI, then ask Agent the same; verify response and history."""
    if not _rag_reachable() or not _agent_reachable():
        pytest.skip("RAG or Agent API not reachable")
    # 1. RAG query
    r = requests.post(
        f"{rag_url}/query",
        headers={"Authorization": f"Bearer {rag_token}"},
        json={
            "query": "How many credits does the MS AI program require? What are the core courses and some specialization or elective courses?",
            "k": 5,
            "entity_id": "public",
        },
        timeout=15,
    )
    assert r.ok, r.text
    rag_data = r.json()
    assert isinstance(rag_data, list)
    # 2. Agent chat
    chat_r = requests.post(
        f"{agent_url}/api/v1/chatbot/chat",
        headers={"Authorization": f"Bearer {agent_session}"},
        json={
            "messages": [
                {
                    "role": "user",
                    "content": "How many credits does the MS in Artificial Intelligence program require, and what are some core and specialization courses?",
                }
            ]
        },
        timeout=60,
    )
    assert chat_r.ok, chat_r.text
    chat_data = chat_r.json() or {}
    assert "messages" in chat_data
    msgs = chat_data.get("messages", [])
    assistant = next((m for m in reversed(msgs) if m.get("role") == "assistant"), None)
    assert assistant is not None
    content = (assistant.get("content") or "").strip()
    assert len(content) > 0
    # 3. History
    hist_r = requests.get(
        f"{agent_url}/api/v1/chatbot/messages",
        headers={"Authorization": f"Bearer {agent_session}"},
        timeout=10,
    )
    assert hist_r.ok
    assert len((hist_r.json() or {}).get("messages", [])) > 0
