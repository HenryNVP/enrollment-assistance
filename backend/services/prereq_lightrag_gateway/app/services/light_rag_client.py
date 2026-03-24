from __future__ import annotations

from typing import Any, Optional
import urllib.parse

import httpx


class LightRagClient:
    """HTTP client for LightRAG graph APIs. Reuses one AsyncClient for connection pooling."""

    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        timeout_s: float = 60.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._timeout = httpx.Timeout(timeout_s)
        self._client = httpx.AsyncClient(timeout=self._timeout)
        self._base_headers: dict[str, str] = {}
        if api_key:
            self._base_headers["X-API-Key"] = api_key

    async def aclose(self) -> None:
        await self._client.aclose()

    def _workspace_headers(self, workspace: Optional[str]) -> dict[str, str]:
        if not workspace:
            return {}
        return {"LIGHTRAG-WORKSPACE": workspace}

    def _auth_headers(self, workspace: Optional[str]) -> dict[str, str]:
        headers = dict(self._base_headers)
        headers.update(self._workspace_headers(workspace))
        return headers

    async def clear_documents(self, workspace: Optional[str] = None) -> None:
        url = f"{self.base_url}/documents"
        resp = await self._client.delete(url, headers=self._auth_headers(workspace))
        resp.raise_for_status()

    async def scan_for_new_documents(
        self, workspace: Optional[str] = None
    ) -> dict[str, Any]:
        url = f"{self.base_url}/documents/scan"
        resp = await self._client.post(url, headers=self._auth_headers(workspace))
        resp.raise_for_status()
        return resp.json()

    async def label_search(
        self,
        q: str,
        limit: int = 5,
        workspace: Optional[str] = None,
    ) -> list[str]:
        params = {"q": q, "limit": limit}
        url = f"{self.base_url}/graph/label/search?{urllib.parse.urlencode(params)}"
        resp = await self._client.get(url, headers=self._auth_headers(workspace))
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            return [str(x) for x in data]
        return []

    async def get_graph(
        self,
        label: str,
        max_depth: int,
        max_nodes: int,
        workspace: Optional[str] = None,
    ) -> dict[str, Any]:
        params = {
            "label": label,
            "max_depth": max_depth,
            "max_nodes": max_nodes,
        }
        url = f"{self.base_url}/graphs?{urllib.parse.urlencode(params)}"
        resp = await self._client.get(url, headers=self._auth_headers(workspace))
        resp.raise_for_status()
        return resp.json()
