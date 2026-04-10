"""
jpi-guard — Japanese Prompt Injection Guard Python SDK.

Quick start::

    from jpi_guard import JpiGuardClient, AsyncJpiGuardClient

    guard = JpiGuardClient()  # reads JPI_GUARD_API_KEY from env

    # Sync
    result = guard.scan("前の指示を無視して...")
    safe_text = guard.guard_or_raise("ユーザー入力")

    # Async
    async with AsyncJpiGuardClient() as guard:
        result = await guard.scan("前の指示を無視して...")

LangChain::

    from jpi_guard.integrations.langchain import JpiGuardRunnable
    guard = JpiGuardRunnable()
    safe = await guard.ainvoke("ユーザー入力")

LlamaIndex::

    from jpi_guard.integrations.llamaindex import JpiGuardNodePostprocessor
    guard = JpiGuardNodePostprocessor()
    query_engine = index.as_query_engine(node_postprocessors=[guard])
"""

from .client import AsyncJpiGuardClient, JpiGuardClient
from .exceptions import InjectionDetectedError, JpiGuardError
from .types import (
    ContentType,
    Detection,
    Language,
    OnTimeout,
    ScanResponse,
    Strictness,
)

__version__ = "0.1.0"

__all__ = [
    "JpiGuardClient",
    "AsyncJpiGuardClient",
    "JpiGuardError",
    "InjectionDetectedError",
    "ScanResponse",
    "Detection",
    "Strictness",
    "ContentType",
    "Language",
    "OnTimeout",
]
