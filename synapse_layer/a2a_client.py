"""
Synapse Layer A2A Client — JSON-RPC 2.0 over HTTPS

Provides async client for Agent-to-Agent (A2A) communication with Synapse Layer MCP server.
Implements Trust Quotient (TQ) formula for memory confidence evaluation:

    TQ = (confidence_score * 0.4) + (recency_score * 0.3) + (usage_normalized * 0.3)

where:
  - confidence_score: Precision of memory (0.0-1.0)
  - recency_score: How recent the memory is (0.0-1.0, decays over time)
  - usage_normalized: Normalized count of times memory was recalled (0.0-1.0)
"""

import asyncio
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional
import aiohttp


# Constants
DEFAULT_BASE_URL = "https://forge.synapselayer.org/api/mcp"
VALID_SKILL_IDS = {
    "store_memory",
    "recall_memory",
    "create_handover",
    "resolve_conflict",
    "forget_memory"
}


# Enums
class TaskState(str, Enum):
    """State enum for A2A task lifecycle."""
    SUBMITTED = "submitted"
    WORKING = "working"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# Dataclasses
@dataclass
class TaskResult:
    """Result of a skill invocation."""
    task_id: str
    status: TaskState
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    def __post_init__(self):
        """Convert status string to TaskState enum if needed."""
        if isinstance(self.status, str):
            self.status = TaskState(self.status)


# Main Client Class
class SynapseA2AClient:
    """
    Async client for Synapse Layer A2A protocol (JSON-RPC 2.0).
    
    Provides methods to interact with Synapse Layer's memory, handover, and
    conflict resolution skills through the MCP server.
    
    Trust Quotient (TQ) formula applied to all memory operations:
        TQ = (confidence_score * 0.4) + (recency_score * 0.3) + (usage_normalized * 0.3)
    
    Example:
        async with SynapseA2AClient(api_key="...") as client:
            result = await client.store_memory(
                user_id="user-123",
                content="My preferences...",
                source_type="user_input",
                confidence=0.95
            )
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: int = 30
    ):
        """
        Initialize A2A client.
        
        Args:
            api_key: Synapse Layer API key for authentication
            base_url: MCP server base URL (defaults to production Supabase Edge Function)
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session: Optional[aiohttp.ClientSession] = None
        self._request_id_counter = 0

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    def _get_next_request_id(self) -> int:
        """Get next JSON-RPC request ID."""
        self._request_id_counter += 1
        return self._request_id_counter

    async def send_task(self, skill_id: str, params: Dict[str, Any]) -> TaskResult:
        """
        Send a skill invocation task via JSON-RPC 2.0.
        
        Core method for all A2A communication. Validates skill_id and formats
        the JSON-RPC request according to MCP spec.
        
        Args:
            skill_id: One of VALID_SKILL_IDS
            params: Skill-specific parameters dict
            
        Returns:
            TaskResult with task_id, status, output or error
            
        Raises:
            ValueError: If skill_id is invalid
            aiohttp.ClientError: If HTTP request fails
        """
        if skill_id not in VALID_SKILL_IDS:
            raise ValueError(f"Unknown skill: {skill_id}. Valid: {VALID_SKILL_IDS}")

        if not self.session:
            raise RuntimeError("Client not in async context. Use 'async with' syntax.")

        # Build JSON-RPC 2.0 request
        request_id = self._get_next_request_id()
        rpc_payload = {
            "jsonrpc": "2.0",
            "method": skill_id,
            "params": params,
            "id": request_id
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        try:
            async with self.session.post(
                self.base_url,
                json=rpc_payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                body = await response.json()
                return self._parse_response(body, request_id)
        except asyncio.TimeoutError:
            return TaskResult(
                task_id=f"req-{request_id}",
                status=TaskState.FAILED,
                error="Request timeout"
            )
        except Exception as e:
            return TaskResult(
                task_id=f"req-{request_id}",
                status=TaskState.FAILED,
                error=str(e)
            )

    @staticmethod
    def _parse_response(body: Dict[str, Any], request_id: int) -> TaskResult:
        """
        Parse JSON-RPC 2.0 response.
        
        Handles both success (result) and error responses according to JSON-RPC spec.
        
        Args:
            body: Response body from server
            request_id: Original request ID for correlation
            
        Returns:
            TaskResult with parsed output or error
        """
        task_id = body.get("id", request_id)

        if "error" in body:
            error_obj = body["error"]
            error_msg = error_obj.get("message", "Unknown error")
            return TaskResult(
                task_id=str(task_id),
                status=TaskState.FAILED,
                error=error_msg
            )

        if "result" in body:
            result = body["result"]
            return TaskResult(
                task_id=str(task_id),
                status=TaskState.COMPLETED,
                output=result
            )

        return TaskResult(
            task_id=str(task_id),
            status=TaskState.FAILED,
            error="Invalid JSON-RPC response"
        )

    # Skill Convenience Wrappers

    async def store_memory(
        self,
        user_id: str,
        content: str,
        source_type: str,
        confidence: float
    ) -> TaskResult:
        """
        Store encrypted memory with semantic embedding.
        
        TQ formula applied: confidence contributes 40% to final Trust Quotient.
        
        Args:
            user_id: UUID of memory owner
            content: Plaintext content to encrypt and store
            source_type: Origin type (user_input, api_response, inference, handover, system)
            confidence: Confidence score (0.0-1.0)
            
        Returns:
            TaskResult with memory_id, fact_hash, and tq_score
        """
        return await self.send_task("store_memory", {
            "user_id": user_id,
            "content": content,
            "source_type": source_type,
            "confidence": confidence
        })

    async def recall_memory(
        self,
        user_id: str,
        query: str,
        limit: int = 10
    ) -> TaskResult:
        """
        Semantic search over encrypted memories with TQ weighting.
        
        Results ordered by Trust Quotient = (confidence * 0.4) + (recency * 0.3) + (usage * 0.3).
        
        Args:
            user_id: UUID of agent requesting recall
            query: Natural language query for semantic search
            limit: Max memories to return (default 10, max 100)
            
        Returns:
            TaskResult with memories array (memory_id, similarity, tq_score)
        """
        return await self.send_task("recall_memory", {
            "user_id": user_id,
            "query": query,
            "limit": min(limit, 100)
        })

    async def create_handover(
        self,
        user_id: str,
        target_model: str,
        summary: str
    ) -> TaskResult:
        """
        Create Neural Handover package for context transfer to another model.
        
        Package includes HMAC-SHA256 signature and list of transferred memories.
        
        Args:
            user_id: UUID of agent context to transfer
            target_model: Target model identifier (claude-3-opus, gpt-4, gemini-2.5, etc)
            summary: Brief context summary for handover
            
        Returns:
            TaskResult with handover_package (Base64), signature, and memories_count
        """
        return await self.send_task("create_handover", {
            "user_id": user_id,
            "target_model": target_model,
            "summary": summary
        })

    async def resolve_conflict(
        self,
        user_id: str,
        memory_id: str
    ) -> TaskResult:
        """
        Detect and auto-resolve conflicting memories using Consensus Engine.
        
        Uses Trust Quotient to select winner among conflicts:
            TQ = (confidence * 0.4) + (recency * 0.3) + (usage * 0.3)
        
        Args:
            user_id: UUID of memory vault
            memory_id: Primary memory ID to check for conflicts
            
        Returns:
            TaskResult with conflict_detected, winner_id, winner_tq, resolution_method
        """
        return await self.send_task("resolve_conflict", {
            "user_id": user_id,
            "memory_id": memory_id
        })

    async def forget_memory(
        self,
        user_id: str,
        memory_id: str
    ) -> TaskResult:
        """
        Soft-delete memory with GDPR/LGPD compliance.
        
        Memory marked inactive but audit trail preserved for compliance.
        
        Args:
            user_id: UUID of memory owner
            memory_id: UUID of memory to delete
            
        Returns:
            TaskResult with deleted flag, deletion_timestamp, and audit_id
        """
        return await self.send_task("forget_memory", {
            "user_id": user_id,
            "memory_id": memory_id
        })
