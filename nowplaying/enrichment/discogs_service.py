"""
Discogs metadata enrichment service.

This module provides integration with the Discogs database for retrieving
release information, artist discographies, and marketplace data.
"""

import asyncio
import json
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Optional

from .base import EnrichmentData, EnrichmentRequest, EnrichmentService


class DiscogsService(EnrichmentService):
    """Discogs metadata enrichment service."""

    def __init__(self):
        """Initialize Discogs service."""
        super().__init__("discogs", "Discogs")
        self._rate_limit_delay = 1.5  # Discogs rate limit is more restrictive
        self._base_url = "https://api.discogs.com"
        self._user_agent = "NowPlayingApp/1.0"

    def _search_artist_sync(self, artist_name: str) -> Optional[Dict[str, Any]]:
        """Synchronous version of artist search for thread pool execution."""
        try:
            query = urllib.parse.quote_plus(artist_name)
            url = f"{self._base_url}/database/search?q={query}&type=artist&per_page=1"

            req = urllib.request.Request(
                url, headers={"User-Agent": self._user_agent, "Accept": "application/json"}
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))

                if data.get("results") and len(data["results"]) > 0:
                    artist = data["results"][0]
                    return {
                        "id": artist.get("id"),
                        "title": artist.get("title"),
                        "uri": artist.get("uri"),
                        "resource_url": artist.get("resource_url"),
                        "thumb": artist.get("thumb"),
                    }

        except Exception as e:
            self.logger.warning(f"Discogs artist search failed for '{artist_name}': {e}")

        return None

    def _search_release_sync(self, artist: str, album: str) -> Optional[Dict[str, Any]]:
        """Synchronous version of release search for thread pool execution."""
        try:
            query = urllib.parse.quote_plus(f"{artist} {album}")
            url = f"{self._base_url}/database/search?q={query}&type=release&per_page=1"

            req = urllib.request.Request(
                url, headers={"User-Agent": self._user_agent, "Accept": "application/json"}
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))

                if data.get("results") and len(data["results"]) > 0:
                    release = data["results"][0]
                    return {
                        "id": release.get("id"),
                        "title": release.get("title"),
                        "year": release.get("year"),
                        "format": release.get("format", []),
                        "label": release.get("label", []),
                        "country": release.get("country"),
                        "uri": release.get("uri"),
                        "resource_url": release.get("resource_url"),
                        "thumb": release.get("thumb"),
                    }

        except Exception as e:
            self.logger.warning(f"Discogs release search failed for '{artist} - {album}': {e}")

        return None

    async def _search_artist(self, artist_name: str) -> Optional[Dict[str, Any]]:
        """Search for artist asynchronously."""
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            return await loop.run_in_executor(executor, self._search_artist_sync, artist_name)

    async def _search_release(self, artist: str, album: str) -> Optional[Dict[str, Any]]:
        """Search for release asynchronously."""
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            return await loop.run_in_executor(executor, self._search_release_sync, artist, album)

    async def enrich(self, request: EnrichmentRequest) -> Optional[EnrichmentData]:
        """Enrich with Discogs data."""
        if not self.can_enrich(request):
            return None

        await self._rate_limit()

        try:
            self.logger.debug("Enriching with Discogs: %s - %s", request.artist, request.album)

            enrichment = EnrichmentData()
            enrichment.last_updated["discogs"] = time.time()

            # Search for artist if provided
            if request.artist:
                artist_data = await self._search_artist(request.artist)
                if artist_data:
                    enrichment.discogs_artist_id = str(artist_data.get("id"))

            # Search for release if both artist and album provided
            if request.artist and request.album:
                release_data = await self._search_release(request.artist, request.album)
                if release_data:
                    enrichment.discogs_release_id = str(release_data.get("id"))
                    
                    # Add release info to discography
                    enrichment.artist_discography = [
                        {
                            "title": release_data.get("title", request.album),
                            "year": str(release_data.get("year", "Unknown")),
                            "format": ", ".join(release_data.get("format", [])),
                            "country": release_data.get("country", "Unknown"),
                            "discogs_id": str(release_data.get("id")),
                        }
                    ]

            return enrichment

        except Exception as e:
            self.logger.error("Discogs enrichment failed: %s", e)
            enrichment = EnrichmentData()
            enrichment.service_errors["discogs"] = str(e)
            return enrichment
