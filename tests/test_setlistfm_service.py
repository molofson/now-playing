"""Tests for Setlist.fm enrichment service."""

import os
import sys
from unittest.mock import Mock

import pytest

# Add the project root to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "."))

from nowplaying.enrichment import EnrichmentRequest, SetlistFmService
from nowplaying.music_views import ContentContext


class TestSetlistFmService:
    """Test cases for Setlist.fm enrichment service."""

    @pytest.fixture
    def service(self):
        """Create Setlist.fm service instance."""
        return SetlistFmService()

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
        assert service.service_id == "setlistfm"
        assert service.service_name == "Setlist.fm"
        assert service.enabled is True
        assert service._rate_limit_delay == 0.5

    def test_logger_initialization(self, service):
        """Test that logger is properly initialized."""
        assert hasattr(service, "logger")
        assert service.logger is not None
        assert service.logger.name == "enrichment.setlistfm"

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
        assert "setlistfm" in result.last_updated

    def test_service_info(self, service):
        """Test get_service_info method."""
        info = service.get_service_info()

        assert info["service_id"] == "setlistfm"
        assert info["service_name"] == "Setlist.fm"
        assert info["enabled"] is True
        assert info["rate_limit_delay"] == 0.5

    def test_cache_key_generation(self, service, sample_request):
        """Test cache key generation."""
        cache_key = service.get_cache_key(sample_request)
        expected = "setlistfm:Radiohead:OK Computer:Paranoid Android"
        assert cache_key == expected

    def test_api_key_setting(self, service):
        """Test API key setting functionality."""
        test_key = "test_api_key_123"
        service.set_api_key(test_key)
        assert service._api_key == test_key

    @pytest.mark.asyncio
    async def test_enrich_without_api_key(self, service, sample_request):
        """Test enrichment without API key (should use mock data)."""
        # Ensure no API key is set
        service._api_key = None

        result = await service.enrich(sample_request)

        # Should still return data (mock data)
        assert result is not None
        assert "setlistfm" in result.last_updated

        # Should have mock tour dates for Radiohead
        assert result.tour_dates is not None
        assert len(result.tour_dates) > 0

    def test_mock_data_structure(self, service):
        """Test that mock data has correct structure."""
        mock_data = service._get_mock_data("radiohead")

        assert mock_data is not None
        assert "tour_dates" in mock_data
        assert "setlist" in mock_data

        # Check tour dates structure
        tour_dates = mock_data["tour_dates"]
        assert isinstance(tour_dates, list)
        assert len(tour_dates) > 0

        # Check first tour date has required fields
        first_date = tour_dates[0]
        assert "date" in first_date
        assert "venue" in first_date
        assert "city" in first_date
        assert "country" in first_date
        assert "type" in first_date
