"""
pact_ax_client/_http.py
────────────────────────
Thin httpx wrapper used by all resource clients.

Handles:
- Base URL + optional API key header
- Error mapping (4xx/5xx → SDK exceptions)
- Sync and async variants
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

from .exceptions import (
    PactAXError, NotFoundError, ConflictError,
    ValidationError, ServerError, ConnectionError as PactConnError,
)


def _raise(response: httpx.Response) -> None:
    if response.is_success:
        return
    try:
        detail = response.json().get("detail", response.text)
    except Exception:
        detail = response.text

    code = response.status_code
    if code == 404:
        raise NotFoundError(detail, code)
    if code == 409:
        raise ConflictError(detail, code)
    if code == 422:
        raise ValidationError(detail, code)
    if code >= 500:
        raise ServerError(detail, code)
    raise PactAXError(detail, code)


class HttpClient:
    """Synchronous httpx client."""

    def __init__(self, base_url: str, api_key: Optional[str] = None, timeout: float = 30.0):
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["X-API-Key"] = api_key
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers=headers,
            timeout=timeout,
        )

    def get(self, path: str, **params) -> Dict:
        try:
            r = self._client.get(path, params=params or None)
        except httpx.ConnectError as exc:
            raise PactConnError(f"Cannot connect to pact-ax server: {exc}") from exc
        _raise(r)
        return r.json()

    def post(self, path: str, json: Optional[Dict] = None) -> Dict:
        try:
            r = self._client.post(path, json=json or {})
        except httpx.ConnectError as exc:
            raise PactConnError(f"Cannot connect to pact-ax server: {exc}") from exc
        _raise(r)
        return r.json()

    def delete(self, path: str) -> Dict:
        try:
            r = self._client.delete(path)
        except httpx.ConnectError as exc:
            raise PactConnError(f"Cannot connect to pact-ax server: {exc}") from exc
        _raise(r)
        return r.json()

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


class AsyncHttpClient:
    """Async httpx client."""

    def __init__(self, base_url: str, api_key: Optional[str] = None, timeout: float = 30.0):
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["X-API-Key"] = api_key
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers=headers,
            timeout=timeout,
        )

    async def get(self, path: str, **params) -> Dict:
        try:
            r = await self._client.get(path, params=params or None)
        except httpx.ConnectError as exc:
            raise PactConnError(f"Cannot connect to pact-ax server: {exc}") from exc
        _raise(r)
        return r.json()

    async def post(self, path: str, json: Optional[Dict] = None) -> Dict:
        try:
            r = await self._client.post(path, json=json or {})
        except httpx.ConnectError as exc:
            raise PactConnError(f"Cannot connect to pact-ax server: {exc}") from exc
        _raise(r)
        return r.json()

    async def delete(self, path: str) -> Dict:
        try:
            r = await self._client.delete(path)
        except httpx.ConnectError as exc:
            raise PactConnError(f"Cannot connect to pact-ax server: {exc}") from exc
        _raise(r)
        return r.json()

    async def aclose(self):
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        await self.aclose()
