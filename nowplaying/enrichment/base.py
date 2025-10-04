"""
Base classes for the enrichment services system.

This module provides the core data structures and abstract base class
for implementing metadata enrichment services.
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from ..music_views import ContentContext


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
    song_lyrics: Optional[str] = None
    song_annotations: List[Dict[str, Any]] = field(
        default_factory=list
    )  # [{'text': str, 'range': str, 'explanation': str}]

    # Discovery data
    tour_dates: List[Dict[str, Any]] = field(default_factory=list)
    recent_releases: List[Dict[str, Any]] = field(default_factory=list)
    artist_discography: List[Dict[str, Any]] = field(default_factory=list)

    # Social/community data
    scrobble_count: Optional[int] = None
    popularity_score: Optional[float] = None
    user_tags: List[str] = field(default_factory=list)

    # Image URLs from external services
    cover_art_urls: List[Dict[str, Any]] = field(default_factory=list)  # [{'url': str, 'size': str, 'type': str}]
    artist_images: List[Dict[str, Any]] = field(default_factory=list)  # [{'url': str, 'type': str}]

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

    def __init__(self, service_id: str, service_name: str):
        """Initialize enrichment service with ID and name."""
        self.service_id = service_id
        self.service_name = service_name
        self.enabled = True
        self._rate_limit_delay = 1.0
        self._last_request_time = 0.0
        self.logger = logging.getLogger(f"enrichment.{service_id}")

    @abstractmethod
    async def enrich(
        self, request: EnrichmentRequest  # noqa: U100 - abstract method, used in subclasses
    ) -> Optional[EnrichmentData]:
        """Enrich metadata. Override in subclasses."""
        return EnrichmentData()

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
