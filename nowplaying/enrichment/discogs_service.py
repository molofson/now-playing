"""Provide Discogs metadata enrichment.

Integrate with the Discogs database to retrieve release information,
artist discographies, and marketplace data.
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
        self._rate_limit_delay = 1.0  # Discogs rate limit (60 requests per minute for unauthenticated)
        self._base_url = "https://api.discogs.com"
        self._user_agent = "NowPlayingApp/1.0 (https://github.com/user/now-playing)"
        # Discogs requires authentication - you can get a token from https://www.discogs.com/settings/developers
        self._api_token = None  # Set this to your Discogs API token

    def set_api_token(self, token: str):
        """Set the Discogs API token for authenticated requests."""
        self._api_token = token
        if token:
            self._rate_limit_delay = 0.1  # Authenticated requests allow 1000 per hour (60 per minute)

    def _get_request_headers(self):
        """Get request headers including authentication if available."""
        headers = {
            "User-Agent": self._user_agent,
            "Accept": "application/json",
        }
        if self._api_token:
            headers["Authorization"] = f"Discogs token={self._api_token}"
        return headers

    def _search_artist_sync(self, artist_name: str) -> Optional[Dict[str, Any]]:
        """Perform synchronous artist search."""
        try:
            query = urllib.parse.quote_plus(artist_name)
            url = f"{self._base_url}/database/search?q={query}&type=artist&per_page=5"

            req = urllib.request.Request(
                url,
                headers=self._get_request_headers(),
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))

                if data.get("results") and len(data["results"]) > 0:
                    # Find the best match (highest score or first result)
                    artist = data["results"][0]
                    return {
                        "id": artist.get("id"),
                        "name": artist.get("title", "").replace(" (Artist)", ""),  # Clean up name
                        "resource_url": artist.get("resource_url"),
                        "thumb": artist.get("thumb"),
                        "score": artist.get("score", 0),
                    }

        except Exception as e:
            self.logger.warning(f"Discogs artist search failed for '{artist_name}': {e}")

        return None

    def _search_release_sync(self, artist: str, album: str) -> Optional[Dict[str, Any]]:
        """Perform synchronous release search."""
        try:
            query = urllib.parse.quote_plus(f"{album} {artist}")
            url = f"{self._base_url}/database/search?q={query}&type=release&per_page=5"

            req = urllib.request.Request(
                url,
                headers=self._get_request_headers(),
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))

                if data.get("results") and len(data["results"]) > 0:
                    # Find best match for this artist/album combination
                    for result in data["results"]:
                        title = result.get("title", "").lower()
                        if artist.lower() in title and album.lower() in title:
                            return {
                                "id": result.get("id"),
                                "title": result.get("title"),
                                "year": result.get("year"),
                                "resource_url": result.get("resource_url"),
                                "thumb": result.get("thumb"),
                                "country": result.get("country"),
                                "format": result.get("format"),
                                "score": result.get("score", 0),
                            }

                    # If no exact match, return first result
                    result = data["results"][0]
                    return {
                        "id": result.get("id"),
                        "title": result.get("title"),
                        "year": result.get("year"),
                        "resource_url": result.get("resource_url"),
                        "thumb": result.get("thumb"),
                        "country": result.get("country"),
                        "format": result.get("format"),
                        "score": result.get("score", 0),
                    }

        except Exception as e:
            self.logger.warning(f"Discogs release search failed for '{artist} - {album}': {e}")

        return None

    def _get_artist_releases_sync(self, artist_id: int) -> Optional[List[Dict[str, Any]]]:
        """Fetch artist releases synchronously."""
        try:
            url = f"{self._base_url}/artists/{artist_id}/releases?per_page=20&sort=year&sort_order=desc"

            req = urllib.request.Request(
                url,
                headers=self._get_request_headers(),
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))

                if data.get("releases"):
                    discography = []
                    for release in data["releases"][:10]:  # Limit to 10 most recent
                        discography.append(
                            {
                                "title": release.get("title", ""),
                                "year": release.get("year", ""),
                                "format": ", ".join(release.get("format", [])),
                                "role": release.get("role", ""),
                                "resource_url": release.get("resource_url"),
                            }
                        )

                    return discography

        except Exception as e:
            self.logger.warning(f"Discogs artist releases fetch failed for artist ID {artist_id}: {e}")

        return None

    def _get_release_details_sync(self, release_id: int) -> Optional[Dict[str, Any]]:
        """Fetch release details synchronously."""
        try:
            url = f"{self._base_url}/releases/{release_id}"

            req = urllib.request.Request(
                url,
                headers=self._get_request_headers(),
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))

                # Extract credits and other release information
                credits = []
                if data.get("extraartists"):
                    for artist in data["extraartists"]:
                        credits.append(
                            {
                                "role": artist.get("role", ""),
                                "artist": artist.get("name", ""),
                                "tracks": artist.get("tracks", ""),
                            }
                        )

                return {
                    "id": data.get("id"),
                    "title": data.get("title"),
                    "artists": data.get("artists", []),
                    "genres": data.get("genres", []),
                    "styles": data.get("styles", []),
                    "year": data.get("year"),
                    "country": data.get("country"),
                    "labels": data.get("labels", []),
                    "formats": data.get("formats", []),
                    "tracklist": data.get("tracklist", []),
                    "credits": credits,
                }

        except Exception as e:
            self.logger.warning(f"Discogs release details fetch failed for release ID {release_id}: {e}")

        return None

    async def enrich(self, request: EnrichmentRequest) -> Optional[EnrichmentData]:
        """Enrich with Discogs data."""
        if not self.can_enrich(request):
            return None

        # Check if we have authentication - if not, skip Discogs
        if not self._api_token:
            self.logger.debug(
                "Discogs enrichment skipped - no API token configured. Get one from https://www.discogs.com/settings/developers"
            )
            return None

        await self._rate_limit()

        try:
            self.logger.debug("Enriching with Discogs: %s - %s", request.artist, request.album)

            enrichment = EnrichmentData()

            # Perform searches using thread pool to avoid blocking async loop
            loop = asyncio.get_event_loop()

            with ThreadPoolExecutor(max_workers=3) as executor:
                # Search for artist
                artist_future = loop.run_in_executor(executor, self._search_artist_sync, request.artist)

                # Search for release if we have album info
                release_future = None
                if request.album:
                    release_future = loop.run_in_executor(
                        executor,
                        self._search_release_sync,
                        request.artist,
                        request.album,
                    )

                # Get artist info
                artist_info = await artist_future
                if artist_info:
                    enrichment.discogs_artist_id = str(artist_info["id"])

                    # Fetch artist discography
                    discography_future = loop.run_in_executor(
                        executor, self._get_artist_releases_sync, artist_info["id"]
                    )
                    discography = await discography_future
                    if discography:
                        enrichment.artist_discography = discography

                # Get release info and details
                if release_future:
                    release_info = await release_future
                    if release_info:
                        enrichment.discogs_release_id = str(release_info["id"])

                        # Fetch detailed release information
                        release_details_future = loop.run_in_executor(
                            executor, self._get_release_details_sync, release_info["id"]
                        )
                        release_details = await release_details_future
                        if release_details:
                            # Extract album reviews from release notes or descriptions
                            # Discogs doesn't have traditional reviews, but we can use community data
                            if release_details.get("genres"):
                                enrichment.artist_tags.extend(
                                    [f"genre:{genre.lower()}" for genre in release_details["genres"]]
                                )

                            if release_details.get("styles"):
                                enrichment.artist_tags.extend(
                                    [f"style:{style.lower()}" for style in release_details["styles"]]
                                )

                            # Extract credits
                            if release_details.get("credits"):
                                enrichment.album_credits = release_details["credits"]

            enrichment.last_updated["discogs"] = time.time()

            # Check if we got any meaningful data
            if (
                not enrichment.discogs_artist_id
                and not enrichment.discogs_release_id
                and not enrichment.artist_discography
                and not enrichment.album_credits
            ):
                # If no data was enriched, it might indicate a service problem
                self.logger.debug("No Discogs data enriched for: %s - %s", request.artist, request.album)

            self.logger.info(
                "Discogs enrichment result: artist_id=%s, release_id=%s, discography=%d items",
                enrichment.discogs_artist_id,
                enrichment.discogs_release_id,
                len(enrichment.artist_discography) if enrichment.artist_discography else 0,
            )

            return enrichment

        except Exception as e:
            self.logger.error("Discogs enrichment failed: %s", e)
            enrichment = EnrichmentData()
            enrichment.service_errors["discogs"] = str(e)
            self.logger.info("Discogs enrichment result (error): %s", enrichment)
            return enrichment
