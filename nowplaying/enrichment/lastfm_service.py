"""
Last.fm metadata enrichment service.

This module provides integration with the Last.fm API for retrieving
artist biographies, tags, similar artists, and scrobble data.
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
        self._rate_limit_delay = 0.5  # Last.fm rate limit
        self._base_url = "https://ws.audioscrobbler.com/2.0/"
        # Note: For a real implementation, you'd get this from config
        self._api_key = "demo_key"  # Replace with actual API key

    def _get_artist_info_sync(self, artist_name: str) -> Optional[Dict[str, Any]]:
        """Synchronous version of artist info lookup for thread pool execution."""
        try:
            params = {
                "method": "artist.getinfo",
                "artist": artist_name,
                "api_key": self._api_key,
                "format": "json",
            }
            query_string = urllib.parse.urlencode(params)
            url = f"{self._base_url}?{query_string}"

            req = urllib.request.Request(url, headers={"User-Agent": "NowPlayingApp/1.0"})

            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))

                if "artist" in data:
                    artist = data["artist"]
                    return {
                        "name": artist.get("name"),
                        "mbid": artist.get("mbid"),
                        "url": artist.get("url"),
                        "bio": artist.get("bio", {}).get("summary", ""),
                        "tags": [tag.get("name") for tag in artist.get("tags", {}).get("tag", [])],
                        "similar": [
                            {"name": sim.get("name"), "match": float(sim.get("match", 0))}
                            for sim in artist.get("similar", {}).get("artist", [])
                        ],
                        "stats": artist.get("stats", {}),
                    }

        except Exception as e:
            self.logger.warning(f"Last.fm artist info failed for '{artist_name}': {e}")

        return None

    def _get_similar_artists_sync(self, artist_name: str) -> List[Dict[str, Any]]:
        """Synchronous version of similar artists lookup."""
        try:
            params = {
                "method": "artist.getsimilar",
                "artist": artist_name,
                "api_key": self._api_key,
                "format": "json",
                "limit": "5",
            }
            query_string = urllib.parse.urlencode(params)
            url = f"{self._base_url}?{query_string}"

            req = urllib.request.Request(url, headers={"User-Agent": "NowPlayingApp/1.0"})

            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))

                if "similarartists" in data and "artist" in data["similarartists"]:
                    return [
                        {"name": artist.get("name"), "match": float(artist.get("match", 0))}
                        for artist in data["similarartists"]["artist"]
                    ]

        except Exception as e:
            self.logger.warning(f"Last.fm similar artists failed for '{artist_name}': {e}")

        return []

    async def _get_artist_info(self, artist_name: str) -> Optional[Dict[str, Any]]:
        """Get artist info asynchronously."""
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            return await loop.run_in_executor(executor, self._get_artist_info_sync, artist_name)

    async def _get_similar_artists(self, artist_name: str) -> List[Dict[str, Any]]:
        """Get similar artists asynchronously."""
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            return await loop.run_in_executor(executor, self._get_similar_artists_sync, artist_name)

    async def enrich(self, request: EnrichmentRequest) -> Optional[EnrichmentData]:
        """Enrich with Last.fm data."""
        if not self.can_enrich(request):
            return None

        await self._rate_limit()

        try:
            self.logger.debug("Enriching with Last.fm: %s", request.artist)

            enrichment = EnrichmentData()
            enrichment.last_updated["lastfm"] = time.time()

            if not request.artist:
                return enrichment

            # For demo purposes, we'll use mock data if no API key is configured
            if self._api_key == "demo_key":
                # Mock data
                enrichment.artist_bio = f"Demo biography for {request.artist}. Configure Last.fm API key for real data."
                enrichment.artist_tags = ["rock", "alternative", "indie"]
                enrichment.similar_artists = [
                    {"name": "Similar Artist 1", "match": 0.8},
                    {"name": "Similar Artist 2", "match": 0.7},
                ]
                enrichment.scrobble_count = abs(hash(request.artist)) % 1000000
                return enrichment

            # Real API calls (uncomment when API key is configured)
            # artist_info = await self._get_artist_info(request.artist)
            # if artist_info:
            #     enrichment.artist_bio = artist_info.get("bio", "")
            #     enrichment.artist_tags = artist_info.get("tags", [])
            #     enrichment.similar_artists = artist_info.get("similar", [])
            #     if "stats" in artist_info and "playcount" in artist_info["stats"]:
            #         enrichment.scrobble_count = int(artist_info["stats"]["playcount"])

            return enrichment

        except Exception as e:
            self.logger.error("Last.fm enrichment failed: %s", e)
            enrichment = EnrichmentData()
            enrichment.service_errors["lastfm"] = str(e)
            return enrichment
