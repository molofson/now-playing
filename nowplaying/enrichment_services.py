"""
Metadata enrichment services for extending core music metadata.

This module provides a pluggable system for enriching core metadata with
information from external services like MusicBrainz, Discogs, Last.fm, etc.
Enrichment happens asynchronously and provides sidecar data that panels can use.
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set

from .music_views import ContentContext


@dataclass
class EnrichmentData:
    """Container for enriched metadata from external services."""

    # Core identifiers (for cross-service linking)
    musicbrainz_artist_id: Optional[str] = None
    musicbrainz_album_id: Optional[str] = None
    musicbrainz_track_id: Optional[str] = None
    discogs_artist_id: Optional[str] = None
    discogs_release_id: Optional[str] = None
    spotify_artist_id: Optional[str] = None
    spotify_album_id: Optional[str] = None

    # Extended metadata
    artist_bio: Optional[str] = None
    artist_tags: List[str] = field(default_factory=list)
    similar_artists: List[Dict[str, Any]] = field(default_factory=list)
    album_reviews: List[Dict[str, Any]] = field(default_factory=list)
    album_credits: List[Dict[str, Any]] = field(default_factory=list)

    # Discovery data
    tour_dates: List[Dict[str, Any]] = field(default_factory=list)
    recent_releases: List[Dict[str, Any]] = field(default_factory=list)
    artist_discography: List[Dict[str, Any]] = field(default_factory=list)

    # Social/community data
    scrobble_count: Optional[int] = None
    popularity_score: Optional[float] = None
    user_tags: List[str] = field(default_factory=list)

    # Service metadata
    last_updated: Dict[str, float] = field(default_factory=dict)  # service_name -> timestamp
    service_errors: Dict[str, str] = field(default_factory=dict)  # service_name -> error

    def merge(self, other: "EnrichmentData") -> "EnrichmentData":
        """Merge another enrichment data object into this one."""
        # This would implement smart merging logic
        # For now, simple field updates
        for field_name, _field_def in self.__dataclass_fields__.items():
            other_value = getattr(other, field_name, None)
            if other_value:
                if isinstance(other_value, list):
                    current_list = getattr(self, field_name, [])
                    # Merge lists, avoiding duplicates
                    if current_list:
                        merged = current_list + [item for item in other_value if item not in current_list]
                        setattr(self, field_name, merged)
                    else:
                        setattr(self, field_name, other_value)
                elif isinstance(other_value, dict):
                    current_dict = getattr(self, field_name, {})
                    merged = {**current_dict, **other_value}
                    setattr(self, field_name, merged)
                else:
                    # Simple field update
                    setattr(self, field_name, other_value)

        return self


@dataclass
class EnrichmentRequest:
    """Request for metadata enrichment."""

    artist: str
    album: str
    title: str
    context: ContentContext
    requested_services: Set[str] = field(default_factory=set)  # Empty = all enabled
    priority: int = 0  # Higher = more urgent
    timestamp: float = field(default_factory=time.time)


class EnrichmentService(ABC):
    """Base class for metadata enrichment services."""

    def __init__(self, service_id: str, service_name: str, enabled: bool = True):
        self.service_id = service_id
        self.service_name = service_name
        self.enabled = enabled
        self.logger = logging.getLogger(f"enrichment.{service_id}")
        self._rate_limit_delay = 1.0  # Seconds between requests
        self._last_request_time = 0.0

    @abstractmethod
    async def enrich(self, _request: EnrichmentRequest) -> Optional[EnrichmentData]:
        """Enrich metadata with this service's data."""
        pass

    def can_enrich(self, request: EnrichmentRequest) -> bool:
        """Check if this service can enrich the given request."""
        return self.enabled and bool(request.artist or request.album or request.title)

    def get_cache_key(self, request: EnrichmentRequest) -> str:
        """Generate cache key for this request."""
        return f"{self.service_id}:{request.artist}:{request.album}:{request.title}"

    async def _rate_limit(self) -> None:
        """Apply rate limiting."""
        now = time.time()
        time_since_last = now - self._last_request_time
        if time_since_last < self._rate_limit_delay:
            await asyncio.sleep(self._rate_limit_delay - time_since_last)
        self._last_request_time = time.time()

    def get_service_info(self) -> Dict[str, Any]:
        """Get service information for debugging."""
        return {
            "service_id": self.service_id,
            "service_name": self.service_name,
            "enabled": self.enabled,
            "rate_limit_delay": self._rate_limit_delay,
        }


class MusicBrainzService(EnrichmentService):
    """MusicBrainz metadata enrichment service."""

    def __init__(self, enabled: bool = True):
        super().__init__("musicbrainz", "MusicBrainz", enabled)
        self._rate_limit_delay = 1.0  # MusicBrainz rate limit

    async def enrich(self, request: EnrichmentRequest) -> Optional[EnrichmentData]:
        """Enrich with MusicBrainz data."""
        if not self.can_enrich(request):
            return None

        await self._rate_limit()

        try:
            # This would make actual MusicBrainz API calls
            # For now, return mock data
            self.logger.debug("Enriching with MusicBrainz: %s - %s", request.artist, request.title)

            enrichment = EnrichmentData()
            enrichment.musicbrainz_artist_id = f"mb-artist-{hash(request.artist) % 10000}"
            enrichment.musicbrainz_album_id = f"mb-album-{hash(request.album) % 10000}"
            enrichment.musicbrainz_track_id = f"mb-track-{hash(request.title) % 10000}"
            enrichment.last_updated["musicbrainz"] = time.time()

            # Mock album credits
            enrichment.album_credits = [
                {"role": "vocals", "artist": request.artist},
                {"role": "producer", "artist": "Mock Producer"},
            ]

            return enrichment

        except Exception as e:
            self.logger.error("MusicBrainz enrichment failed: %s", e)
            enrichment = EnrichmentData()
            enrichment.service_errors["musicbrainz"] = str(e)
            return enrichment


class DiscogsService(EnrichmentService):
    """Discogs metadata enrichment service."""

    def __init__(self, enabled: bool = True):
        super().__init__("discogs", "Discogs", enabled)
        self._rate_limit_delay = 1.5  # Discogs rate limit

    async def enrich(self, request: EnrichmentRequest) -> Optional[EnrichmentData]:
        """Enrich with Discogs data."""
        if not self.can_enrich(request):
            return None

        await self._rate_limit()

        try:
            self.logger.debug("Enriching with Discogs: %s - %s", request.artist, request.album)

            enrichment = EnrichmentData()
            enrichment.discogs_artist_id = f"discogs-artist-{hash(request.artist) % 10000}"
            enrichment.discogs_release_id = f"discogs-release-{hash(request.album) % 10000}"
            enrichment.last_updated["discogs"] = time.time()

            # Mock artist discography
            enrichment.artist_discography = [
                {"title": f"{request.album} (Original)", "year": "2020", "format": "LP"},
                {"title": "Previous Album", "year": "2018", "format": "CD"},
            ]

            return enrichment

        except Exception as e:
            self.logger.error("Discogs enrichment failed: %s", e)
            enrichment = EnrichmentData()
            enrichment.service_errors["discogs"] = str(e)
            return enrichment


class LastFmService(EnrichmentService):
    """Last.fm metadata enrichment service."""

    def __init__(self, enabled: bool = True):
        super().__init__("lastfm", "Last.fm", enabled)
        self._rate_limit_delay = 0.5  # Last.fm rate limit

    async def enrich(self, request: EnrichmentRequest) -> Optional[EnrichmentData]:
        """Enrich with Last.fm data."""
        if not self.can_enrich(request):
            return None

        await self._rate_limit()

        try:
            self.logger.debug("Enriching with Last.fm: %s", request.artist)

            enrichment = EnrichmentData()
            enrichment.last_updated["lastfm"] = time.time()

            # Mock data
            enrichment.artist_bio = f"Mock biography for {request.artist}. This would be fetched from Last.fm API."
            enrichment.artist_tags = ["rock", "alternative", "indie"]
            enrichment.similar_artists = [
                {"name": "Similar Artist 1", "match": 0.8},
                {"name": "Similar Artist 2", "match": 0.7},
            ]
            enrichment.scrobble_count = hash(request.artist) % 1000000

            return enrichment

        except Exception as e:
            self.logger.error("Last.fm enrichment failed: %s", e)
            enrichment = EnrichmentData()
            enrichment.service_errors["lastfm"] = str(e)
            return enrichment


class EnrichmentEngine:
    """Manages metadata enrichment services and orchestrates enrichment."""

    def __init__(self, max_workers: int = 4):
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
