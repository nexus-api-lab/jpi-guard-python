"""
LlamaIndex integration for jpi-guard.

Requires: pip install jpi-guard[llamaindex]
"""

from __future__ import annotations

from typing import Any, List, Optional

from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.core.schema import NodeWithScore, QueryBundle

from ..client import JpiGuardClient
from ..exceptions import InjectionDetectedError
from ..types import Strictness


class JpiGuardNodePostprocessor(BaseNodePostprocessor):
    """
    LlamaIndex node postprocessor that guards retrieved chunks for injection.

    Use this in a query pipeline to scan RAG context before it reaches the LLM.

    Usage::

        from llama_index.core import VectorStoreIndex
        from jpi_guard.integrations.llamaindex import JpiGuardNodePostprocessor

        guard = JpiGuardNodePostprocessor()

        query_engine = index.as_query_engine(
            node_postprocessors=[guard],
        )
        response = query_engine.query("What is jpi-guard?")
    """

    api_key: Optional[str] = None
    strictness: Strictness = "medium"
    block_on_detection: bool = True

    def __init__(
        self,
        api_key: Optional[str] = None,
        strictness: Strictness = "medium",
        block_on_detection: bool = True,
    ) -> None:
        """
        Args:
            api_key: jpi-guard API key. Falls back to JPI_GUARD_API_KEY env var.
            strictness: Scan strictness ("low", "medium", "high").
            block_on_detection: If True, raises InjectionDetectedError on detection.
                                 If False, replaces node text with cleaned_content.
        """
        super().__init__(
            api_key=api_key,
            strictness=strictness,
            block_on_detection=block_on_detection,
        )
        self._client = JpiGuardClient(
            api_key=api_key,
            default_strictness=strictness,
            fail_open=True,  # don't break RAG on API unavailability
        )

    def _postprocess_nodes(
        self,
        nodes: List[NodeWithScore],
        query_bundle: Optional[QueryBundle] = None,
    ) -> List[NodeWithScore]:
        safe_nodes: List[NodeWithScore] = []

        for node_with_score in nodes:
            text = node_with_score.node.get_content()
            result = self._client.scan(text, strictness=self.strictness)

            if result["injection_detected"]:
                if self.block_on_detection:
                    raise InjectionDetectedError(result)
                # Replace injected content with cleaned version
                node_with_score.node.set_content(result["cleaned_content"])

            safe_nodes.append(node_with_score)

        return safe_nodes


class JpiGuardQueryGuard:
    """
    Guard for user query text (not RAG context).

    Usage::

        guard = JpiGuardQueryGuard()
        safe_query = guard.guard(user_query)  # raises on injection
        response = query_engine.query(safe_query)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        strictness: Strictness = "medium",
    ) -> None:
        self._client = JpiGuardClient(api_key=api_key, default_strictness=strictness)

    def guard(self, query: str) -> str:
        """Raise InjectionDetectedError if injection found, else return cleaned text."""
        return self._client.guard_or_raise(query)
