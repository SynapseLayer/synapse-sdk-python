"""
Synapse Layer — Plugin System
Extensible memory resolver architecture.
"""

from synapse_layer.plugins.base import MemoryResolverPlugin, PluginRegistry, default_registry

__all__ = ["MemoryResolverPlugin", "PluginRegistry", "default_registry"]
