"""
Tests for Last.fm enrichment service.
"""

import os
import sys
from unittest.mock import Mock

import pytest

# Add the project root to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from nowplaying.enrichment import EnrichmentRequest, LastFmService  # noqa: E402
from nowplaying.music_views import ContentContext  # noqa: E402


class TestLastFmService:
    """Test cases for Last.fm enrichment service."""

    @pytest.fixture
    def service(self):
        """Create Last.fm service instance."""
        return LastFmService()

    @pytest.fixture
    def sample_request(self):
        """Create sample enrichment request."""
        context = Mock(spec=ContentContext)
        return EnrichmentRequest(
            artist="Radiohead",
            album="OK Computer",
            title="Paranoid Android",
            context=context,
        )

    def test_service_initialization(self, service):
        """Test service initialization."""
        assert service.service_id == "lastfm"
        assert service.service_name == "Last.fm"
        assert service.enabled is True
        assert service._rate_limit_delay == 0.5

    def test_logger_initialization(self, service):
        """Test that logger is properly initialized."""
        assert hasattr(service, "logger")
        assert service.logger is not None
        assert service.logger.name == "enrichment.lastfm"

    def test_logger_functionality(self, service, caplog):
        """Test that logger actually works."""
        import logging

        with caplog.at_level(logging.DEBUG):
            service.logger.debug("Test debug message")
            service.logger.info("Test info message")
            service.logger.warning("Test warning message")

        # Check that messages were logged
        assert "Test debug message" in caplog.text
        assert "Test info message" in caplog.text
        assert "Test warning message" in caplog.text

    def test_can_enrich(self, service, sample_request):
        """Test can_enrich method."""
        assert service.can_enrich(sample_request) is True

        # Test with disabled service
        service.enabled = False
        assert service.can_enrich(sample_request) is False

    @pytest.mark.asyncio
    async def test_enrich_disabled_service(self, service, sample_request):
        """Test enrichment with disabled service."""
        service.enabled = False
        result = await service.enrich(sample_request)
        assert result is None

    @pytest.mark.asyncio
    async def test_enrich_basic_functionality(self, service, sample_request):
        """Test basic enrichment functionality."""
        result = await service.enrich(sample_request)

        # Should return EnrichmentData (even if mock)
        assert result is not None
        assert hasattr(result, "last_updated")
        assert "lastfm" in result.last_updated

    def test_service_info(self, service):
        """Test get_service_info method."""
        info = service.get_service_info()

        assert info["service_id"] == "lastfm"
        assert info["service_name"] == "Last.fm"
        assert info["enabled"] is True
        assert info["rate_limit_delay"] == 0.5

    def test_cache_key_generation(self, service, sample_request):
        """Test cache key generation."""
        cache_key = service.get_cache_key(sample_request)
        expected = "lastfm:Radiohead:OK Computer:Paranoid Android"
        assert cache_key == expected
