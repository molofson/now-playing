"""
Last.fm metadata enrichment service.

This module provides integration with the Last.fm API for retrieving
artist biographies, tags, similar artists, and scrobble data.

To use this service, you need a Last.fm API key:
1. Go to https://www.last.fm/api/account/create
2. Create a new application to get your API key
3. Configure the service with: service.set_api_key("your_api_key_here")

Without an API key, the service will be skipped gracefully.
"""

import asyncio
import json
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

from .base import EnrichmentData, EnrichmentRequest, EnrichmentService


class LastFmService(EnrichmentService):
    """Last.fm metadata enrichment service."""

    def __init__(self):
        """Initialize Last.fm service."""
        super().__init__("lastfm", "Last.fm")
        self._rate_limit_delay = 0.2  # Last.fm rate limit (5 requests per second for authenticated)
        self._base_url = "http://ws.audioscrobbler.com/2.0/"
        self._user_agent = "NowPlayingApp/1.0 (https://github.com/user/now-playing)"
        # Last.fm requires an API key - you can get one from https://www.last.fm/api/account/create
        self._api_key = None  # Set this to your Last.fm API key

    def set_api_key(self, api_key: str):
        """Set the Last.fm API key for authenticated requests."""
        self._api_key = api_key

    def _get_request_params(self, method: str, **kwargs) -> Dict[str, str]:
        """Get base request parameters including API key."""
        params = {
            "method": method,
            "api_key": self._api_key or "",
            "format": "json",
        }
        params.update(kwargs)
        return params

    def _make_request(self, params: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Make a request to the Last.fm API."""
        try:
            url = f"{self._base_url}?{urllib.parse.urlencode(params)}"

            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": self._user_agent,
                    "Accept": "application/json",
                },
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))
                return data

        except Exception:
            self.logger.warning("Last.fm API request failed")
            return None

    def _get_artist_info_sync(self, artist_name: str) -> Optional[Dict[str, Any]]:
        """Fetch artist info synchronously."""
        if not self._api_key:
            return None

        try:
            params = self._get_request_params(
                "artist.getInfo",
                artist=artist_name,
                autocorrect=1,  # Enable autocorrect for artist names
            )

            data = self._make_request(params)
            if data and "artist" in data:
                artist_data = data["artist"]
                return {
                    "name": artist_data.get("name", ""),
                    "bio": artist_data.get("bio", {}).get("content", ""),
                    "tags": [tag["name"] for tag in artist_data.get("tags", {}).get("tag", [])],
                    "stats": artist_data.get("stats", {}),
                    "similar": artist_data.get("similar", {}).get("artist", []),
                }

        except Exception as e:
            self.logger.warning(f"Last.fm artist info fetch failed for '{artist_name}': {e}")

        return None

    def _get_artist_top_tracks_sync(self, artist_name: str) -> Optional[List[Dict[str, Any]]]:
        """Fetch artist top tracks synchronously."""
        if not self._api_key:
            return None

        try:
            params = self._get_request_params(
                "artist.getTopTracks",
                artist=artist_name,
                limit=5,
            )

            data = self._make_request(params)
            if data and "toptracks" in data and "track" in data["toptracks"]:
                tracks = []
                for track in data["toptracks"]["track"][:5]:
                    tracks.append(
                        {
                            "name": track.get("name", ""),
                            "playcount": int(track.get("playcount", 0)),
                            "listeners": int(track.get("listeners", 0)),
                        }
                    )
                return tracks

        except Exception as e:
            self.logger.warning(f"Last.fm artist top tracks fetch failed for '{artist_name}': {e}")

        return None

    async def enrich(self, request: EnrichmentRequest) -> Optional[EnrichmentData]:
        """Enrich with Last.fm data."""
        if not self.can_enrich(request):
            return None

        # Check if we have API key - if not, skip Last.fm
        if not self._api_key:
            self.logger.debug(
                "Last.fm enrichment skipped - no API key configured. Get one from https://www.last.fm/api/account/create"
            )
            return None

        await self._rate_limit()

        try:
            self.logger.debug("Enriching with Last.fm: %s", request.artist)

            enrichment = EnrichmentData()

            # Perform API calls using thread pool to avoid blocking async loop
            loop = asyncio.get_event_loop()

            with ThreadPoolExecutor(max_workers=2) as executor:
                # Get artist info (bio, tags, similar artists)
                artist_info_future = loop.run_in_executor(executor, self._get_artist_info_sync, request.artist)

                # Get artist top tracks for popularity data
                top_tracks_future = loop.run_in_executor(executor, self._get_artist_top_tracks_sync, request.artist)

                # Process artist info
                artist_info = await artist_info_future
                if artist_info:
                    # Artist biography
                    if artist_info.get("bio"):
                        # Clean up the bio - remove HTML and truncate if too long
                        bio = artist_info["bio"]
                        # Remove HTML tags (simple approach)
                        bio = bio.replace("<a href=", "").replace("</a>", "").replace(">", "").replace("<", "")
                        # Find the first paragraph or reasonable break
                        bio_lines = bio.split("\n")
                        clean_bio = bio_lines[0] if bio_lines else bio
                        if len(clean_bio) > 1000:  # Truncate very long bios
                            clean_bio = clean_bio[:997] + "..."
                        enrichment.artist_bio = clean_bio

                    # Artist tags
                    if artist_info.get("tags"):
                        enrichment.artist_tags = artist_info["tags"]

                    # Similar artists
                    if artist_info.get("similar"):
                        similar_artists = []
                        for similar in artist_info["similar"][:5]:  # Limit to 5
                            match = float(similar.get("match", 0)) / 100.0  # Convert percentage to decimal
                            similar_artists.append(
                                {
                                    "name": similar.get("name", ""),
                                    "match": match,
                                }
                            )
                        enrichment.similar_artists = similar_artists

                    # Scrobble count from artist stats
                    if artist_info.get("stats") and artist_info["stats"].get("playcount"):
                        enrichment.scrobble_count = int(artist_info["stats"]["playcount"])

                # Process top tracks for additional popularity data
                top_tracks = await top_tracks_future
                if top_tracks and not enrichment.scrobble_count:
                    # If we don't have artist playcount, use the highest track playcount as approximation
                    max_playcount = max((track.get("playcount", 0) for track in top_tracks), default=0)
                    if max_playcount > 0:
                        enrichment.scrobble_count = max_playcount

            enrichment.last_updated["lastfm"] = time.time()

            # Check if we got any meaningful data
            if (
                not enrichment.artist_bio
                and not enrichment.artist_tags
                and not enrichment.similar_artists
                and not enrichment.scrobble_count
            ):
                # If no data was enriched, it might indicate a service problem
                self.logger.debug("No Last.fm data enriched for: %s", request.artist)

            self.logger.info(
                "Last.fm enrichment result: bio=%s, tags=%d, similar=%d, scrobbles=%s",
                "yes" if enrichment.artist_bio else "no",
                len(enrichment.artist_tags) if enrichment.artist_tags else 0,
                len(enrichment.similar_artists) if enrichment.similar_artists else 0,
                enrichment.scrobble_count,
            )

            return enrichment

        except Exception as e:
            self.logger.error("Last.fm enrichment failed: %s", e)
            enrichment = EnrichmentData()
            enrichment.service_errors["lastfm"] = str(e)
            return enrichment
