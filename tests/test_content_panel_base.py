"""
Tests for ContentPanel base class and related components.

This module tests the foundational panel system including:
- ContentContext data structure
- PanelInfo metadata
- ContentPanel abstract base class
- Panel display logic and context management
"""

from datetime import datetime
from unittest.mock import Mock, patch

import pygame
import pytest  # noqa: I201

from nowplaying.panels.base import ContentContext, ContentPanel, PanelInfo
from nowplaying.playback_state import PlaybackState


class ConcreteContentPanel(ContentPanel):
    """Concrete implementation for testing the abstract base class."""

    def __init__(self, panel_info):
        """Initialize concrete test panel."""
        super().__init__(panel_info)
        self.render_called = False
        self.event_handled = False
        self.last_context = None

    def update_context(self, context: ContentContext) -> None:
        """Update with new content context."""
        super().update_context(context)
        self.last_context = context

    def render(self, surface, rect) -> None:  # noqa: U100
        """Render the panel."""
        self.render_called = True

    def handle_event(self, event) -> bool:  # noqa: U100
        """Handle pygame events."""
        self.event_handled = True
        return True  # Consume the event


class TestContentContext:
    """Tests for ContentContext data class."""

    def test_content_context_defaults(self):
        """Test ContentContext default values."""
        context = ContentContext()

        assert context.artist == ""
        assert context.album == ""
        assert context.title == ""
        assert context.genre == ""
        assert context.cover_art_path is None
        assert context.playback_state == PlaybackState.NO_SESSION
        assert context.is_held is False
        assert context.source == "live"

    def test_content_context_from_metadata(self):
        """Test creating ContentContext from metadata dict."""
        metadata = {
            "artist": "Test Artist",
            "album": "Test Album",
            "title": "Test Song",
            "genre": "Rock",
            "year": "2023",
            "duration": 180.5,
            "cover_art_path": "/path/to/art.jpg",
        }

        context = ContentContext.from_metadata(metadata, PlaybackState.PLAYING)

        assert context.artist == "Test Artist"
        assert context.album == "Test Album"
        assert context.title == "Test Song"
        assert context.genre == "Rock"
        assert context.year == "2023"
        assert context.duration == 180.5
        assert context.cover_art_path == "/path/to/art.jpg"
        assert context.playback_state == PlaybackState.PLAYING
        assert context.is_held is False
        assert context.source == "live"

    def test_content_context_from_metadata_manual_source(self):
        """Test creating ContentContext with manual source."""
        metadata = {"artist": "Test Artist"}

        context = ContentContext.from_metadata(metadata, PlaybackState.PLAYING, is_live=False)

        assert context.source == "manual"
        assert context.is_held is False

    def test_content_context_hold(self):
        """Test creating held copy of ContentContext."""
        original = ContentContext(
            artist="Test Artist",
            album="Test Album",
            title="Test Song",
            playback_state=PlaybackState.PLAYING,
            source="live",
        )

        with patch("nowplaying.panels.base.datetime") as mock_datetime:
            mock_now = datetime(2023, 1, 1, 12, 0, 0)
            mock_datetime.now.return_value = mock_now

            held = original.hold()

        # Verify held copy has different state
        assert held.is_held is True
        assert held.source == "held"
        assert held.held_timestamp == mock_now

        # Verify content is copied
        assert held.artist == "Test Artist"
        assert held.album == "Test Album"
        assert held.title == "Test Song"
        assert held.playback_state == PlaybackState.PLAYING

        # Verify original is unchanged
        assert original.is_held is False
        assert original.source == "live"
        assert original.held_timestamp is None


class TestPanelInfo:
    """Tests for PanelInfo data class."""

    def test_panel_info_defaults(self):
        """Test PanelInfo default values."""
        info = PanelInfo(id="test_panel", name="Test Panel", description="A test panel", icon="🎵")

        assert info.id == "test_panel"
        assert info.name == "Test Panel"
        assert info.description == "A test panel"
        assert info.icon == "🎵"
        assert info.category == "general"
        assert info.enabled is True
        assert info.requires_cover_art is False
        assert info.requires_metadata is True
        assert info.requires_audio_data is False
        assert info.requires_network is False

    def test_panel_info_custom_requirements(self):
        """Test PanelInfo with custom requirements."""
        info = PanelInfo(
            id="audio_panel",
            name="Audio Panel",
            description="Requires audio data",
            icon="🔊",
            category="audio",
            requires_audio_data=True,
            requires_cover_art=True,
            requires_network=True,
        )

        assert info.category == "audio"
        assert info.requires_audio_data is True
        assert info.requires_cover_art is True
        assert info.requires_network is True


class TestContentPanel:
    """Tests for ContentPanel abstract base class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.panel_info = PanelInfo(id="test_panel", name="Test Panel", description="A test panel", icon="🎵")
        self.panel = ConcreteContentPanel(self.panel_info)

    def test_panel_initialization(self):
        """Test ContentPanel initialization."""
        assert self.panel.info == self.panel_info
        assert self.panel._context is None

    def test_panel_info_property(self):
        """Test panel info property access."""
        assert self.panel.info.id == "test_panel"
        assert self.panel.info.name == "Test Panel"

    def test_update_context(self):
        """Test updating panel context."""
        context = ContentContext(artist="Test Artist")

        self.panel.update_context(context)

        assert self.panel._context == context
        assert self.panel.last_context == context

    def test_get_title(self):
        """Test getting panel title."""
        assert self.panel.get_title() == "Test Panel"

    def test_can_display_with_metadata(self):
        """Test can_display with valid metadata."""
        context = ContentContext(artist="Test Artist", title="Test Song")

        assert self.panel.can_display(context) is True

    def test_can_display_no_metadata_required(self):
        """Test can_display when no metadata required."""
        info = PanelInfo(
            id="no_metadata_panel",
            name="No Metadata Panel",
            description="Doesn't need metadata",
            icon="🎵",
            requires_metadata=False,
        )
        panel = ConcreteContentPanel(info)
        context = ContentContext()  # Empty context

        assert panel.can_display(context) is True

    def test_can_display_missing_metadata(self):
        """Test can_display with missing required metadata."""
        context = ContentContext()  # No artist, album, or title

        assert self.panel.can_display(context) is False

    def test_can_display_requires_cover_art(self):
        """Test can_display when cover art is required."""
        info = PanelInfo(
            id="art_panel",
            name="Art Panel",
            description="Needs cover art",
            icon="🎨",
            requires_cover_art=True,
        )
        panel = ConcreteContentPanel(info)

        # Test with cover art
        context_with_art = ContentContext(artist="Test Artist", cover_art_path="/path/to/art.jpg")
        assert panel.can_display(context_with_art) is True

        # Test without cover art
        context_without_art = ContentContext(artist="Test Artist")
        assert panel.can_display(context_without_art) is False

    def test_can_display_requires_audio_data(self):
        """Test can_display when audio data is required."""
        info = PanelInfo(
            id="audio_panel",
            name="Audio Panel",
            description="Needs audio data",
            icon="🔊",
            requires_audio_data=True,
        )
        panel = ConcreteContentPanel(info)

        # Test with audio data
        context_with_audio = ContentContext(artist="Test Artist", audio_levels={"left": 0.5, "right": 0.6})
        assert panel.can_display(context_with_audio) is True

        # Test without audio data
        context_without_audio = ContentContext(artist="Test Artist")
        assert panel.can_display(context_without_audio) is False

    def test_supports_hold_default(self):
        """Test supports_hold default behavior."""
        assert self.panel.supports_hold() is True

    def test_supports_hold_audio_panel(self):
        """Test supports_hold for audio panels."""
        info = PanelInfo(
            id="audio_panel",
            name="Audio Panel",
            description="Audio panel",
            icon="🔊",
            requires_audio_data=True,
        )
        panel = ConcreteContentPanel(info)

        # Audio panels don't support holding (need live data)
        assert panel.supports_hold() is False

    def test_get_status_info_no_context(self):
        """Test get_status_info with no context."""
        status = self.panel.get_status_info()

        assert status["panel_id"] == "test_panel"
        assert status["name"] == "Test Panel"
        assert status["category"] == "general"
        assert status["has_context"] is False
        assert status["can_display"] is False
        assert status["context_source"] is None
        assert status["context_is_held"] is False

    def test_get_status_info_with_context(self):
        """Test get_status_info with context."""
        context = ContentContext(artist="Test Artist", source="live", is_held=False)
        self.panel.update_context(context)

        status = self.panel.get_status_info()

        assert status["panel_id"] == "test_panel"
        assert status["has_context"] is True
        assert status["can_display"] is True
        assert status["context_source"] == "live"
        assert status["context_is_held"] is False

    def test_get_status_info_with_held_context(self):
        """Test get_status_info with held context."""
        context = ContentContext(artist="Test Artist", source="held", is_held=True)
        self.panel.update_context(context)

        status = self.panel.get_status_info()

        assert status["context_source"] == "held"
        assert status["context_is_held"] is True

    def test_abstract_methods_implemented(self):
        """Test that abstract methods are properly implemented."""
        # Test render method
        surface = Mock()
        rect = Mock()
        self.panel.render(surface, rect)
        assert self.panel.render_called is True

        # Test handle_event method
        event = Mock()
        result = self.panel.handle_event(event)
        assert self.panel.event_handled is True
        assert result is True

    def test_concrete_panel_cannot_be_instantiated_from_abc(self):
        """Test that ContentPanel cannot be instantiated directly."""
        with pytest.raises(TypeError):
            ContentPanel(self.panel_info)  # Should fail - abstract class
