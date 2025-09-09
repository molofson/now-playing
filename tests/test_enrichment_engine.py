"""
Tests for EnrichmentEngine.
"""

import asyncio
import os
import sys
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Add the project root to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from nowplaying.enrichment import (  # noqa: E402
    EnrichmentData,
    EnrichmentEngine,
    EnrichmentRequest,
    EnrichmentService,
)
from nowplaying.music_views import ContentContext  # noqa: E402


class MockEnrichmentService(EnrichmentService):
    """Mock enrichment service for testing."""

    def __init__(self, service_id="mock", service_name="Mock Service", enabled=True):
        """Initialize mock service."""
        super().__init__(service_id, service_name)
        self.enabled = enabled
        self.enrich_called = False
        self.mock_data = EnrichmentData()

    async def enrich(self, request):  # noqa: U100
        """Mock enrichment method."""
        self.enrich_called = True
        if not self.enabled:
            return None
        self.mock_data.last_updated[self.service_id] = 12345.0
        return self.mock_data


class TestEnrichmentEngine:
    """Test cases for EnrichmentEngine."""

    @pytest.fixture
    def engine(self):
        """Create EnrichmentEngine instance."""
        # Create engine without auto-registering built-in services
        with patch.object(EnrichmentEngine, "_register_builtin_services"):
            return EnrichmentEngine(max_workers=2)

    @pytest.fixture
    def sample_request(self):
        """Create sample enrichment request."""
        context = Mock(spec=ContentContext)
        return EnrichmentRequest(artist="Test Artist", album="Test Album", title="Test Song", context=context)

    def test_engine_initialization(self, engine):
        """Test engine initialization."""
        assert engine.services == {}
        assert engine.enabled_services == set()
        assert engine._max_workers == 2
        assert engine._cache_timeout == 3600

    def test_logger_initialization(self, engine):
        """Test that logger is properly initialized."""
        assert hasattr(engine, "logger")
        assert engine.logger is not None
        assert engine.logger.name == "enrichment.engine"

    def test_logger_functionality(self, engine, caplog):
        """Test that logger actually works."""
        import logging

        with caplog.at_level(logging.DEBUG):
            engine.logger.debug("Test debug message")
            engine.logger.info("Test info message")
            engine.logger.warning("Test warning message")

        # Check that messages were logged
        assert "Test debug message" in caplog.text
        assert "Test info message" in caplog.text
        assert "Test warning message" in caplog.text

    def test_register_service(self, engine):
        """Test service registration."""
        mock_service = MockEnrichmentService("test_service", "Test Service")

        engine.register_service(mock_service)

        assert "test_service" in engine.services
        assert engine.services["test_service"] == mock_service
        assert "test_service" in engine.enabled_services

    def test_register_disabled_service(self, engine):
        """Test registration of disabled service."""
        mock_service = MockEnrichmentService("disabled_service", "Disabled Service", enabled=False)

        engine.register_service(mock_service)

        assert "disabled_service" in engine.services
        assert "disabled_service" not in engine.enabled_services

    def test_disable_service(self, engine):
        """Test disabling a service."""
        mock_service = MockEnrichmentService("test_service", "Test Service")
        engine.register_service(mock_service)

        assert "test_service" in engine.enabled_services

        success = engine.disable_service("test_service")

        assert success is True
        assert "test_service" not in engine.enabled_services
        assert mock_service.enabled is False

    def test_disable_nonexistent_service(self, engine):
        """Test disabling a service that doesn't exist."""
        success = engine.disable_service("nonexistent")
        assert success is False

    def test_enable_service(self, engine):
        """Test enabling a service."""
        mock_service = MockEnrichmentService("test_service", "Test Service", enabled=False)
        engine.register_service(mock_service)

        assert "test_service" not in engine.enabled_services

        success = engine.enable_service("test_service")

        assert success is True
        assert "test_service" in engine.enabled_services
        assert mock_service.enabled is True

    def test_get_enabled_services_info(self, engine):
        """Test getting enabled services information."""
        service1 = MockEnrichmentService("service1", "Service 1", enabled=True)
        service2 = MockEnrichmentService("service2", "Service 2", enabled=False)
        service3 = MockEnrichmentService("service3", "Service 3", enabled=True)

        engine.register_service(service1)
        engine.register_service(service2)
        engine.register_service(service3)

        # Check enabled services set
        assert "service1" in engine.enabled_services
        assert "service3" in engine.enabled_services
        assert "service2" not in engine.enabled_services

    def test_get_engine_status(self, engine):
        """Test getting engine status information."""
        service1 = MockEnrichmentService("service1", "Service 1", enabled=True)
        service2 = MockEnrichmentService("service2", "Service 2", enabled=False)

        engine.register_service(service1)
        engine.register_service(service2)

        status = engine.get_engine_status()

        assert "services" in status
        assert "enabled_services" in status
        assert "cache_size" in status
        assert len(status["services"]) == 2
        assert len(status["enabled_services"]) == 1

    @pytest.mark.asyncio
    async def test_enrich_single_service(self, engine, sample_request):
        """Test enrichment with single service."""
        mock_service = MockEnrichmentService("test_service", "Test Service")
        engine.register_service(mock_service)

        result = await engine.enrich_async(sample_request)

        assert result is not None
        assert mock_service.enrich_called is True
        assert "test_service" in result.last_updated

    @pytest.mark.asyncio
    async def test_enrich_multiple_services(self, engine, sample_request):
        """Test enrichment with multiple services."""
        service1 = MockEnrichmentService("service1", "Service 1")
        service2 = MockEnrichmentService("service2", "Service 2")

        engine.register_service(service1)
        engine.register_service(service2)

        result = await engine.enrich_async(sample_request)

        assert result is not None
        assert service1.enrich_called is True
        assert service2.enrich_called is True
        assert "service1" in result.last_updated
        assert "service2" in result.last_updated

    @pytest.mark.asyncio
    async def test_enrich_with_disabled_service(self, engine, sample_request):
        """Test enrichment with disabled service."""
        enabled_service = MockEnrichmentService("enabled", "Enabled Service", enabled=True)
        disabled_service = MockEnrichmentService("disabled", "Disabled Service", enabled=False)

        engine.register_service(enabled_service)
        engine.register_service(disabled_service)

        result = await engine.enrich_async(sample_request)

        assert result is not None
        assert enabled_service.enrich_called is True
        assert disabled_service.enrich_called is False
        assert "enabled" in result.last_updated
        assert "disabled" not in result.last_updated

    def test_add_enrichment_callback(self, engine):
        """Test adding enrichment callbacks."""

        def test_callback(data, context):  # noqa: U100
            pass

        engine.add_enrichment_callback(test_callback)

        # The callbacks are stored but triggered internally during enrichment
        # We can test that the callback was added to the list
        assert len(engine._enrichment_callbacks) == 1
        assert engine._enrichment_callbacks[0] == test_callback
