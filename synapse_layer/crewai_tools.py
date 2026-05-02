"""
CrewAI Tools for Synapse Layer Integration

Provides three CrewAI tools for Agent-to-Agent memory management:
- SynapseStoreMemoryTool: Store encrypted memory with semantic embedding
- SynapseRecallMemoryTool: Retrieve memories using Trust Quotient (TQ) weighting
- SynapseHandoverTool: Create Neural Handover context for target model

TQ Formula: TQ = (confidence_score * 0.4) + (recency_score * 0.3) + (usage_normalized * 0.3)

Requires: pip install 'synapse-layer[crewai]'

Author: Ismael Marchi
License: Apache 2.0
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Optional, Union

from pydantic import BaseModel, Field

try:
    from crewai.tools import BaseTool
    _CREWAI_AVAILABLE = True
except ImportError:
    _CREWAI_AVAILABLE = False

if not _CREWAI_AVAILABLE:
    raise ImportError(
        "crewai is required for CrewAI tools. "
        "Install with: pip install 'synapse-layer[crewai]'"
    )

from .a2a_client import SynapseA2AClient, TaskResult


# ============================================================================
# Input Schemas (Pydantic v2)
# ============================================================================


class StoreMemoryInput(BaseModel):
    """Input schema for storing memory in Synapse Layer."""

    user_id: str = Field(
        ...,
        description="UUID of the user",
    )
    content: str = Field(
        ...,
        description="Memory content to store",
    )
    source_type: str = Field(
        default="api_response",
        description="Source of memory: user_input, api_response, inference, handover, system",
    )
    confidence: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Confidence score (0.0-1.0)",
    )


class RecallMemoryInput(BaseModel):
    """Input schema for recalling memories from Synapse Layer."""

    user_id: str = Field(
        ...,
        description="UUID of the user",
    )
    query: str = Field(
        ...,
        description="Semantic search query for memory retrieval",
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of memories to retrieve",
    )


class HandoverInput(BaseModel):
    """Input schema for Neural Handover to target model."""

    user_id: str = Field(
        ...,
        description="UUID of the user",
    )
    target_model: str = Field(
        ...,
        description="Target model identifier (e.g., claude-3.5-sonnet, gpt-4o)",
    )
    summary: str = Field(
        ...,
        description="Context summary for handover",
    )


# ============================================================================
# Base Class with _run_sync
# ============================================================================


class _SynapseBaseTool(BaseTool):
    """
    Base class for Synapse Layer tools with synchronous execution wrapper.

    Provides _run_sync method using concurrent.futures.ThreadPoolExecutor
    to safely execute async code in sync contexts (CrewAI requirement).
    """

    api_key: str
    base_url: str = "https://synapse-layer-api.supabase.co/functions/v1"

    def _run_sync(self, coro):
        """
        Execute async coroutine in a thread pool executor.

        Args:
            coro: Coroutine to execute

        Returns:
            Result of coroutine execution
        """
        loop = None
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is None:
            return asyncio.run(coro)
        else:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result()


# ============================================================================
# Tool 1: SynapseStoreMemoryTool
# ============================================================================


class SynapseStoreMemoryTool(_SynapseBaseTool):
    """
    Tool for storing encrypted memory in Synapse Layer.

    Stores content with semantic embedding and Trust Quotient (TQ) metadata.
    TQ = (confidence_score * 0.4) + (recency_score * 0.3) + (usage_normalized * 0.3)

    Args:
        api_key: Synapse Layer API key
        base_url: API endpoint (default: Supabase Edge Function)

    Returns:
        TaskResult with memory storage status
    """

    name: str = "synapse_store_memory"
    description: str = (
        "Store encrypted memory in Synapse Layer with semantic embedding and TQ metadata. "
        "Use this to persist agent context, observations, and decisions."
    )
    args_schema: type = StoreMemoryInput

    def _run(
        self,
        user_id: str,
        content: str,
        source_type: str = "api_response",
        confidence: float = 0.8,
    ) -> str:
        coro = self._async_run(user_id, content, source_type, confidence)
        result = self._run_sync(coro)
        return str(result)

    async def _async_run(
        self,
        user_id: str,
        content: str,
        source_type: str = "api_response",
        confidence: float = 0.8,
    ) -> TaskResult:
        async with SynapseA2AClient(api_key=self.api_key, base_url=self.base_url) as client:
            return await client.store_memory(
                user_id=user_id,
                content=content,
                source_type=source_type,
                confidence=confidence,
            )

    async def _arun(
        self,
        user_id: str,
        content: str,
        source_type: str = "api_response",
        confidence: float = 0.8,
    ) -> str:
        result = await self._async_run(user_id, content, source_type, confidence)
        return str(result)


# ============================================================================
# Tool 2: SynapseRecallMemoryTool
# ============================================================================


class SynapseRecallMemoryTool(_SynapseBaseTool):
    """
    Tool for semantic search and retrieval of memories from Synapse Layer.

    Retrieves memories ordered by Trust Quotient (TQ) score.
    TQ = (confidence_score * 0.4) + (recency_score * 0.3) + (usage_normalized * 0.3)
    """

    name: str = "synapse_recall_memory"
    description: str = (
        "Retrieve encrypted memories from Synapse Layer using semantic search and TQ weighting. "
        "Use this to access relevant agent context and previous observations."
    )
    args_schema: type = RecallMemoryInput

    def _run(
        self,
        user_id: str,
        query: str,
        limit: int = 10,
    ) -> str:
        coro = self._async_run(user_id, query, limit)
        result = self._run_sync(coro)
        return str(result)

    async def _async_run(
        self,
        user_id: str,
        query: str,
        limit: int = 10,
    ) -> TaskResult:
        async with SynapseA2AClient(api_key=self.api_key, base_url=self.base_url) as client:
            return await client.recall_memory(
                user_id=user_id,
                query=query,
                limit=limit,
            )

    async def _arun(
        self,
        user_id: str,
        query: str,
        limit: int = 10,
    ) -> str:
        result = await self._async_run(user_id, query, limit)
        return str(result)


# ============================================================================
# Tool 3: SynapseHandoverTool
# ============================================================================


class SynapseHandoverTool(_SynapseBaseTool):
    """
    Tool for creating Neural Handover context to target model.

    Packages agent context with HMAC-SHA256 signature for secure transfer.
    """

    name: str = "synapse_create_handover"
    description: str = (
        "Create Neural Handover context with HMAC-SHA256 signature for secure agent-to-model transfer. "
        "Use this to transition context to different AI models while maintaining memory continuity."
    )
    args_schema: type = HandoverInput

    def _run(
        self,
        user_id: str,
        target_model: str,
        summary: str,
    ) -> str:
        coro = self._async_run(user_id, target_model, summary)
        result = self._run_sync(coro)
        return str(result)

    async def _async_run(
        self,
        user_id: str,
        target_model: str,
        summary: str,
    ) -> TaskResult:
        async with SynapseA2AClient(api_key=self.api_key, base_url=self.base_url) as client:
            return await client.create_handover(
                user_id=user_id,
                target_model=target_model,
                summary=summary,
            )

    async def _arun(
        self,
        user_id: str,
        target_model: str,
        summary: str,
    ) -> str:
        result = await self._async_run(user_id, target_model, summary)
        return str(result)


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    "SynapseStoreMemoryTool",
    "SynapseRecallMemoryTool",
    "SynapseHandoverTool",
    "StoreMemoryInput",
    "RecallMemoryInput",
    "HandoverInput",
]
