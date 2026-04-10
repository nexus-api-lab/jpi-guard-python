"""
LangChain integration for jpi-guard.

Requires: pip install jpi-guard[langchain]
"""

from __future__ import annotations

from typing import Any, Optional

from langchain_core.runnables import RunnableConfig, RunnableLambda

from ..client import AsyncJpiGuardClient, JpiGuardClient
from ..exceptions import InjectionDetectedError
from ..types import ContentType, Language, OnTimeout, Strictness


class JpiGuardRunnable:
    """
    LangChain-compatible runnable that guards string inputs.

    Throws :class:`InjectionDetectedError` by default.
    Set ``pass_cleaned_content=True`` to pass sanitized text downstream.

    Usage::

        from jpi_guard.integrations.langchain import JpiGuardRunnable
        from langchain_openai import ChatOpenAI

        guard = JpiGuardRunnable()
        llm = ChatOpenAI(model="gpt-4o-mini")

        # Block on injection
        safe = await guard.ainvoke("ユーザー入力")

        # Use in LCEL chain
        chain = guard.as_runnable() | llm
        result = await chain.ainvoke("ユーザー入力")
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        strictness: Strictness = "medium",
        content_type: ContentType = "plaintext",
        language: Language = "auto",
        on_timeout: OnTimeout = "fail_open",
        fail_open: bool = False,
        pass_cleaned_content: bool = False,
    ) -> None:
        self._client = JpiGuardClient(
            api_key=api_key,
            fail_open=fail_open,
            default_strictness=strictness,
        )
        self._async_client = AsyncJpiGuardClient(
            api_key=api_key,
            fail_open=fail_open,
            default_strictness=strictness,
        )
        self._scan_kwargs: dict[str, Any] = {
            "content_type": content_type,
            "language": language,
            "on_timeout": on_timeout,
        }
        self._pass_cleaned = pass_cleaned_content

    def invoke(self, input: str, config: Optional[RunnableConfig] = None) -> str:
        if self._pass_cleaned:
            result = self._client.scan(input, **self._scan_kwargs)
            return result["cleaned_content"]
        return self._client.guard_or_raise(input, **self._scan_kwargs)

    async def ainvoke(self, input: str, config: Optional[RunnableConfig] = None) -> str:
        if self._pass_cleaned:
            result = await self._async_client.scan(input, **self._scan_kwargs)
            return result["cleaned_content"]
        return await self._async_client.guard_or_raise(input, **self._scan_kwargs)

    def as_runnable(self) -> RunnableLambda:
        """Return a LangChain RunnableLambda wrapping this guard."""
        return RunnableLambda(self.invoke, afunc=self.ainvoke)


def create_safe_rag_chain(
    llm: Any,
    prompt: Any,
    api_key: Optional[str] = None,
    strictness: Strictness = "medium",
) -> Any:
    """
    Helper: wrap a (prompt | llm) chain with jpi-guard pre-processing on context.

    The guard scans the ``context`` key of the input dict.

    Usage::

        from langchain_openai import ChatOpenAI
        from langchain_core.prompts import ChatPromptTemplate
        from jpi_guard.integrations.langchain import create_safe_rag_chain

        llm = ChatOpenAI(model="gpt-4o-mini")
        prompt = ChatPromptTemplate.from_messages([
            ("system", "Answer based on: {context}"),
            ("human", "{question}"),
        ])

        chain = create_safe_rag_chain(llm, prompt)
        result = await chain.ainvoke({
            "context": scraped_webpage,
            "question": user_question,
        })
    """
    from langchain_core.runnables import RunnableLambda, RunnablePassthrough

    guard = JpiGuardRunnable(
        api_key=api_key,
        strictness=strictness,
        pass_cleaned_content=True,  # pass cleaned context, don't throw
    )

    def scan_context(inputs: dict) -> dict:
        cleaned = guard.invoke(inputs["context"])
        return {**inputs, "context": cleaned}

    async def ascan_context(inputs: dict) -> dict:
        cleaned = await guard.ainvoke(inputs["context"])
        return {**inputs, "context": cleaned}

    return (
        RunnableLambda(scan_context, afunc=ascan_context)
        | prompt
        | llm
    )
