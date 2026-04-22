"""
Synapse Layer — Universal memory layer for AI agents.
Persistent, Private, Model-agnostic.

MCP-native. LangChain-compatible. A2A-ready.
"""

__version__ = "1.0.2"

from .a2a_client import SynapseA2AClient
from .langchain_memory import SynapseMemory

__all__ = ["SynapseA2AClient", "SynapseMemory", "__version__"]
