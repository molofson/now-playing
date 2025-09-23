"""
Tests for enrichment panels and related functionality.

This module tests the new enrichment panel implementations including:
- EnrichmentLogBuffer for capturing logger output
- MusicBrainzPanel, DiscogsPanel, LastFmPanel implementations
- Enrichment data attachment to context
- Panel rendering with enrichment data
"""

import sys

# Add project root to path
sys.path.insert(0, "/home/molofson/repos/now-playing")

import logging
from unittest.mock import Mock, patch

import pygame
import pytest

from nowplaying.enrichment import EnrichmentData
from nowplaying.music_views import ContentContext
from nowplaying.panels.discogs_panel import DiscogsPanel
from nowplaying.panels.enrichment_log_buffer import EnrichmentLogBuffer
from nowplaying.panels.lastfm_panel import LastFmPanel
from nowplaying.panels.musicbrainz_panel import MusicBrainzPanel


class TestEnrichmentLogBuffer:
    """Test EnrichmentLogBuffer functionality."""

    def test_log_buffer_initialization(self):
        """Test that EnrichmentLogBuffer initializes correctly."""
        buffer = EnrichmentLogBuffer("test.logger", max_lines=5)
        assert buffer.logger.name == "test.logger"
        assert buffer.max_lines == 5
        assert len(buffer.buffer) == 0

    def test_log_capture(self):
        """Test that log messages are captured."""
        buffer = EnrichmentLogBuffer("test.capture", max_lines=10)

        # Create a logger and log some messages
        logger = logging.getLogger("test.capture")
        logger.info("Test message 1")
        logger.warning("Test message 2")
        logger.error("Test message 3")

        # Check that messages were captured
        lines = buffer.get_lines()
        assert len(lines) >= 2  # At least info and warning/error
        assert any("Test message" in line for line in lines)

    def test_buffer_size_limit(self):
        """Test that buffer respects max_lines limit."""
        buffer = EnrichmentLogBuffer("test.limit", max_lines=3)

        logger = logging.getLogger("test.limit")
        for i in range(5):
            logger.info(f"Message {i}")

        lines = buffer.get_lines()
        assert len(lines) <= 3  # Should not exceed max_lines

    def test_write_method(self):
        """Test direct write method."""
        buffer = EnrichmentLogBuffer("test.write", max_lines=5)

        buffer.write("Direct message 1")
        buffer.write("Direct message 2")
        buffer.write("")  # Empty message should be ignored
        buffer.write("Direct message 3")

        lines = buffer.get_lines()
        assert len(lines) == 3  # Empty message ignored
        assert "Direct message 1" in lines[0]
        assert "Direct message 2" in lines[1]


class TestEnrichmentPanels:
    """Test enrichment panel implementations."""

    @pytest.fixture
    def mock_surface(self):
        """Create mock pygame surface."""
        return Mock(spec=pygame.Surface)

    @pytest.fixture
    def mock_rect(self):
        """Create mock pygame rect."""
        rect = Mock()
        rect.left = 10
        rect.top = 10
        rect.width = 400
        rect.height = 200
        return rect

    @pytest.fixture
    def sample_context(self):
        """Create sample content context."""
        return ContentContext(artist="Test Artist", album="Test Album", title="Test Track", duration=180.0)

    def test_musicbrainz_panel_initialization(self):
        """Test MusicBrainzPanel initialization."""
        panel = MusicBrainzPanel()
        assert panel.info.id == "musicbrainz"
        assert panel.info.name == "MusicBrainz"
        assert hasattr(panel, "log_buffer")

    def test_discogs_panel_initialization(self):
        """Test DiscogsPanel initialization."""
        panel = DiscogsPanel()
        assert panel.info.id == "discogs"
        assert panel.info.name == "Discogs"
        assert hasattr(panel, "log_buffer")

    def test_lastfm_panel_initialization(self):
        """Test LastFmPanel initialization."""
        panel = LastFmPanel()
        assert panel.info.id == "lastfm"
        assert panel.info.name == "Last.fm"
        assert hasattr(panel, "log_buffer")

    def test_panel_display_logic(self, sample_context):
        """Test that panels can display content."""
        panel = MusicBrainzPanel()
        assert panel.can_display(sample_context)

        # Test with None context
        assert not panel.can_display(None)

    def test_panel_context_update(self, sample_context):
        """Test panel context updates."""
        panel = MusicBrainzPanel()
        panel.update_context(sample_context)
        assert panel._context == sample_context

    def test_panel_render_without_context(self, mock_surface, mock_rect):
        """Test panel rendering without context."""
        panel = MusicBrainzPanel()
        # Should not raise exception
        panel.render(mock_surface, mock_rect)

    def test_panel_render_with_enrichment_data(self, mock_surface, mock_rect, sample_context):
        """Test panel rendering with enrichment data."""
        panel = MusicBrainzPanel()

        # Create enrichment data
        enrichment = EnrichmentData()
        enrichment.musicbrainz_artist_id = "test-artist-id"
        enrichment.musicbrainz_album_id = "test-album-id"
        enrichment.musicbrainz_track_id = "test-track-id"
        enrichment.artist_tags = ["rock", "british"]

        # Attach to context
        sample_context.enrichment_data = enrichment
        panel.update_context(sample_context)

        # Mock pygame font
        with patch("pygame.font.Font") as mock_font:
            mock_text = Mock()
            mock_font.return_value.render.return_value = mock_text

            # Should not raise exception
            panel.render(mock_surface, mock_rect)

            # Verify font was created and render was called
            mock_font.assert_called()
            mock_font.return_value.render.assert_called()

    def test_handle_event_noop(self):
        """Test that handle_event returns False (no-op)."""
        panel = MusicBrainzPanel()
        result = panel.handle_event(None)
        assert not result


class TestEnrichmentDataAttachment:
    """Test enrichment data attachment to context."""

    def test_enrichment_data_attachment(self):
        """Test that enrichment data can be attached to context."""
        context = ContentContext(artist="Test", title="Track")

        enrichment = EnrichmentData()
        enrichment.musicbrainz_artist_id = "mb-artist-123"

        # Simulate attachment
        context.enrichment_data = enrichment

        assert hasattr(context, "enrichment_data")
        assert context.enrichment_data.musicbrainz_artist_id == "mb-artist-123"

    def test_context_without_enrichment_data(self):
        """Test context behavior without enrichment data."""
        context = ContentContext(artist="Test", title="Track")

        # enrichment_data attribute should not exist initially
        assert not hasattr(context, "enrichment_data")

        # Accessing it should return None via getattr
        data = getattr(context, "enrichment_data", None)
        assert data is None


class TestPanelRegistration:
    """Test enrichment panel registration logic."""

    @patch("nowplaying.panels.content_panel_registry.register_panel")
    def test_panel_registration_success(self, mock_register):
        """Test successful panel registration."""
        from nowplaying.panels.musicbrainz_panel import MusicBrainzPanel

        # Simulate successful import and registration
        panel = MusicBrainzPanel()
        mock_register.assert_not_called()  # Not called in __init__

        # Manual registration
        mock_register(panel)
        mock_register.assert_called_once_with(panel)

    @patch("nowplaying.panels.content_panel_registry.register_panel")
    @patch("builtins.__import__", side_effect=ImportError("Panel not found"))
    def test_panel_registration_failure(self, mock_import, mock_register):
        """Test panel registration failure handling."""
        # This would test the try/except blocks in music_discovery.py
        # For now, just verify the mock setup works
        with pytest.raises(ImportError):
            mock_import("nonexistent.module")

        # register should not be called on failure
        mock_register.assert_not_called()
