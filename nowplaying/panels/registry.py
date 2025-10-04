"""
Global registry instance for content panels.

This module provides the single global instance of ContentPanelRegistry
that manages all available panels in the application.
"""

from .base import ContentPanelRegistry

# Global registry instance
content_panel_registry = ContentPanelRegistry()
