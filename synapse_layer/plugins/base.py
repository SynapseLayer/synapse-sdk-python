"""
Synapse Layer — Plugin System Base Classes
Extensible resolver architecture for conflict resolution and memory validation.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
import uuid


@dataclass
class MemoryCandidate:
    """A memory entry and its relevance/credibility score."""
    memory_id: str
    content: str
    embedding: List[float]
    relevance_score: float  # 0.0 to 1.0, from cosine similarity
    source: str  # "user_input", "retrieval", "handover", etc.
    timestamp: str  # ISO 8601
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResolverDecision:
    """Outcome of conflict resolution or validation."""
    decision_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    winner_memory_id: Optional[str] = None  # if conflict, which memory wins
    reasoning: str = ""  # human-readable explanation
    confidence: float = 1.0  # 0.0 to 1.0
    action: str = "accept"  # "accept", "reject", "merge", "deprecate"
    deprecated_ids: List[str] = field(default_factory=list)  # IDs to mark deprecated
    metadata: Dict[str, Any] = field(default_factory=dict)


class MemoryResolverPlugin(ABC):
    """Abstract base class for memory resolution plugins.
    
    Plugins implement domain-specific logic for validating, comparing,
    and resolving conflicts between memory candidates.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique plugin name (e.g., 'medical_truth', 'financial_fact_checker')."""
        pass
    
    @abstractmethod
    def can_handle(self, candidates: List[MemoryCandidate]) -> bool:
        """Check if this plugin should handle the given candidates.
        
        Args:
            candidates: List of memory candidates to evaluate
            
        Returns:
            True if this plugin can resolve these candidates, False otherwise
        """
        pass
    
    @abstractmethod
    def resolve(self, candidates: List[MemoryCandidate]) -> ResolverDecision:
        """Resolve conflict or validate candidates using domain-specific logic.
        
        Args:
            candidates: List of memory candidates to resolve
            
        Returns:
            ResolverDecision with the outcome and reasoning
        """
        pass
    
    def on_load(self) -> None:
        """Called when plugin is registered. Override for initialization."""
        pass
    
    def on_unload(self) -> None:
        """Called when plugin is unregistered. Override for cleanup."""
        pass


class PluginRegistry:
    """Global registry for managing memory resolver plugins."""
    
    def __init__(self):
        """Initialize the plugin registry."""
        self._plugins: Dict[str, MemoryResolverPlugin] = {}
        self._plugin_order: List[str] = []  # Ordering for fallback logic
    
    def register(self, plugin: MemoryResolverPlugin) -> None:
        """Register a new plugin.
        
        Args:
            plugin: MemoryResolverPlugin instance to register
        """
        name = plugin.name
        if name in self._plugins:
            raise ValueError(f"Plugin '{name}' is already registered")
        
        self._plugins[name] = plugin
        self._plugin_order.append(name)
        plugin.on_load()
    
    def unregister(self, plugin_name: str) -> None:
        """Unregister a plugin.
        
        Args:
            plugin_name: Name of the plugin to unregister
        """
        if plugin_name not in self._plugins:
            raise ValueError(f"Plugin '{plugin_name}' not found")
        
        plugin = self._plugins.pop(plugin_name)
        self._plugin_order.remove(plugin_name)
        plugin.on_unload()
    
    def find_handler(self, candidates: List[MemoryCandidate]) -> Optional[MemoryResolverPlugin]:
        """Find the first plugin that can handle the given candidates.
        
        Args:
            candidates: List of memory candidates to resolve
            
        Returns:
            The first matching plugin, or None if no plugin can handle
        """
        for plugin_name in self._plugin_order:
            plugin = self._plugins[plugin_name]
            if plugin.can_handle(candidates):
                return plugin
        return None
    
    def get_plugin(self, plugin_name: str) -> Optional[MemoryResolverPlugin]:
        """Get a plugin by name.
        
        Args:
            plugin_name: Name of the plugin
            
        Returns:
            The plugin, or None if not found
        """
        return self._plugins.get(plugin_name)
    
    def list_plugins(self) -> List[str]:
        """List all registered plugin names.
        
        Returns:
            List of plugin names in registration order
        """
        return self._plugin_order.copy()


# Global default registry
default_registry = PluginRegistry()
