"""
Tests for Discogs enrichment service.
"""

import os
import sys
from unittest.mock import Mock

import pytest

# Add the project root to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from nowplaying.enrichment import DiscogsService, EnrichmentRequest  # noqa: E402
from nowplaying.music_views import ContentContext  # noqa: E402


class TestDiscogsService:
    """Test cases for Discogs enrichment service."""

    @pytest.fixture
    def service(self):
        """Create Discogs service instance."""
        return DiscogsService()

    @pytest.fixture
    def sample_request(self):
        """Create sample enrichment request."""
        context = Mock(spec=ContentContext)
        return EnrichmentRequest(
            artist="Pink Floyd",
            album="The Dark Side of the Moon",
            title="Money",
            context=context,
        )

    def test_service_initialization(self, service):
        """Test service initialization."""
        assert service.service_id == "discogs"
        assert service.service_name == "Discogs"
        assert service.enabled is True
        assert service._rate_limit_delay == 1.5

    def test_logger_initialization(self, service):
        """Test that logger is properly initialized."""
        assert hasattr(service, "logger")
        assert service.logger is not None
        assert service.logger.name == "enrichment.discogs"

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
        assert "discogs" in result.last_updated

    def test_service_info(self, service):
        """Test get_service_info method."""
        info = service.get_service_info()

        assert info["service_id"] == "discogs"
        assert info["service_name"] == "Discogs"
        assert info["enabled"] is True
        assert info["rate_limit_delay"] == 1.5

    def test_cache_key_generation(self, service, sample_request):
        """Test cache key generation."""
        cache_key = service.get_cache_key(sample_request)
        expected = "discogs:Pink Floyd:The Dark Side of the Moon:Money"
        assert cache_key == expected
