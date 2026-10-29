"""Minimal client for the hosted ChemPath lab API.

The hosted service is available to registered testing labs. This client has no
default endpoint: pass ``base_url`` and ``api_key`` (or set
``CHEMPATH_BASE_URL`` and ``CHEMPATH_API_KEY``) using the details supplied
during onboarding. Every authenticated call counts toward your lab's quota.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Optional


class ChemPathAPIError(RuntimeError):
    """Non-2xx response from the hosted API."""

    def __init__(self, status: int, body: str) -> None:
        super().__init__(f"HTTP {status}: {body[:500]}")
        self.status = status
        self.body = body


class ChemPathClient:
    """Thin wrapper over the four ChemPath lab routes plus lab status."""

    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None,
                 timeout: float = 60.0) -> None:
        self.base_url = (base_url or os.environ.get("CHEMPATH_BASE_URL", "")).rstrip("/")
        self.api_key = api_key or os.environ.get("CHEMPATH_API_KEY", "")
        if not self.base_url or not self.api_key:
            raise ValueError("base_url and api_key are required (or CHEMPATH_BASE_URL / CHEMPATH_API_KEY)")
        self.timeout = timeout

    def _request(self, method: str, path: str, body: Any = None) -> bytes:
        """Send a request with the lab API key and return the raw response body."""
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(f"{self.base_url}{path}", data=data, method=method)
        req.add_header("X-API-Key", self.api_key)
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as exc:
            raise ChemPathAPIError(exc.code, exc.read().decode(errors="replace")) from exc

    def formulation(self, payload: dict[str, Any]) -> dict[str, Any]:
        """POST /api/v1/chempath/formulation."""
        return json.loads(self._request("POST", "/api/v1/chempath/formulation", payload))

    def batch(self, items: list[dict[str, Any]]) -> dict[str, Any]:
        """POST /api/v1/chempath/batch (up to 25 items)."""
        return json.loads(self._request("POST", "/api/v1/chempath/batch", {"items": items}))

    def report_json(self, analysis_id: str) -> dict[str, Any]:
        """GET /api/v1/chempath/{id}/report?format=json."""
        return json.loads(self._request("GET", f"/api/v1/chempath/{analysis_id}/report?format=json"))

    def report_pdf(self, analysis_id: str) -> bytes:
        """GET /api/v1/chempath/{id}/report (PDF bytes)."""
        return self._request("GET", f"/api/v1/chempath/{analysis_id}/report")

    def history(self, limit: int = 50, offset: int = 0) -> dict[str, Any]:
        """GET /api/v1/chempath/history."""
        return json.loads(self._request("GET", f"/api/v1/chempath/history?limit={limit}&offset={offset}"))

    def status(self) -> dict[str, Any]:
        """GET /api/lab/status — plan, limits and current usage."""
        return json.loads(self._request("GET", "/api/lab/status"))
