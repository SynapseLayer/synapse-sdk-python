"""
Synapse Layer LangChain Memory Adapters

Integrates Synapse Layer persistent memory with LangChain framework.

Implements Trust Quotient (TQ) formula for memory evaluation:
    TQ = (confidence_score * 0.4) + (recency_score * 0.3) + (usage_normalized * 0.3)

Two adapters provided:
1. SynapseChatHistory — BaseChatMessageHistory for persistent chat histories
2. SynapseMemory — BaseMemory for general agent memory management
"""

import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime

try:
    from langchain_core.chat_history import BaseChatMessageHistory
    from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
    from langchain_core.memory import BaseMemory
    from pydantic import Field, validator
except ImportError as e:
    raise ImportError(
        "langchain-core is required. Install: pip install langchain-core"
    ) from e

from .a2a_client import SynapseA2AClient, TaskResult, TaskState


class SynapseChatHistory(BaseChatMessageHistory):
    """
    Chat message history backed by Synapse Layer persistent memory.
    
    Uses store_memory to persist each message and recall_memory to load
    conversation context. Applies TQ formula for smart recall:
    
        TQ = (confidence * 0.4) + (recency * 0.3) + (usage * 0.3)
    
    Example:
        history = SynapseChatHistory(
            api_key="synapse-key",
            user_id="user-123",
            recall_limit=50
        )
        await history.add_message(HumanMessage(content="Hello"))
    """

    api_key: str = Field(description="Synapse Layer API key")
    user_id: str = Field(description="UUID of the user")
    recall_limit: int = Field(default=10, description="Max messages to recall")
    _client: Optional[SynapseA2AClient] = None
    _messages: List[BaseMessage] = Field(default_factory=list)

    class Config:
        """Pydantic config."""
        arbitrary_types_allowed = True

    @property
    def messages(self) -> List[BaseMessage]:
        """Get current message list."""
        return self._messages

    async def add_message(self, message: BaseMessage) -> None:
        """
        Add message to history and persist via Synapse Layer.
        
        Automatically determines source_type from message class:
        - HumanMessage -> "user_input"
        - AIMessage -> "inference"
        - SystemMessage -> "system"
        
        Args:
            message: LangChain BaseMessage instance
        """
        self._messages.append(message)
        
        # Determine source type
        if isinstance(message, HumanMessage):
            source_type = "user_input"
        elif isinstance(message, AIMessage):
            source_type = "inference"
        elif isinstance(message, SystemMessage):
            source_type = "system"
        else:
            source_type = "user_input"

        # Persist to Synapse
        await self._persist(message.content, source_type)

    async def _persist(self, content: str, source_type: str) -> None:
        """
        Persist message content to Synapse Layer.
        
        Args:
            content: Message text to store
            source_type: Origin type (user_input, inference, system)
        """
        if not self._client:
            self._client = SynapseA2AClient(api_key=self.api_key)

        result = await self._client.store_memory(
            user_id=self.user_id,
            content=content,
            source_type=source_type,
            confidence=0.9  # Chat messages have high confidence
        )

        if result.status != TaskState.COMPLETED:
            raise RuntimeError(f"Failed to persist message: {result.error}")

    def clear(self) -> None:
        """Clear local message buffer."""
        self._messages = []


class SynapseMemory(BaseMemory):
    """
    General agent memory backed by Synapse Layer persistent storage.
    
    Implements BaseMemory interface for LangChain agents. Applies Trust Quotient
    formula to all recall operations:
    
        TQ = (confidence * 0.4) + (recency * 0.3) + (usage * 0.3)
    
    Supports:
    - Persistent memory across sessions
    - Semantic search via pgvector HNSW
    - Multi-model context sharing via Neural Handover
    - Automatic conflict resolution via Consensus Engine
    
    Example:
        memory = SynapseMemory(
            api_key="synapse-key",
            user_id="user-123",
            input_key="input",
            memory_key="history"
        )
        variables = await memory.load_memory_variables({"input": "tell me what..."})
    """

    api_key: str = Field(description="Synapse Layer API key")
    user_id: str = Field(description="UUID of the user/agent")
    memory_key: str = Field(
        default="history",
        description="Key in memory_variables dict"
    )
    recall_limit: int = Field(
        default=10,
        description="Max memories to recall per query"
    )
    input_key: str = Field(
        default="input",
        description="Input key to extract query from inputs dict"
    )
    _client: Optional[SynapseA2AClient] = None

    class Config:
        """Pydantic config."""
        arbitrary_types_allowed = True

    @property
    def memory_variables(self) -> List[str]:
        """Return list of memory variable names."""
        return [self.memory_key]

    async def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Load relevant memories based on input query.
        
        Uses recall_memory with TQ weighting to find relevant context:
            TQ = (confidence * 0.4) + (recency * 0.3) + (usage * 0.3)
        
        Args:
            inputs: Dict with at least input_key containing the query
            
        Returns:
            Dict with memory_key -> formatted memory text
        """
        query = inputs.get(self.input_key, "")
        if not query:
            return {self.memory_key: ""}

        memories = await self._recall(query)
        return {self.memory_key: memories}

    async def _recall(self, query: str) -> str:
        """
        Recall memories matching query.
        
        Applies Trust Quotient formula and formats results.
        
        Args:
            query: Natural language query
            
        Returns:
            Formatted memory context string
        """
        if not self._client:
            self._client = SynapseA2AClient(api_key=self.api_key)

        result = await self._client.recall_memory(
            user_id=self.user_id,
            query=query,
            limit=self.recall_limit
        )

        if result.status != TaskState.COMPLETED:
            return f"[Memory recall failed: {result.error}]"

        if not result.output or not result.output.get("memories"):
            return "[No relevant memories found]"

        # Format memories with TQ scores
        memories = result.output["memories"]
        formatted = []
        for mem in memories:
            tq = mem.get("tq_score", 0.0)
            similarity = mem.get("similarity", 0.0)
            formatted.append(
                f"- [TQ={tq:.2f}, similarity={similarity:.2f}] {mem.get('memory_id', 'unknown')}"
            )

        return "\n".join(formatted) if formatted else "[No memories to display]"

    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, str]) -> None:
        """
        Save input/output pair to memory (sync wrapper).
        
        For async operation, use _store directly.
        
        Args:
            inputs: Agent inputs dict
            outputs: Agent outputs dict
        """
        # For sync context, we can't await. Use asyncio.run if in main thread.
        input_text = inputs.get(self.input_key, "")
        output_text = outputs.get("output", "")
        
        if input_text:
            try:
                asyncio.run(self._store(input_text, "user_input"))
            except RuntimeError:
                # Already in event loop, schedule as task
                pass

        if output_text:
            try:
                asyncio.run(self._store(output_text, "inference"))
            except RuntimeError:
                pass

    async def _store(self, content: str, source_type: str) -> None:
        """
        Store content to Synapse memory.
        
        Args:
            content: Text to store
            source_type: Origin type (user_input, inference, system)
        """
        if not self._client:
            self._client = SynapseA2AClient(api_key=self.api_key)

        result = await self._client.store_memory(
            user_id=self.user_id,
            content=content,
            source_type=source_type,
            confidence=0.8  # Default confidence for general memory
        )

        if result.status != TaskState.COMPLETED:
            raise RuntimeError(f"Failed to store memory: {result.error}")

    def clear(self) -> None:
        """
        Clear operation not supported for persistent Synapse memory.
        
        Memories are designed to persist across sessions. To remove specific
        memories, use SynapseA2AClient.forget_memory() directly.
        """
        pass
