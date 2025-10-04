"""
MusicBrainz metadata enrichment service.

This module provides integration with the MusicBrainz database for retrieving
artist, album, and track metadata and identifiers.
"""

import asyncio
import json
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

from .base import EnrichmentData, EnrichmentRequest, EnrichmentService


class MusicBrainzService(EnrichmentService):
    """MusicBrainz metadata enrichment service."""

    def __init__(self):
        """Initialize MusicBrainz service."""
        super().__init__("musicbrainz", "MusicBrainz")
        self._rate_limit_delay = 1.0  # MusicBrainz rate limit
        self._base_url = "https://musicbrainz.org/ws/2"
        self._user_agent = "NowPlayingApp/1.0 (https://github.com/user/now-playing)"

    def _search_artist_sync(self, artist_name: str) -> Optional[Dict[str, Any]]:
        """Perform synchronous artist search for thread pool execution."""
        try:
            query = urllib.parse.quote_plus(f'artist:"{artist_name}"')
            url = f"{self._base_url}/artist/?query={query}&fmt=json&limit=1"

            req = urllib.request.Request(
                url,
                headers={"User-Agent": self._user_agent, "Accept": "application/json"},
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))

                if data.get("artists") and len(data["artists"]) > 0:
                    artist = data["artists"][0]
                    return {
                        "id": artist.get("id"),
                        "name": artist.get("name"),
                        "sort_name": artist.get("sort-name"),
                        "type": artist.get("type"),
                        "country": artist.get("country"),
                        "life_span": artist.get("life-span", {}),
                        "score": artist.get("score", 0),
                    }

        except Exception as e:
            self.logger.warning(f"MusicBrainz artist search failed for '{artist_name}': {e}")

        return None

    def _search_release_sync(self, artist: str, album: str) -> Optional[Dict[str, Any]]:
        """Perform synchronous release search for thread pool execution."""
        try:
            query = urllib.parse.quote_plus(f'release:"{album}" AND artist:"{artist}"')
            url = f"{self._base_url}/release/?query={query}&fmt=json&limit=1"

            req = urllib.request.Request(
                url,
                headers={"User-Agent": self._user_agent, "Accept": "application/json"},
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))

                if data.get("releases") and len(data["releases"]) > 0:
                    release = data["releases"][0]
                    return {
                        "id": release.get("id"),
                        "title": release.get("title"),
                        "status": release.get("status"),
                        "date": release.get("date"),
                        "country": release.get("country"),
                        "packaging": release.get("packaging"),
                        "artist_credit": release.get("artist-credit", []),
                        "score": release.get("score", 0),
                    }

        except Exception as e:
            self.logger.warning(f"MusicBrainz release search failed for '{artist} - {album}': {e}")

        return None

    def _search_recording_sync(self, artist: str, track: str) -> Optional[Dict[str, Any]]:
        """Perform synchronous recording search for thread pool execution."""
        try:
            query = urllib.parse.quote_plus(f'recording:"{track}" AND artist:"{artist}"')
            url = f"{self._base_url}/recording/?query={query}&fmt=json&limit=1"

            req = urllib.request.Request(
                url,
                headers={"User-Agent": self._user_agent, "Accept": "application/json"},
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))

                if data.get("recordings") and len(data["recordings"]) > 0:
                    recording = data["recordings"][0]
                    return {
                        "id": recording.get("id"),
                        "title": recording.get("title"),
                        "length": recording.get("length"),
                        "artist_credit": recording.get("artist-credit", []),
                        "releases": recording.get("releases", []),
                        "score": recording.get("score", 0),
                    }

        except Exception as e:
            self.logger.warning(f"MusicBrainz recording search failed for '{artist} - {track}': {e}")

        return None

    def _fetch_cover_art_sync(self, release_id: str) -> Optional[List[Dict[str, Any]]]:
        """Fetch cover art synchronously."""
        try:
            url = f"https://coverartarchive.org/release/{release_id}"

            req = urllib.request.Request(
                url,
                headers={"User-Agent": self._user_agent, "Accept": "application/json"},
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))

                if data.get("images"):
                    cover_urls = []
                    for image in data["images"]:
                        if image.get("front") or (image.get("types") and "Front" in image.get("types", [])):
                            cover_urls.append(
                                {
                                    "url": image.get("image"),
                                    "thumbnails": image.get("thumbnails", {}),
                                    "type": "front_cover",
                                    "source": "musicbrainz",
                                }
                            )

                    return cover_urls[:3]  # Limit to 3 images

        except Exception as e:
            self.logger.debug(f"Cover art fetch failed for release {release_id}: {e}")

        return None

    async def _search_artist(self, artist_name: str) -> Optional[Dict[str, Any]]:
        """Async wrapper for artist search."""
        return self._search_artist_sync(artist_name)

    async def _search_release(self, artist: str, album: str) -> Optional[Dict[str, Any]]:
        """Async wrapper for release search."""
        return self._search_release_sync(artist, album)

    async def _search_recording(self, artist: str, track: str) -> Optional[Dict[str, Any]]:
        """Async wrapper for recording search."""
        return self._search_recording_sync(artist, track)

    async def _fetch_cover_art(self, release_id: str) -> Optional[List[Dict[str, Any]]]:
        """Async wrapper for cover art fetching."""
        return self._fetch_cover_art_sync(release_id)

    async def enrich(self, request: EnrichmentRequest) -> Optional[EnrichmentData]:
        """Enrich with MusicBrainz data."""
        if not self.can_enrich(request):
            return None

        await self._rate_limit()

        try:
            self.logger.debug("Enriching with MusicBrainz: %s - %s", request.artist, request.title)

            enrichment = EnrichmentData()

            # Perform searches using thread pool to avoid blocking async loop
            loop = asyncio.get_event_loop()

            with ThreadPoolExecutor(max_workers=3) as executor:
                # Submit all searches concurrently
                artist_future = loop.run_in_executor(executor, self._search_artist_sync, request.artist)

                album_future = None
                if request.album:
                    album_future = loop.run_in_executor(
                        executor,
                        self._search_release_sync,
                        request.artist,
                        request.album,
                    )

                track_future = None
                if request.title:
                    track_future = loop.run_in_executor(
                        executor,
                        self._search_recording_sync,
                        request.artist,
                        request.title,
                    )

                # Collect results
                artist_info = await artist_future
                if artist_info:
                    enrichment.musicbrainz_artist_id = artist_info["id"]
                    # Add artist bio/tags if available
                    if artist_info.get("type"):
                        enrichment.artist_tags.append(f"type:{artist_info['type'].lower()}")
                    if artist_info.get("country"):
                        enrichment.artist_tags.append(f"country:{artist_info['country']}")

                # Get album info
                if album_future:
                    album_info = await album_future
                    if album_info:
                        enrichment.musicbrainz_album_id = album_info["id"]
                        # Extract album credits from artist-credit
                        if album_info.get("artist_credit"):
                            for credit in album_info["artist_credit"]:
                                if isinstance(credit, dict) and credit.get("artist"):
                                    enrichment.album_credits.append(
                                        {
                                            "role": "artist",
                                            "artist": credit["artist"].get("name", ""),
                                            "musicbrainz_id": credit["artist"].get("id", ""),
                                        }
                                    )

                        # Fetch cover art URLs for this release
                        cover_art_future = loop.run_in_executor(executor, self._fetch_cover_art_sync, album_info["id"])
                        cover_art = await cover_art_future
                        if cover_art:
                            enrichment.cover_art_urls.extend(cover_art)

                # Get track info
                if track_future:
                    track_info = await track_future
                    if track_info:
                        enrichment.musicbrainz_track_id = track_info["id"]

            enrichment.last_updated["musicbrainz"] = time.time()

            # Check if we got any data at all
            if (
                enrichment.musicbrainz_artist_id is None
                and enrichment.musicbrainz_album_id is None
                and enrichment.musicbrainz_track_id is None
            ):
                # If no data was enriched, it might indicate a service problem
                # This happens when all individual searches fail
                pass  # Still return the enrichment, just with no data

            self.logger.info("MusicBrainz enrichment result: %s", enrichment)
            return enrichment

        except Exception as e:
            self.logger.error("MusicBrainz enrichment failed: %s", e)
            enrichment = EnrichmentData()
            enrichment.service_errors["musicbrainz"] = str(e)
            self.logger.info("MusicBrainz enrichment result (error): %s", enrichment)
            return enrichment
