"""
Module registry for extensible features, enhancements, and capabilities.

Supports debug logging, enable/disable states, and future extensibility.
"""

import logging
from typing import Any, Dict, Optional, Set


class ModuleRegistry:
    """Registry for application modules with debug logging, enable/disable, and extensibility."""

    def __init__(self):
        """Initialize the module registry with built-in modules."""
        self._modules: Dict[str, dict] = {}
        self._register_builtin_modules()

    def _register_builtin_modules(self):
        """Register the built-in core modules."""
        self.register_module(
            name="playback_metadata",
            description="Song metadata processing (artist, album, title, genre)",
            logger_name="playback_metadata",
            debug_flag="--debug-metadata",
            enabled_by_default=True,
            category="core",
        )

        self.register_module(
            name="playback_state",
            description="State transitions (play, pause, stop, waiting)",
            logger_name="playback_state",
            debug_flag="--debug-state",
            enabled_by_default=True,
            category="core",
        )

    def register_module(
        self,
        name: str,
        description: str,
        logger_name: str,
        debug_flag: str,
        enabled_by_default: bool = True,
        category: str = "feature",
        dependencies: Optional[list] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """Register a new module with full metadata."""
        self._modules[name] = {
            "description": description,
            "logger_name": logger_name,
            "debug_flag": debug_flag,
            "logger": logging.getLogger(logger_name),
            "enabled": enabled_by_default,
            "enabled_by_default": enabled_by_default,
            "category": category,
            "dependencies": dependencies or [],
            "config": config or {},
        }

    def enable_module(self, name: str) -> bool:
        """Enable a module if it exists."""
        if name in self._modules:
            self._modules[name]["enabled"] = True
            return True
        return False

    def disable_module(self, name: str) -> bool:
        """Disable a module if it exists."""
        if name in self._modules:
            self._modules[name]["enabled"] = False
            return True
        return False

    def is_module_enabled(self, name: str) -> bool:
        """Check if a module is enabled."""
        return self._modules.get(name, {}).get("enabled", False)

    def get_enabled_modules(self) -> Dict[str, dict]:
        """Get all enabled modules."""
        return {name: info for name, info in self._modules.items() if info["enabled"]}

    def get_modules_by_category(self, category: str) -> Dict[str, dict]:
        """Get all modules in a specific category."""
        return {name: info for name, info in self._modules.items() if info["category"] == category}

    def get_all_modules(self) -> Dict[str, dict]:
        """Get all registered modules."""
        return self._modules.copy()

    def get_module_names(self) -> Set[str]:
        """Get all module names."""
        return set(self._modules.keys())

    def get_debug_logger_names(self) -> Set[str]:
        """Get all logger names for debug filtering."""
        return {info["logger_name"] for info in self._modules.values()}

    def get_debug_flags(self) -> Dict[str, str]:
        """Get mapping of debug CLI flags to module names."""
        return {info["debug_flag"]: name for name, info in self._modules.items()}

    def get_module_info(self, name: str) -> dict:
        """Get information about a specific module."""
        return self._modules.get(name, {})

    def validate_dependencies(self, name: str) -> bool:
        """Check if all dependencies for a module are enabled."""
        module_info = self._modules.get(name, {})
        dependencies = module_info.get("dependencies", [])

        return all(self.is_module_enabled(dep) for dep in dependencies)

    def get_categories(self) -> Set[str]:
        """Get all unique categories."""
        return {info["category"] for info in self._modules.values()}


# Global registry instance
module_registry = ModuleRegistry()

# Backward compatibility alias for existing debug code
debug_registry = module_registry
