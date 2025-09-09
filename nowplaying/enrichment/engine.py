"""
Enrichment engine for orchestrating multiple metadata enrichment services.

This module provides the central engine that manages and coordinates
all enrichment services, handles caching, and provides async/sync interfaces.
"""

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, List, Optional, Set

from .base import ContentContext, EnrichmentData, EnrichmentRequest, EnrichmentService
from .discogs_service import DiscogsService
from .lastfm_service import LastFmService
from .musicbrainz_service import MusicBrainzService


class EnrichmentEngine:
    """Manages metadata enrichment services and orchestrates enrichment."""

    def __init__(self, max_workers: int = 4):
        """Initialize enrichment engine with worker thread pool."""
        self.services: Dict[str, EnrichmentService] = {}
        self.enabled_services: Set[str] = set()
        self._max_workers = max_workers
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._enrichment_cache: Dict[str, EnrichmentData] = {}
        self._cache_timeout = 3600  # 1 hour cache timeout

        # Setup logger first
        self.logger = logging.getLogger("enrichment.engine")

        # Callbacks for enrichment completion
        self._enrichment_callbacks: List[Callable[[EnrichmentData, ContentContext], None]] = []

        # Register built-in services
        self._register_builtin_services()

    def _register_builtin_services(self):
        """Register built-in enrichment services."""
        self.register_service(MusicBrainzService())
        self.register_service(DiscogsService())
        self.register_service(LastFmService())

    def register_service(self, service: EnrichmentService) -> None:
        """Register an enrichment service."""
        self.services[service.service_id] = service
        if service.enabled:
            self.enabled_services.add(service.service_id)
        self.logger.info("Registered enrichment service: %s", service.service_name)

    def enable_service(self, service_id: str) -> bool:
        """Enable an enrichment service."""
        if service_id in self.services:
            self.services[service_id].enabled = True
            self.enabled_services.add(service_id)
            return True
        return False

    def disable_service(self, service_id: str) -> bool:
        """Disable an enrichment service."""
        if service_id in self.services:
            self.services[service_id].enabled = False
            self.enabled_services.discard(service_id)
            return True
        return False

    def add_enrichment_callback(self, callback: Callable[[EnrichmentData, ContentContext], None]) -> None:
        """Add callback for when enrichment completes."""
        self._enrichment_callbacks.append(callback)

    async def enrich_async(self, request: EnrichmentRequest) -> EnrichmentData:
        """Enrich metadata asynchronously using all enabled services."""
        # Check cache first
        cache_key = self._get_cache_key(request)
        cached = self._get_cached_enrichment(cache_key)
        if cached:
            return cached

        # Determine which services to use
        services_to_use = request.requested_services or self.enabled_services
        services_to_use = services_to_use.intersection(self.enabled_services)

        if not services_to_use:
            return EnrichmentData()

        # Run enrichment services concurrently
        tasks = []
        for service_id in services_to_use:
            service = self.services[service_id]
            if service.can_enrich(request):
                task = asyncio.create_task(service.enrich(request))
                tasks.append((service_id, task))

        # Collect results
        combined_enrichment = EnrichmentData()
        for service_id, task in tasks:
            try:
                result = await task
                if result:
                    combined_enrichment.merge(result)
            except Exception as e:
                self.logger.error("Service %s failed: %s", service_id, e)
                combined_enrichment.service_errors[service_id] = str(e)

        # Cache result
        self._cache_enrichment(cache_key, combined_enrichment)

        # Notify callbacks
        for callback in self._enrichment_callbacks:
            try:
                callback(combined_enrichment, request.context)
            except Exception as e:
                self.logger.error("Enrichment callback failed: %s", e)

        return combined_enrichment

    def enrich_sync(self, request: EnrichmentRequest) -> None:
        """Start enrichment in background thread."""

        def run_enrichment():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.enrich_async(request))
            finally:
                loop.close()

        self._executor.submit(run_enrichment)

    def _get_cache_key(self, request: EnrichmentRequest) -> str:
        """Generate cache key for request."""
        return f"{request.artist}:{request.album}:{request.title}"

    def _get_cached_enrichment(self, cache_key: str) -> Optional[EnrichmentData]:
        """Get cached enrichment if still valid."""
        if cache_key in self._enrichment_cache:
            enrichment = self._enrichment_cache[cache_key]
            # Check if cache is still valid (simplified - should check per service)
            oldest_update = min(enrichment.last_updated.values()) if enrichment.last_updated else 0
            if time.time() - oldest_update < self._cache_timeout:
                return enrichment
            else:
                # Cache expired
                del self._enrichment_cache[cache_key]
        return None

    def _cache_enrichment(self, cache_key: str, enrichment: EnrichmentData) -> None:
        """Cache enrichment data."""
        self._enrichment_cache[cache_key] = enrichment

        # Simple cache size management
        if len(self._enrichment_cache) > 1000:
            # Remove oldest entries (simplified LRU)
            oldest_key = min(
                self._enrichment_cache.keys(),
                key=lambda k: (
                    min(self._enrichment_cache[k].last_updated.values())
                    if self._enrichment_cache[k].last_updated
                    else 0
                ),
            )
            del self._enrichment_cache[oldest_key]

    def get_engine_status(self) -> Dict[str, Any]:
        """Get enrichment engine status."""
        return {
            "total_services": len(self.services),
            "enabled_services": list(self.enabled_services),
            "cache_size": len(self._enrichment_cache),
            "max_workers": self._max_workers,
            "services": {sid: service.get_service_info() for sid, service in self.services.items()},
        }

    def shutdown(self) -> None:
        """Shutdown the enrichment engine."""
        self._executor.shutdown(wait=True)


# Global enrichment engine
enrichment_engine = EnrichmentEngine()
