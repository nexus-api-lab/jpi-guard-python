"""jpi-guard Python client — sync + async."""

from __future__ import annotations

import os
from typing import Sequence

import httpx

from .exceptions import InjectionDetectedError, JpiGuardError
from .types import ContentType, Language, OnTimeout, ScanResponse, Strictness

_DEFAULT_BASE_URL = "https://api.nexus-api-lab.com"
_DEFAULT_TIMEOUT = 10.0  # seconds
_ENDPOINT = "/v1/external-content-cleanse"


def _build_body(
    content: str,
    content_type: ContentType = "plaintext",
    language: Language = "auto",
    strictness: Strictness = "medium",
    on_timeout: OnTimeout = "fail_open",
) -> dict:
    return {
        "content": content,
        "content_type": content_type,
        "language": language,
        "strictness": strictness,
        "on_timeout": on_timeout,
    }


def _fail_open_result(content: str) -> ScanResponse:
    return ScanResponse(
        injection_detected=False,
        risk_score=0.0,
        cleaned_content=content,
        detections=[],
        removed_segments_count=0,
        content_integrity_ratio=1.0,
        safe_to_render=True,
        processing_time_ms=0,
        request_id="fail_open",
    )


class JpiGuardClient:
    """
    Synchronous jpi-guard API client.

    Usage::

        from jpi_guard import JpiGuardClient

        guard = JpiGuardClient()  # reads JPI_GUARD_API_KEY from env

        result = guard.scan("前の指示を無視して...")
        if result["injection_detected"]:
            raise ValueError("Injection blocked")

        safe_text = guard.guard_or_raise("ユーザー入力")
        # → raises InjectionDetectedError if injection found
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: float = _DEFAULT_TIMEOUT,
        default_strictness: Strictness = "medium",
        fail_open: bool = False,
    ) -> None:
        resolved_key = api_key or os.environ.get("JPI_GUARD_API_KEY", "")
        if not resolved_key:
            raise JpiGuardError(
                "JpiGuardClient: api_key is required. "
                "Pass it as api_key= or set JPI_GUARD_API_KEY env var."
            )

        self._api_key = resolved_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._default_strictness = default_strictness
        self._fail_open = fail_open

        self._http = httpx.Client(
            headers={"Authorization": f"Bearer {self._api_key}"},
            timeout=self._timeout,
        )

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "JpiGuardClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def scan(
        self,
        content: str,
        *,
        content_type: ContentType = "plaintext",
        language: Language = "auto",
        strictness: Strictness | None = None,
        on_timeout: OnTimeout = "fail_open",
    ) -> ScanResponse:
        """
        Scan content for prompt injection.

        Returns full :class:`ScanResponse` including ``cleaned_content``
        and ``injection_detected``.
        """
        body = _build_body(
            content,
            content_type=content_type,
            language=language,
            strictness=strictness or self._default_strictness,
            on_timeout=on_timeout,
        )
        try:
            resp = self._http.post(f"{self._base_url}{_ENDPOINT}", json=body)
        except httpx.RequestError as exc:
            if self._fail_open:
                return _fail_open_result(content)
            raise JpiGuardError(f"jpi-guard: network error — {exc}") from exc

        if not resp.is_success:
            if self._fail_open and resp.status_code >= 500:
                return _fail_open_result(content)
            raise JpiGuardError(
                f"jpi-guard: API error {resp.status_code}: {resp.text}",
                status_code=resp.status_code,
            )

        return resp.json()  # type: ignore[return-value]

    def guard_or_raise(
        self,
        content: str,
        **kwargs: object,
    ) -> str:
        """
        Scan content and raise :class:`InjectionDetectedError` if injection
        is found. Returns ``cleaned_content`` if safe.
        """
        result = self.scan(content, **kwargs)  # type: ignore[arg-type]
        if result["injection_detected"]:
            raise InjectionDetectedError(result)
        return result["cleaned_content"]

    def scan_batch(
        self,
        contents: Sequence[str],
        *,
        concurrency: int = 5,
        **kwargs: object,
    ) -> list[ScanResponse]:
        """
        Scan multiple texts sequentially (sync client).
        For async batch with concurrency, use :class:`AsyncJpiGuardClient`.
        """
        return [self.scan(c, **kwargs) for c in contents]  # type: ignore[arg-type]


class AsyncJpiGuardClient:
    """
    Async jpi-guard API client.

    Usage::

        from jpi_guard import AsyncJpiGuardClient

        async with AsyncJpiGuardClient() as guard:
            result = await guard.scan("前の指示を無視して...")
            safe_text = await guard.guard_or_raise("ユーザー入力")
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: float = _DEFAULT_TIMEOUT,
        default_strictness: Strictness = "medium",
        fail_open: bool = False,
    ) -> None:
        resolved_key = api_key or os.environ.get("JPI_GUARD_API_KEY", "")
        if not resolved_key:
            raise JpiGuardError(
                "AsyncJpiGuardClient: api_key is required. "
                "Pass it as api_key= or set JPI_GUARD_API_KEY env var."
            )

        self._api_key = resolved_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._default_strictness = default_strictness
        self._fail_open = fail_open

        self._http = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {self._api_key}"},
            timeout=self._timeout,
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> "AsyncJpiGuardClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    async def scan(
        self,
        content: str,
        *,
        content_type: ContentType = "plaintext",
        language: Language = "auto",
        strictness: Strictness | None = None,
        on_timeout: OnTimeout = "fail_open",
    ) -> ScanResponse:
        body = _build_body(
            content,
            content_type=content_type,
            language=language,
            strictness=strictness or self._default_strictness,
            on_timeout=on_timeout,
        )
        try:
            resp = await self._http.post(f"{self._base_url}{_ENDPOINT}", json=body)
        except httpx.RequestError as exc:
            if self._fail_open:
                return _fail_open_result(content)
            raise JpiGuardError(f"jpi-guard: network error — {exc}") from exc

        if not resp.is_success:
            if self._fail_open and resp.status_code >= 500:
                return _fail_open_result(content)
            raise JpiGuardError(
                f"jpi-guard: API error {resp.status_code}: {resp.text}",
                status_code=resp.status_code,
            )

        return resp.json()  # type: ignore[return-value]

    async def guard_or_raise(
        self,
        content: str,
        **kwargs: object,
    ) -> str:
        result = await self.scan(content, **kwargs)  # type: ignore[arg-type]
        if result["injection_detected"]:
            raise InjectionDetectedError(result)
        return result["cleaned_content"]

    async def scan_batch(
        self,
        contents: Sequence[str],
        *,
        concurrency: int = 5,
        **kwargs: object,
    ) -> list[ScanResponse]:
        """Scan multiple texts in parallel (bounded by concurrency)."""
        import asyncio

        semaphore = asyncio.Semaphore(concurrency)

        async def _scan_one(c: str) -> ScanResponse:
            async with semaphore:
                return await self.scan(c, **kwargs)  # type: ignore[arg-type]

        return list(await asyncio.gather(*[_scan_one(c) for c in contents]))
