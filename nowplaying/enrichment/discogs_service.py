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
from typing import Any, Dict, List, Optional

from .base import EnrichmentData, EnrichmentRequest, EnrichmentService


class DiscogsService(EnrichmentService):
    """Discogs metadata enrichment service."""

    def __init__(self):
        """Initialize Discogs service."""
        super().__init__("discogs", "Discogs")
        self._rate_limit_delay = 1.5  # Discogs rate limit is 60 requests/minute
        self._base_url = "https://api.discogs.com"
        self._user_agent = "NowPlayingApp/1.0 +https://github.com/user/now-playing"

    def _search_artist_sync(self, artist_name: str) -> Optional[Dict[str, Any]]:
        """Synchronous version of artist search for thread pool execution."""
        try:
            query = urllib.parse.quote_plus(artist_name)
            url = f"{self._base_url}/database/search?q={query}&type=artist&per_page=1"

            req = urllib.request.Request(
                url,
                headers={"User-Agent": self._user_agent, "Accept": "application/json"},
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))

                if data.get("results") and len(data["results"]) > 0:
                    artist = data["results"][0]
                    return {
                        "id": artist.get("id"),
                        "title": artist.get("title"),
                        "resource_url": artist.get("resource_url"),
                        "uri": artist.get("uri"),
                        "cover_image": artist.get("cover_image"),
                        "thumb": artist.get("thumb"),
                    }

        except Exception as e:
            self.logger.warning(f"Discogs artist search failed for '{artist_name}': {e}")

        return None

    def _search_release_sync(self, artist: str, album: str) -> Optional[Dict[str, Any]]:
        """Synchronous version of release search for thread pool execution."""
        try:
            # Create a combined query for better results
            query = urllib.parse.quote_plus(f"{artist} {album}")
            url = f"{self._base_url}/database/search?q={query}&type=release&per_page=5"

            req = urllib.request.Request(
                url,
                headers={"User-Agent": self._user_agent, "Accept": "application/json"},
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))

                if data.get("results"):
                    # Find the best match (simple scoring based on title similarity)
                    best_match = None
                    best_score = 0

                    for release in data["results"]:
                        title = release.get("title", "").lower()
                        # Simple scoring: exact album match gets high score
                        score = 0
                        if album.lower() in title:
                            score += 50
                        if artist.lower() in title:
                            score += 30

                        if score > best_score:
                            best_score = score
                            best_match = release

                    if best_match:
                        return {
                            "id": best_match.get("id"),
                            "title": best_match.get("title"),
                            "year": best_match.get("year"),
                            "format": best_match.get("format", []),
                            "country": best_match.get("country"),
                            "genre": best_match.get("genre", []),
                            "style": best_match.get("style", []),
                            "label": best_match.get("label", []),
                            "resource_url": best_match.get("resource_url"),
                            "cover_image": best_match.get("cover_image"),
                            "thumb": best_match.get("thumb"),
                        }

        except Exception as e:
            self.logger.warning(f"Discogs release search failed for '{artist} - {album}': {e}")

        return None

    def _get_artist_releases_sync(self, artist_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get artist discography from Discogs."""
        try:
            url = f"{self._base_url}/artists/{artist_id}/releases?per_page={limit}&sort=year&sort_order=desc"

            req = urllib.request.Request(
                url,
                headers={"User-Agent": self._user_agent, "Accept": "application/json"},
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))

                releases = []
                for release in data.get("releases", []):
                    releases.append({
                        "title": release.get("title", ""),
                        "year": release.get("year"),
                        "role": release.get("role", ""),
                        "type": release.get("type", ""),
                        "format": release.get("format", ""),
                        "label": release.get("label", ""),
                        "resource_url": release.get("resource_url", ""),
                        "thumb": release.get("thumb", ""),
                    })

                return releases

        except Exception as e:
            self.logger.warning(f"Discogs artist releases failed for artist_id '{artist_id}': {e}")

        return []

    async def enrich(self, request: EnrichmentRequest) -> Optional[EnrichmentData]:
        """Enrich with Discogs data."""
        if not self.can_enrich(request):
            return None

        await self._rate_limit()

        try:
            self.logger.debug("Enriching with Discogs: %s - %s", request.artist, request.album)

            enrichment = EnrichmentData()

            # Perform searches using thread pool to avoid blocking async loop
            loop = asyncio.get_event_loop()

            with ThreadPoolExecutor(max_workers=2) as executor:
                # Submit searches concurrently
                artist_future = loop.run_in_executor(executor, self._search_artist_sync, request.artist)

                release_future = None
                if request.album:
                    release_future = loop.run_in_executor(
                        executor,
                        self._search_release_sync,
                        request.artist,
                        request.album,
                    )

                # Collect artist results
                artist_info = await artist_future
                if artist_info:
                    enrichment.discogs_artist_id = str(artist_info["id"])

                    # Get artist discography if we have an artist ID
                    discography_future = loop.run_in_executor(
                        executor,
                        self._get_artist_releases_sync,
                        enrichment.discogs_artist_id,
                        15,  # Get more releases for discovery
                    )

                    discography = await discography_future
                    if discography:
                        enrichment.artist_discography = discography

                # Get release info
                if release_future:
                    release_info = await release_future
                    if release_info:
                        enrichment.discogs_release_id = str(release_info["id"])

                        # Add genre/style tags
                        for genre in release_info.get("genre", []):
                            if genre not in enrichment.artist_tags:
                                enrichment.artist_tags.append(genre.lower())

                        for style in release_info.get("style", []):
                            if style not in enrichment.artist_tags:
                                enrichment.artist_tags.append(style.lower())

                        # Add album review placeholder (Discogs doesn't have reviews in API)
                        if release_info.get("year"):
                            enrichment.album_reviews.append({
                                "source": "discogs",
                                "rating": None,
                                "summary": f"Released in {release_info['year']}",
                                "format": ", ".join(release_info.get("format", [])),
                                "label": ", ".join(release_info.get("label", [])),
                            })

            enrichment.last_updated["discogs"] = time.time()

            return enrichment

        except Exception as e:
            self.logger.error("Discogs enrichment failed: %s", e)
            enrichment = EnrichmentData()
            enrichment.service_errors["discogs"] = str(e)
            return enrichment
