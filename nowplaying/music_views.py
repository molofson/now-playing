"""
Content exploration system for swipeable discovery experiences.

This module is now minimal and serves as a legacy placeholder.
All content panel functionality has been moved to the nowplaying.panels package.
Use imports from nowplaying.panels instead.
"""

# For any legacy code that might still import from here, redirect to panels package
from .panels import (  # noqa: F401 - convenience re-exports, used by existing code
    ContentContext,
    ContentPanel,
    ContentPanelRegistry,
    PanelInfo,
    content_panel_registry,
)
