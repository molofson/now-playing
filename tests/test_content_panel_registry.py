"""
Tests for ContentPanelRegistry.

This module tests the panel registry system including:
- Panel registration and management
- Context management (live vs held)
- Panel filtering and ordering
- Registry status and debugging
"""

from datetime import datetime
from unittest.mock import patch

import pytest

from nowplaying.panels.base import ContentContext, ContentPanel, ContentPanelRegistry, PanelInfo


class MockContentPanel(ContentPanel):
    """Mock panel for testing registry functionality."""

    def __init__(self, panel_info, supports_hold_override=None):
        """Initialize mock panel."""
        super().__init__(panel_info)
        self.update_context_calls = []
        self.supports_hold_override = supports_hold_override

    def update_context(self, context: ContentContext) -> None:
        """Track context updates."""
        super().update_context(context)
        self.update_context_calls.append(context)

    def render(self, surface, rect) -> None:  # noqa: U100
        """Mock render method."""
        pass

    def handle_event(self, event) -> bool:  # noqa: U100
        """Mock event handler."""
        return False

    def supports_hold(self) -> bool:
        """Override supports_hold if specified."""
        if self.supports_hold_override is not None:
            return self.supports_hold_override
        return super().supports_hold()


class TestContentPanelRegistry:
    """Tests for ContentPanelRegistry."""

    def setup_method(self):
        """Set up test fixtures."""
        self.registry = ContentPanelRegistry()

        # Create test panels
        self.panel1_info = PanelInfo(
            id="panel1",
            name="Panel 1",
            description="First test panel",
            icon="🎵",
            category="general",
        )
        self.panel1 = MockContentPanel(self.panel1_info)

        self.panel2_info = PanelInfo(
            id="panel2",
            name="Panel 2",
            description="Second test panel",
            icon="🎶",
            category="debug",
        )
        self.panel2 = MockContentPanel(self.panel2_info)

        self.audio_panel_info = PanelInfo(
            id="audio_panel",
            name="Audio Panel",
            description="Audio visualization panel",
            icon="🔊",
            category="audio",
            requires_audio_data=True,
        )
        self.audio_panel = MockContentPanel(self.audio_panel_info, supports_hold_override=False)

    def test_registry_initialization(self):
        """Test registry initialization."""
        assert len(self.registry._panels) == 0
        assert len(self.registry._panel_order) == 0
        assert self.registry._live_context is None
        assert self.registry._held_context is None

    def test_register_panel(self):
        """Test registering a panel."""
        self.registry.register_panel(self.panel1)

        assert len(self.registry._panels) == 1
        assert self.registry._panels["panel1"] == self.panel1
        assert self.registry._panel_order == ["panel1"]

    def test_register_multiple_panels(self):
        """Test registering multiple panels maintains order."""
        self.registry.register_panel(self.panel1)
        self.registry.register_panel(self.panel2)

        assert len(self.registry._panels) == 2
        assert self.registry._panel_order == ["panel1", "panel2"]

    def test_register_duplicate_panel_raises_error(self):
        """Test registering duplicate panel ID raises error."""
        self.registry.register_panel(self.panel1)

        duplicate_panel = MockContentPanel(self.panel1_info)
        with pytest.raises(ValueError, match="Panel with id 'panel1' already registered"):
            self.registry.register_panel(duplicate_panel)

    def test_unregister_panel(self):
        """Test unregistering a panel."""
        self.registry.register_panel(self.panel1)
        self.registry.register_panel(self.panel2)

        result = self.registry.unregister_panel("panel1")

        assert result is True
        assert len(self.registry._panels) == 1
        assert "panel1" not in self.registry._panels
        assert self.registry._panel_order == ["panel2"]

    def test_unregister_nonexistent_panel(self):
        """Test unregistering nonexistent panel returns False."""
        result = self.registry.unregister_panel("nonexistent")

        assert result is False
        assert len(self.registry._panels) == 0

    def test_get_panel(self):
        """Test getting panel by ID."""
        self.registry.register_panel(self.panel1)

        panel = self.registry.get_panel("panel1")
        assert panel == self.panel1

        nonexistent = self.registry.get_panel("nonexistent")
        assert nonexistent is None

    def test_get_panel_ids(self):
        """Test getting ordered panel IDs."""
        self.registry.register_panel(self.panel1)
        self.registry.register_panel(self.panel2)

        ids = self.registry.get_panel_ids()
        assert ids == ["panel1", "panel2"]

        # Verify it's a copy (modifying doesn't affect registry)
        ids.append("test")
        assert self.registry._panel_order == ["panel1", "panel2"]

    def test_get_available_panels_all_enabled(self):
        """Test getting all available panels when enabled."""
        self.registry.register_panel(self.panel1)
        self.registry.register_panel(self.panel2)

        panels = self.registry.get_available_panels()

        assert len(panels) == 2
        assert panels[0] == self.panel1  # Order preserved
        assert panels[1] == self.panel2

    def test_get_available_panels_some_disabled(self):
        """Test getting available panels with some disabled."""
        self.panel2_info.enabled = False
        self.registry.register_panel(self.panel1)
        self.registry.register_panel(self.panel2)

        panels = self.registry.get_available_panels()

        assert len(panels) == 1
        assert panels[0] == self.panel1

    def test_get_available_panels_filtered_by_context(self):
        """Test getting panels filtered by context compatibility."""
        # Panel requiring audio data
        self.registry.register_panel(self.panel1)
        self.registry.register_panel(self.audio_panel)

        # Context without audio data
        context = ContentContext(artist="Test Artist")
        panels = self.registry.get_available_panels(context)

        assert len(panels) == 1
        assert panels[0] == self.panel1  # Only panel1 can display this context

    def test_get_available_panels_with_compatible_context(self):
        """Test getting panels with compatible context."""
        self.registry.register_panel(self.panel1)
        self.registry.register_panel(self.audio_panel)

        # Context with audio data
        context = ContentContext(artist="Test Artist", audio_levels={"left": 0.5, "right": 0.6})
        panels = self.registry.get_available_panels(context)

        assert len(panels) == 2  # Both panels can display this context

    def test_get_panels_by_category(self):
        """Test getting panels by category."""
        self.registry.register_panel(self.panel1)  # general category
        self.registry.register_panel(self.panel2)  # debug category
        self.registry.register_panel(self.audio_panel)  # audio category

        general_panels = self.registry.get_panels_by_category("general")
        debug_panels = self.registry.get_panels_by_category("debug")
        audio_panels = self.registry.get_panels_by_category("audio")

        assert len(general_panels) == 1
        assert general_panels[0] == self.panel1
        assert len(debug_panels) == 1
        assert debug_panels[0] == self.panel2
        assert len(audio_panels) == 1
        assert audio_panels[0] == self.audio_panel

    def test_get_panels_by_category_respects_enabled(self):
        """Test get_panels_by_category only returns enabled panels."""
        self.panel1_info.enabled = False
        self.registry.register_panel(self.panel1)

        general_panels = self.registry.get_panels_by_category("general")

        assert len(general_panels) == 0

    def test_update_live_context(self):
        """Test updating live context updates appropriate panels."""
        self.registry.register_panel(self.panel1)
        self.registry.register_panel(self.audio_panel)

        context = ContentContext(artist="Test Artist")
        self.registry.update_live_context(context)

        assert self.registry._live_context == context
        # Both panels should be updated
        assert len(self.panel1.update_context_calls) == 1
        assert len(self.audio_panel.update_context_calls) == 1
        assert self.panel1.update_context_calls[0] == context

    def test_set_held_context(self):
        """Test setting held context."""
        self.registry.register_panel(self.panel1)
        self.registry.register_panel(self.audio_panel)

        context = ContentContext(artist="Test Artist", source="live")

        with patch("nowplaying.panels.base.datetime") as mock_datetime:
            mock_now = datetime(2023, 1, 1, 12, 0, 0)
            mock_datetime.now.return_value = mock_now

            self.registry.set_held_context(context)

        # Verify held context is created
        held_context = self.registry._held_context
        assert held_context is not None
        assert held_context.is_held is True
        assert held_context.source == "held"
        assert held_context.artist == "Test Artist"

        # Only panel1 should be updated (supports hold)
        assert len(self.panel1.update_context_calls) == 1
        assert len(self.audio_panel.update_context_calls) == 0
        assert self.panel1.update_context_calls[0] == held_context

    def test_update_live_context_with_held_context(self):
        """Test live context updates with held context active."""
        self.registry.register_panel(self.panel1)
        self.registry.register_panel(self.audio_panel)

        # Set held context first
        held_context = ContentContext(artist="Held Artist")
        self.registry.set_held_context(held_context)

        # Clear call history
        self.panel1.update_context_calls.clear()
        self.audio_panel.update_context_calls.clear()

        # Update live context
        live_context = ContentContext(artist="Live Artist")
        self.registry.update_live_context(live_context)

        # panel1 should keep held context, audio_panel should get live context
        assert len(self.panel1.update_context_calls) == 0  # No update (has held context)
        assert len(self.audio_panel.update_context_calls) == 1  # Gets live update
        assert self.audio_panel.update_context_calls[0] == live_context

    def test_release_held_context(self):
        """Test releasing held context returns to live updates."""
        self.registry.register_panel(self.panel1)
        self.registry.register_panel(self.audio_panel)

        # Set up live and held contexts
        live_context = ContentContext(artist="Live Artist")
        held_context = ContentContext(artist="Held Artist")

        self.registry.update_live_context(live_context)
        self.registry.set_held_context(held_context)

        # Clear call history
        self.panel1.update_context_calls.clear()
        self.audio_panel.update_context_calls.clear()

        # Release held context
        self.registry.release_held_context()

        assert self.registry._held_context is None

        # All panels should be updated with live context
        assert len(self.panel1.update_context_calls) == 1
        assert len(self.audio_panel.update_context_calls) == 1
        assert self.panel1.update_context_calls[0] == live_context
        assert self.audio_panel.update_context_calls[0] == live_context

    def test_release_held_context_no_live_context(self):
        """Test releasing held context with no live context."""
        self.registry.register_panel(self.panel1)

        held_context = ContentContext(artist="Held Artist")
        self.registry.set_held_context(held_context)

        # Clear call history
        self.panel1.update_context_calls.clear()

        # Release held context (no live context to fall back to)
        self.registry.release_held_context()

        assert self.registry._held_context is None
        # No updates should happen without live context
        assert len(self.panel1.update_context_calls) == 0

    def test_get_live_context(self):
        """Test getting live context."""
        assert self.registry.get_live_context() is None

        context = ContentContext(artist="Test Artist")
        self.registry.update_live_context(context)

        assert self.registry.get_live_context() == context

    def test_get_held_context(self):
        """Test getting held context."""
        assert self.registry.get_held_context() is None

        context = ContentContext(artist="Test Artist")
        self.registry.set_held_context(context)

        held = self.registry.get_held_context()
        assert held is not None
        assert held.is_held is True
        assert held.artist == "Test Artist"

    def test_has_held_context(self):
        """Test checking for held context."""
        assert self.registry.has_held_context() is False

        context = ContentContext(artist="Test Artist")
        self.registry.set_held_context(context)

        assert self.registry.has_held_context() is True

        self.registry.release_held_context()

        assert self.registry.has_held_context() is False

    def test_get_registry_status_empty(self):
        """Test registry status with no panels or context."""
        status = self.registry.get_registry_status()

        assert status["total_panels"] == 0
        assert status["enabled_panels"] == 0
        assert status["panel_order"] == []
        assert status["categories"] == set()
        assert status["has_live_context"] is False
        assert status["has_held_context"] is False
        assert status["live_artist"] is None
        assert status["held_artist"] is None

    def test_get_registry_status_with_panels_and_context(self):
        """Test registry status with panels and contexts."""
        self.panel2_info.enabled = False  # One disabled panel
        self.registry.register_panel(self.panel1)
        self.registry.register_panel(self.panel2)
        self.registry.register_panel(self.audio_panel)

        live_context = ContentContext(artist="Live Artist")
        held_context = ContentContext(artist="Held Artist")

        self.registry.update_live_context(live_context)
        self.registry.set_held_context(held_context)

        status = self.registry.get_registry_status()

        assert status["total_panels"] == 3
        assert status["enabled_panels"] == 2  # panel2 is disabled
        assert status["panel_order"] == ["panel1", "panel2", "audio_panel"]
        assert status["categories"] == {"general", "debug", "audio"}
        assert status["has_live_context"] is True
        assert status["has_held_context"] is True
        assert status["live_artist"] == "Live Artist"
        assert status["held_artist"] == "Held Artist"

    def test_registry_status_returns_copy(self):
        """Test that registry status returns copies of internal data."""
        self.registry.register_panel(self.panel1)

        status = self.registry.get_registry_status()
        panel_order = status["panel_order"]

        # Modifying returned data shouldn't affect registry
        panel_order.append("test")
        assert self.registry._panel_order == ["panel1"]
