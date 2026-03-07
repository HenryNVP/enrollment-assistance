"""
Shared fixtures for API tests. Services (Agent API, RAG API) must be running.
Skip tests if a service is unreachable.
"""
import os
import time
from pathlib import Path

import pytest
import requests

# Base URLs from env (CI-friendly)
AGENT_API_URL = os.environ.get("AGENT_API_URL", "http://localhost:8000")
RAG_API_URL = os.environ.get("RAG_API_URL", "http://localhost:8010")


def _agent_reachable():
    try:
        r = requests.get(f"{AGENT_API_URL}/health", timeout=3)
        return r.ok and ("healthy" in (r.text or "").lower() or "up" in (r.text or "").lower())
    except Exception:
        return False


def _rag_reachable():
    try:
        r = requests.get(f"{RAG_API_URL}/health", timeout=3)
        return r.ok and ("up" in (r.text or "").lower() or "healthy" in (r.text or "").lower())
    except Exception:
        return False


@pytest.fixture(scope="module")
def agent_url():
    return AGENT_API_URL


@pytest.fixture(scope="module")
def rag_url():
    return RAG_API_URL


@pytest.fixture(scope="module")
def agent_session(agent_url):
    """Register (or login), create session; return session token. Skip if Agent API down."""
    if not _agent_reachable():
        pytest.skip("Agent API not reachable (start stack or set AGENT_API_URL)")
    email = f"pytest-{int(time.time())}@example.com"
    password = "Test1234!"
    # Register
    r = requests.post(
        f"{agent_url}/api/v1/auth/register",
        json={"email": email, "password": password},
        timeout=10,
    )
    if r.ok and "access_token" in (r.json() or {}).get("token", {}):
        token = r.json()["token"]["access_token"]
    elif r.status_code == 422 or ("already" in (r.text or "").lower() or "exists" in (r.text or "").lower()):
        r2 = requests.post(
            f"{agent_url}/api/v1/auth/login",
            data={"username": email, "password": password, "grant_type": "password"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10,
        )
        if not r2.ok:
            pytest.skip("Agent API login failed")
        token = (r2.json() or {}).get("access_token")
    else:
        pytest.skip("Agent API registration failed")
    if not token:
        pytest.skip("No Agent API token")
    # Session
    r3 = requests.post(
        f"{agent_url}/api/v1/auth/session",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    if not r3.ok:
        pytest.skip("Agent API session failed")
    session_token = (r3.json() or {}).get("token", {}).get("access_token")
    if not session_token:
        pytest.skip("No session token")
    return session_token


@pytest.fixture(scope="module")
def rag_token(rag_url):
    """RAG JWT token from JWT_SECRET or RAG API .env. Skip if RAG unreachable or no secret."""
    if not _rag_reachable():
        pytest.skip("RAG API not reachable (start stack or set RAG_API_URL)")
    secret = os.environ.get("JWT_SECRET", "").strip()
    if not secret:
        env_file = Path(__file__).resolve().parent.parent / "backend" / "services" / "rag_api" / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.strip().startswith("JWT_SECRET="):
                    secret = line.split("=", 1)[1].strip().strip("'\"").strip()
                    break
    if not secret:
        pytest.skip("RAG JWT_SECRET not set (backend/services/rag_api/.env or env JWT_SECRET)")
    try:
        import jwt as jwt_lib
    except ImportError:
        pytest.skip("PyJWT required for RAG tests: pip install PyJWT")
    import datetime
    payload = {
        "id": "test-user",
        "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1),
    }
    return jwt_lib.encode(payload, secret, algorithm="HS256")
