"""
Agent API tests
Requires Agent API running. Skips if unreachable.
"""
import pytest
import requests

from tests.conftest import AGENT_API_URL, _agent_reachable


def test_agent_health():
    """Health check."""
    if not _agent_reachable():
        pytest.skip("Agent API not reachable")
    r = requests.get(f"{AGENT_API_URL}/health", timeout=5)
    assert r.ok
    assert "healthy" in (r.text or "").lower() or "up" in (r.text or "").lower()


def test_agent_register_session(agent_session):
    """Register or login and create session (fixture does the work)."""
    assert agent_session


def test_agent_chat(agent_url, agent_session):
    """Send chat message and get response."""
    r = requests.post(
        f"{agent_url}/api/v1/chatbot/chat",
        headers={"Authorization": f"Bearer {agent_session}"},
        json={"messages": [{"role": "user", "content": "Hello! Can you help me?"}]},
        timeout=30,
    )
    assert r.ok, r.text
    data = r.json() or {}
    assert "messages" in data
    msgs = data.get("messages", [])
    assert len(msgs) >= 1
    last = next((m for m in reversed(msgs) if m.get("role") == "assistant"), None)
    assert last is not None
    assert last.get("content")


def test_agent_history(agent_url, agent_session):
    """Get chat history."""
    r = requests.get(
        f"{agent_url}/api/v1/chatbot/messages",
        headers={"Authorization": f"Bearer {agent_session}"},
        timeout=10,
    )
    assert r.ok
    data = r.json() or {}
    assert "messages" in data
    assert isinstance(data["messages"], list)
