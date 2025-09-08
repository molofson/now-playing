"""
Plugin system for user-extensible content panels and enrichment services.

This module provides a framework for loading and managing user-defined
panels and enrichment services from external Python files or packages.
"""

import importlib.util
import inspect
import logging
import os
import sys
from typing import Any, Dict, List, Optional

from .enrichment_services import EnrichmentService, enrichment_engine
from .music_views import ContentPanel, content_panel_registry


class PluginLoader:
    """Loads and manages user-defined plugins."""

    def __init__(self, plugin_dirs: Optional[List[str]] = None):
        """Initialize the plugin loader with search directories."""
        self.plugin_dirs = plugin_dirs or self._get_default_plugin_dirs()
        self.loaded_plugins: Dict[str, Dict[str, Any]] = {}
        self.logger = logging.getLogger("discovery.plugins")

    def _get_default_plugin_dirs(self) -> List[str]:
        """Get default plugin directories."""
        dirs = []

        # User's home directory plugins
        home_plugins = os.path.expanduser("~/.config/music-discovery/plugins")
        if os.path.exists(home_plugins):
            dirs.append(home_plugins)

        # System-wide plugins
        system_plugins = "/etc/music-discovery/plugins"
        if os.path.exists(system_plugins):
            dirs.append(system_plugins)

        # Local plugins directory
        local_plugins = os.path.join(os.path.dirname(__file__), "plugins")
        if os.path.exists(local_plugins):
            dirs.append(local_plugins)

        return dirs

    def load_all_plugins(self) -> None:
        """Load all plugins from plugin directories."""
        self.logger.info("Loading plugins from directories: %s", self.plugin_dirs)

        for plugin_dir in self.plugin_dirs:
            if os.path.isdir(plugin_dir):
                self._load_plugins_from_directory(plugin_dir)

        self.logger.info("Loaded %d plugins", len(self.loaded_plugins))

    def _load_plugins_from_directory(self, plugin_dir: str) -> None:
        """Load plugins from a specific directory."""
        for item in os.listdir(plugin_dir):
            item_path = os.path.join(plugin_dir, item)

            if item.endswith(".py") and not item.startswith("_"):
                # Single Python file plugin
                self._load_plugin_file(item_path)
            elif os.path.isdir(item_path) and not item.startswith("_"):
                # Package plugin
                self._load_plugin_package(item_path)

    def _load_plugin_file(self, file_path: str) -> None:
        """Load a plugin from a Python file."""
        try:
            plugin_name = os.path.splitext(os.path.basename(file_path))[0]

            # Load the module
            spec = importlib.util.spec_from_file_location(plugin_name, file_path)
            if not spec or not spec.loader:
                self.logger.warning("Could not load plugin spec: %s", file_path)
                return

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Register components from the module
            self._register_plugin_components(plugin_name, module)

            self.logger.info("Loaded plugin: %s", plugin_name)

        except Exception as e:
            self.logger.error("Failed to load plugin %s: %s", file_path, e)

    def _load_plugin_package(self, package_path: str) -> None:
        """Load a plugin package."""
        try:
            package_name = os.path.basename(package_path)

            # Check for __init__.py
            init_file = os.path.join(package_path, "__init__.py")
            if not os.path.exists(init_file):
                self.logger.warning("Plugin package missing __init__.py: %s", package_path)
                return

            # Add package directory to path temporarily
            sys.path.insert(0, os.path.dirname(package_path))

            try:
                module = importlib.import_module(package_name)
                self._register_plugin_components(package_name, module)
                self.logger.info("Loaded plugin package: %s", package_name)
            finally:
                # Remove from path
                if os.path.dirname(package_path) in sys.path:
                    sys.path.remove(os.path.dirname(package_path))

        except Exception as e:
            self.logger.error("Failed to load plugin package %s: %s", package_path, e)

    def _register_plugin_components(self, plugin_name: str, module) -> None:
        """Register panels and services from a plugin module."""
        plugin_info = {
            "name": plugin_name,
            "module": module,
            "panels": [],
            "services": [],
        }

        # Look for panel classes
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, ContentPanel) and obj != ContentPanel:
                try:
                    panel_instance = obj()
                    content_panel_registry.register_panel(panel_instance)
                    plugin_info["panels"].append(panel_instance.info.id)
                    self.logger.debug("Registered panel: %s from plugin %s", panel_instance.info.id, plugin_name)
                except Exception as e:
                    self.logger.error("Failed to register panel %s: %s", name, e)

        # Look for enrichment service classes
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, EnrichmentService) and obj != EnrichmentService:
                try:
                    service_instance = obj()
                    enrichment_engine.register_service(service_instance)
                    plugin_info["services"].append(service_instance.service_id)
                    self.logger.debug(
                        "Registered enrichment service: %s from plugin %s", service_instance.service_id, plugin_name
                    )
                except Exception as e:
                    self.logger.error("Failed to register service %s: %s", name, e)

        # Look for registration functions
        if hasattr(module, "register_plugin"):
            try:
                module.register_plugin()
                self.logger.debug("Called register_plugin() for %s", plugin_name)
            except Exception as e:
                self.logger.error("Error calling register_plugin() for %s: %s", plugin_name, e)

        self.loaded_plugins[plugin_name] = plugin_info

    def get_plugin_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about loaded plugins."""
        return {
            name: {
                "name": info["name"],
                "panels": info["panels"],
                "services": info["services"],
                "has_module": info["module"] is not None,
            }
            for name, info in self.loaded_plugins.items()
        }

    def unload_plugin(self, plugin_name: str) -> bool:
        """Unload a plugin (remove its panels and services)."""
        if plugin_name not in self.loaded_plugins:
            return False

        plugin_info = self.loaded_plugins[plugin_name]

        # Unregister panels
        for panel_id in plugin_info["panels"]:
            content_panel_registry.unregister_panel(panel_id)

        # Disable services (can't easily unregister from enrichment engine)
        for service_id in plugin_info["services"]:
            enrichment_engine.disable_service(service_id)

        # Remove from loaded plugins
        del self.loaded_plugins[plugin_name]

        self.logger.info("Unloaded plugin: %s", plugin_name)
        return True


# Example plugin template that users can copy
EXAMPLE_PANEL_PLUGIN = '''"""
Example content panel plugin.

Copy this file to your plugins directory and modify to create custom panels.
Location: ~/.config/music-discovery/plugins/my_panel.py
"""

import pygame
from nowplaying.music_views import ContentPanel, PanelInfo, ContentContext


class ExamplePanel(ContentPanel):
    """Example custom content panel."""

    def __init__(self):
        info = PanelInfo(
            id="example_panel",
            name="Example Panel",
            description="An example of a custom content panel",
            icon="🎨",
            category="custom",
            requires_metadata=True
        )
        super().__init__(info)

    def update_context(self, context: ContentContext) -> None:
        """Update with new content context."""
        self._context = context

    def render(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        """Render the panel."""
        if not self._context:
            return

        # Example rendering
        font = pygame.font.Font(None, 24)

        # Title
        title = font.render("Custom Panel", True, (255, 255, 255))
        surface.blit(title, (rect.x + 20, rect.y + 20))

        # Artist info
        if self._context.artist:
            artist_text = f"Artist: {self._context.artist}"
            artist_surface = font.render(artist_text, True, (200, 200, 200))
            surface.blit(artist_surface, (rect.x + 20, rect.y + 60))

        # Custom visualization here
        pygame.draw.circle(surface, (100, 150, 255),
                         (rect.centerx, rect.centery), 50, 3)

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handle events."""
        # Custom event handling here
        return False


# Optional: Registration function for more complex setup
def register_plugin():
    """Called when plugin is loaded."""
    print("Example plugin registered!")
'''

EXAMPLE_SERVICE_PLUGIN = '''"""
Example enrichment service plugin.

Copy this file to your plugins directory and modify to create custom services.
Location: ~/.config/music-discovery/plugins/my_service.py
"""

import asyncio
from nowplaying.enrichment_services import EnrichmentService, EnrichmentData, EnrichmentRequest


class ExampleService(EnrichmentService):
    """Example custom enrichment service."""

    def __init__(self):
        super().__init__("example_service", "Example Service", enabled=True)
        self._rate_limit_delay = 2.0  # Be nice to APIs

    async def enrich(self, request: EnrichmentRequest) -> EnrichmentData:
        """Enrich metadata with custom data."""
        if not self.can_enrich(request):
            return None

        await self._rate_limit()

        try:
            # Your custom enrichment logic here
            # This could call external APIs, databases, etc.

            enrichment = EnrichmentData()

            # Example: add custom tags based on artist
            if "rock" in request.artist.lower():
                enrichment.artist_tags = ["rock", "guitar-driven"]

            # Example: mock tour dates
            enrichment.tour_dates = [
                {"date": "2024-01-15", "venue": "Example Venue", "city": "Example City"}
            ]

            enrichment.last_updated["example_service"] = time.time()

            return enrichment

        except Exception as e:
            self.logger.error("Example service failed: %s", e)
            enrichment = EnrichmentData()
            enrichment.service_errors["example_service"] = str(e)
            return enrichment


def register_plugin():
    """Called when plugin is loaded."""
    print("Example enrichment service registered!")
'''


def create_example_plugins(plugins_dir: str) -> None:
    """Create example plugin files for users to modify."""
    os.makedirs(plugins_dir, exist_ok=True)

    # Create example panel
    panel_file = os.path.join(plugins_dir, "example_panel.py")
    if not os.path.exists(panel_file):
        with open(panel_file, "w") as f:
            f.write(EXAMPLE_PANEL_PLUGIN)

    # Create example service
    service_file = os.path.join(plugins_dir, "example_service.py")
    if not os.path.exists(service_file):
        with open(service_file, "w") as f:
            f.write(EXAMPLE_SERVICE_PLUGIN)

    # Create README
    readme_file = os.path.join(plugins_dir, "README.md")
    if not os.path.exists(readme_file):
        with open(readme_file, "w") as f:
            f.write(
                """# Music Discovery Plugins

This directory contains user-defined plugins for the Music Discovery application.

## Panel Plugins
Create ContentPanel subclasses to add custom swipeable panels.
See `example_panel.py` for a template.

## Service Plugins
Create EnrichmentService subclasses to add custom metadata enrichment.
See `example_service.py` for a template.

## Loading
Plugins are automatically loaded when the application starts.
"""
            )


# Global plugin loader instance
plugin_loader = PluginLoader()
