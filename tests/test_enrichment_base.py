"""
Tests for base EnrichmentService class.
"""

import asyncio
import os
import sys
import time
from unittest.mock import Mock

import pytest

# Add the project root to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from nowplaying.enrichment import EnrichmentData, EnrichmentRequest, EnrichmentService  # noqa: E402
from nowplaying.music_views import ContentContext  # noqa: E402


class ConcreteEnrichmentService(EnrichmentService):
    """Concrete implementation for testing the abstract base class."""

    def __init__(self, service_id="test", service_name="Test Service"):
        """Initialize concrete test service."""
        super().__init__(service_id, service_name)
        self.enrich_called = False

    async def enrich(self, request):
        """Simple test implementation."""
        self.enrich_called = True
        if not self.can_enrich(request):
            return None

        data = EnrichmentData()
        data.last_updated[self.service_id] = time.time()
        return data


class TestEnrichmentServiceBase:
    """Test cases for base EnrichmentService class."""

    @pytest.fixture
    def service(self):
        """Create concrete service instance."""
        return ConcreteEnrichmentService("base_test", "Base Test Service")

    @pytest.fixture
    def sample_request(self):
        """Create sample enrichment request."""
        context = Mock(spec=ContentContext)
        return EnrichmentRequest(artist="Test Artist", album="Test Album", title="Test Song", context=context)

    def test_service_initialization(self, service):
        """Test base service initialization."""
        assert service.service_id == "base_test"
        assert service.service_name == "Base Test Service"
        assert service.enabled is True
        assert service._rate_limit_delay == 1.0
        assert service._last_request_time == 0.0

    def test_logger_initialization(self, service):
        """Test that logger is properly initialized in base class."""
        assert hasattr(service, "logger")
        assert service.logger is not None
        assert service.logger.name == "enrichment.base_test"

    def test_logger_functionality(self, service, caplog):
        """Test that logger actually works."""
        import logging

        with caplog.at_level(logging.DEBUG):
            service.logger.debug("Test debug message")
            service.logger.info("Test info message")
            service.logger.warning("Test warning message")
            service.logger.error("Test error message")

        # Check that messages were logged
        assert "Test debug message" in caplog.text
        assert "Test info message" in caplog.text
        assert "Test warning message" in caplog.text
        assert "Test error message" in caplog.text

    def test_can_enrich_enabled(self, service, sample_request):
        """Test can_enrich with enabled service."""
        assert service.enabled is True
        assert service.can_enrich(sample_request) is True

    def test_can_enrich_disabled(self, service, sample_request):
        """Test can_enrich with disabled service."""
        service.enabled = False
        assert service.can_enrich(sample_request) is False

    def test_can_enrich_empty_request(self, service):
        """Test can_enrich with empty request."""
        context = Mock(spec=ContentContext)
        empty_request = EnrichmentRequest(artist="", album="", title="", context=context)
        assert service.can_enrich(empty_request) is False

    def test_can_enrich_partial_request(self, service):
        """Test can_enrich with partial request data."""
        context = Mock(spec=ContentContext)

        # Only artist
        artist_only = EnrichmentRequest(artist="Artist", album="", title="", context=context)
        assert service.can_enrich(artist_only) is True

        # Only album
        album_only = EnrichmentRequest(artist="", album="Album", title="", context=context)
        assert service.can_enrich(album_only) is True

        # Only title
        title_only = EnrichmentRequest(artist="", album="", title="Title", context=context)
        assert service.can_enrich(title_only) is True

    def test_cache_key_generation(self, service, sample_request):
        """Test cache key generation."""
        cache_key = service.get_cache_key(sample_request)
        expected = "base_test:Test Artist:Test Album:Test Song"
        assert cache_key == expected

    def test_cache_key_with_special_chars(self, service):
        """Test cache key generation with special characters."""
        context = Mock(spec=ContentContext)
        request = EnrichmentRequest(artist="Sigur Rós", album="Ágætis byrjun", title="Svefn-g-englar", context=context)
        cache_key = service.get_cache_key(request)
        expected = "base_test:Sigur Rós:Ágætis byrjun:Svefn-g-englar"
        assert cache_key == expected

    @pytest.mark.asyncio
    async def test_rate_limiting(self, service):
        """Test rate limiting functionality."""
        # Set a short delay for testing
        service._rate_limit_delay = 0.1

        start_time = time.time()

        # First call should not delay
        await service._rate_limit()

        # Second call should delay
        await service._rate_limit()
        second_call_time = time.time()

        # The second call should take at least the rate limit delay
        total_time = second_call_time - start_time
        assert total_time >= service._rate_limit_delay

    def test_service_info(self, service):
        """Test get_service_info method."""
        info = service.get_service_info()

        assert info["service_id"] == "base_test"
        assert info["service_name"] == "Base Test Service"
        assert info["enabled"] is True
        assert info["rate_limit_delay"] == 1.0

    @pytest.mark.asyncio
    async def test_enrich_implementation(self, service, sample_request):
        """Test that concrete implementation works."""
        result = await service.enrich(sample_request)

        assert service.enrich_called is True
        assert result is not None
        assert isinstance(result, EnrichmentData)
        assert "base_test" in result.last_updated

    @pytest.mark.asyncio
    async def test_enrich_disabled_service(self, service, sample_request):
        """Test enrichment with disabled service."""
        service.enabled = False
        result = await service.enrich(sample_request)

        assert service.enrich_called is True  # Method is called but returns None
        assert result is None

    def test_logger_name_matches_service_id(self):
        """Test that logger name always matches service_id."""
        test_cases = [
            ("musicbrainz", "MusicBrainz"),
            ("lastfm", "Last.fm"),
            ("discogs", "Discogs"),
            ("custom_service", "Custom Service"),
            ("service-with-dashes", "Service With Dashes"),
        ]

        for service_id, service_name in test_cases:
            service = ConcreteEnrichmentService(service_id, service_name)
            expected_logger_name = f"enrichment.{service_id}"
            assert service.logger.name == expected_logger_name
