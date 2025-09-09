"""
Last.fm metadata enrichment service.

This module provides integration with the Last.fm API for retrieving
artist biographies, tags, similar artists, and scrobble data.
"""

import time
from typing import Optional

from .base import EnrichmentData, EnrichmentRequest, EnrichmentService


class LastFmService(EnrichmentService):
    """Last.fm metadata enrichment service."""

    def __init__(self):
        """Initialize Last.fm service."""
        super().__init__("lastfm", "Last.fm")
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
