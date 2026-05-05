"""Synapse Layer — Simple Sync Client.

Minimal sync HTTP client for Forge API. AES-256-GCM encryption at rest
is handled server-side; this client sends plaintext over HTTPS.

Usage::

    from synapse_layer import Synapse

    s = Synapse(token="sk_connect_YOUR_TOKEN")
    s.save("user prefers dark mode")
    results = s.recall("user preferences")
    for r in results:
        print(r["content"])

Get your token at https://forge.synapselayer.org → Dashboard → Connect
"""

from __future__ import annotations

import os
import sys
import time
from typing import Any, Dict, List, Optional

import requests


_DEFAULT_BASE_URL = os.environ.get(
    "SYNAPSE_FORGE_URL", "https://forge.synapselayer.org"
)
_DEFAULT_TIMEOUT = 15
_DEFAULT_AGENT = "sdk-client"


class SynapseError(Exception):
    """Base exception for Synapse client errors."""


class SynapseAuthError(SynapseError):
    """Authentication failed (401)."""


class SynapseRateLimitError(SynapseError):
    """Rate limit exceeded (429)."""


class Synapse:
    """Synchronous Synapse client — minimal one-liner API.

    Args:
        token: ``sk_connect_*`` token. Also accepts ``api_key`` kwarg
            or ``SYNAPSE_TOKEN`` env var.
        base_url: Forge base URL. Defaults to ``https://forge.synapselayer.org``.
        agent_id: Agent identifier for memory tagging.
        timeout: HTTP timeout in seconds.
    """

    def __init__(
        self,
        token: Optional[str] = None,
        *,
        api_key: Optional[str] = None,
        base_url: str = _DEFAULT_BASE_URL,
        agent_id: str = _DEFAULT_AGENT,
        timeout: int = _DEFAULT_TIMEOUT,
    ) -> None:
        resolved = token or api_key or os.environ.get("SYNAPSE_TOKEN", "")
        if not resolved:
            print(
                "\n\u274c Missing SYNAPSE_TOKEN — get one at "
                "https://forge.synapselayer.org/dashboard/connect\n",
                file=sys.stderr,
            )
            raise SynapseAuthError(
                "Missing token. Set SYNAPSE_TOKEN env var or pass token= argument. "
                "Get your token at https://forge.synapselayer.org/dashboard/connect"
            )
        if not resolved.startswith("sk_connect_"):
            raise SynapseAuthError(
                "Token must start with 'sk_connect_' — "
                "get one at https://forge.synapselayer.org/dashboard/connect"
            )

        self._token = resolved
        self._base = base_url.rstrip("/")
        self._agent = agent_id
        self._timeout = timeout
        self._session: Optional[requests.Session] = None

    def _get_session(self) -> requests.Session:
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update({
                "x-connect-token": self._token,
                "Content-Type": "application/json",
            })
        return self._session

    # ── Store ──────────────────────────────────────────────────────

    def save(self, content: str, **kwargs: Any) -> Dict[str, Any]:
        """Save a memory to Synapse.

        Args:
            content: Text to persist in encrypted memory.
            **kwargs: Optional overrides (memory_type, metadata, agent).

        Returns:
            Dict with memory_id, tq_score, and other metadata.
        """
        payload: Dict[str, Any] = {
            "content": content,
            "agent": kwargs.get("agent", self._agent),
            "memory_type": kwargs.get("memory_type", "long_term"),
        }
        if "metadata" in kwargs:
            payload["metadata"] = kwargs["metadata"]

        session = self._get_session()
        resp = session.post(
            f"{self._base}/api/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "save_to_synapse",
                    "arguments": payload,
                },
                "id": 1,
            },
            timeout=self._timeout,
        )
        return self._handle(resp)

    def remember(self, content: str, **kwargs: Any) -> Dict[str, Any]:
        """Alias for :meth:`save`."""
        return self.save(content, **kwargs)

    def store(self, content: str, **kwargs: Any) -> Dict[str, Any]:
        """Alias for :meth:`save`."""
        return self.save(content, **kwargs)

    # ── Recall ─────────────────────────────────────────────────────

    def recall(self, query: str, *, limit: int = 5) -> List[Dict[str, Any]]:
        """Recall relevant memories.

        Args:
            query: Natural language query.
            limit: Max results (default 5).

        Returns:
            List of memory dicts with content, trust_quotient, etc.
        """
        session = self._get_session()
        resp = session.post(
            f"{self._base}/api/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "recall",
                    "arguments": {"query": query, "limit": limit},
                },
                "id": 2,
            },
            timeout=self._timeout,
        )
        data = self._handle(resp)
        # Extract memories list from MCP tool response
        if isinstance(data, dict):
            # MCP returns {content: [{type: "text", text: JSON}]}
            content_list = data.get("content", [])
            if content_list and isinstance(content_list, list):
                import json as _json
                try:
                    text = content_list[0].get("text", "{}")
                    parsed = _json.loads(text)
                    return parsed.get("memories", [])
                except (ValueError, KeyError, IndexError):
                    pass
            return data.get("memories", [])
        return []

    # ── Helpers ────────────────────────────────────────────────────

    def _handle(self, resp: requests.Response) -> Dict[str, Any]:
        if resp.status_code == 401:
            raise SynapseAuthError(f"Authentication failed (401): {resp.text[:200]}")
        if resp.status_code == 429:
            raise SynapseRateLimitError(f"Rate limit exceeded (429)")
        if resp.status_code != 200:
            raise SynapseError(f"Request failed ({resp.status_code}): {resp.text[:200]}")

        data = resp.json()
        if "error" in data:
            err = data["error"]
            msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
            raise SynapseError(f"API error: {msg}")

        return data.get("result", data)

    def close(self) -> None:
        """Close the HTTP session."""
        if self._session:
            self._session.close()
            self._session = None

    def __enter__(self) -> "Synapse":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def __repr__(self) -> str:
        return f"Synapse(agent='{self._agent}', base='{self._base}')"
