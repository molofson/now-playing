"""
Spotify enrichment service (skeleton).

This file provides a minimal, safe skeleton implementation for Spotify enrichment.
It is intentionally offline-friendly and will only attempt network calls when
credentials are provided and the implementation is expanded.
"""

import time
from typing import Optional

from .base import EnrichmentData, EnrichmentRequest, EnrichmentService


class SpotifyService(EnrichmentService):
    """Skeleton Spotify enrichment service.

    This class is a placeholder implementation intended to be expanded with
    real Spotify API calls once credentials and an HTTP client are integrated.
    """

    def __init__(self):
        """Create a new SpotifyService instance.

        The service is created enabled by default; callers may disable it by
        not setting credentials.
        """
        super().__init__("spotify", "Spotify")
        self._rate_limit_delay = 0.5
        self._client_id = None
        self._client_secret = None

    def set_credentials(self, client_id: str, client_secret: str) -> None:
        """Store client credentials for later use by the implementation."""
        self._client_id = client_id
        self._client_secret = client_secret

    def can_enrich(self, request: EnrichmentRequest) -> bool:
        """Return True when the service has credentials and the request has basic info."""
        return bool(self._client_id and self._client_secret and (request.artist or request.title))

    async def enrich(self, request: EnrichmentRequest) -> Optional[EnrichmentData]:
        """Perform enrichment (skeleton)."""
        await self._rate_limit()

        enrichment = EnrichmentData()
        now = time.time()
        enrichment.last_updated["spotify"] = now

        if request.artist:
            enrichment.spotify_artist_id = f"spotify:artist:placeholder:{hash(request.artist) & 0xFFFF}"  # type: ignore[arg-type]
        if request.album:
            enrichment.spotify_album_id = f"spotify:album:placeholder:{hash(request.album) & 0xFFFF}"  # type: ignore[arg-type]

        enrichment.popularity_score = 0.0

        return enrichment
