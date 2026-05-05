"""
Synapse Layer — Universal memory layer for AI agents.
Persistent, Private, Model-agnostic.

MCP-native. LangChain-compatible. A2A-ready.

Core (always available):
    from synapse_layer import SynapseA2AClient

LangChain adapter (requires langchain-core):
    from synapse_layer import SynapseMemory, SynapseChatHistory

CrewAI tools (requires crewai):
    from synapse_layer import SynapseStoreMemoryTool, SynapseRecallMemoryTool
"""

__version__ = "2.3.3"

# Core — always importable, zero optional deps
from .a2a_client import SynapseA2AClient


# ---------------------------------------------------------------------------
# Lazy accessors for optional integrations
# ---------------------------------------------------------------------------

def __getattr__(name: str):
    """Lazy-load optional adapters only when accessed."""

    # LangChain adapters
    if name in ("SynapseMemory", "SynapseChatHistory"):
        try:
            from . import langchain_memory as _lc  # noqa: F811
        except ImportError as exc:
            raise ImportError(
                f"{name} requires langchain-core. "
                "Install with: pip install 'synapse-layer[langchain]'"
            ) from exc
        return getattr(_lc, name)

    # CrewAI tools
    if name in (
        "SynapseStoreMemoryTool",
        "SynapseRecallMemoryTool",
        "SynapseHandoverTool",
    ):
        try:
            from . import crewai_tools as _ct  # noqa: F811
        except ImportError as exc:
            raise ImportError(
                f"{name} requires crewai. "
                "Install with: pip install 'synapse-layer[crewai]'"
            ) from exc
        return getattr(_ct, name)

    raise AttributeError(f"module 'synapse_layer' has no attribute {name!r}")


__all__ = [
    "__version__",
    # Core
    "SynapseA2AClient",
    # LangChain (lazy)
    "SynapseMemory",
    "SynapseChatHistory",
    # CrewAI (lazy)
    "SynapseStoreMemoryTool",
    "SynapseRecallMemoryTool",
    "SynapseHandoverTool",
]
