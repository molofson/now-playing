"""
Module registry for extensible features, enhancements, and capabilities.
Supports debug logging, enable/disable states, and future extensibility.
"""

import logging
from typing import Dict, Set


class ModuleRegistry:
    """Registry for application modules with debug logging, enable/disable, and extensibility."""

    def __init__(self):
        """Initialize the module registry."""
        self._modules: Dict[str, dict] = {}
        # Modules will be registered by their respective components

    def register_module(
        self,
        name: str,
        description: str,
        logger_name: str,
        debug_flag: str,
        enabled: bool = True,
        category: str = "feature",
    ):
        """Register a new module with essential metadata."""
        self._modules[name] = {
            "description": description,
            "logger_name": logger_name,
            "debug_flag": debug_flag,
            "logger": logging.getLogger(logger_name),
            "enabled": enabled,
            "category": category,
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

    def get_categories(self) -> Set[str]:
        """Get all unique categories."""
        return {info["category"] for info in self._modules.values()}


# Global registry instance
module_registry = ModuleRegistry()

# Backward compatibility alias for existing debug code
debug_registry = module_registry
