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

    def __init__(self, api_token: Optional[str] = None):
        """Initialize Discogs service.
        
        Args:
            api_token: Discogs API token. If None, service will use mock data.
        """
        super().__init__("discogs", "Discogs")
        self._rate_limit_delay = 1.5  # Discogs rate limit (conservative)
        self._api_token = api_token
        self._base_url = "https://api.discogs.com"
        self._user_agent = "NowPlayingApp/1.0"

    def _search_artist_sync(self, artist_name: str) -> Optional[Dict[str, Any]]:
        """Synchronous version of artist search for thread pool execution."""
        if not self._api_token:
            return None
            
        try:
            params = {
                "q": artist_name,
                "type": "artist",
                "per_page": "5"
            }
            
            url = f"{self._base_url}/database/search?{urllib.parse.urlencode(params)}"
            
            headers = {
                "User-Agent": self._user_agent,
                "Authorization": f"Discogs token={self._api_token}"
            }
            
            req = urllib.request.Request(url, headers=headers)
            
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))
                
                if "results" in data and data["results"]:
                    # Return the best match (first result)
                    return data["results"][0]
                    
        except Exception as e:
            self.logger.warning(f"Discogs artist search failed for '{artist_name}': {e}")
            
        return None

    def _search_release_sync(self, artist_name: str, album_name: str) -> Optional[Dict[str, Any]]:
        """Synchronous version of release search for thread pool execution."""
        if not self._api_token:
            return None
            
        try:
            params = {
                "q": f'artist:"{artist_name}" release_title:"{album_name}"',
                "type": "release",
                "per_page": "5"
            }
            
            url = f"{self._base_url}/database/search?{urllib.parse.urlencode(params)}"
            
            headers = {
                "User-Agent": self._user_agent,
                "Authorization": f"Discogs token={self._api_token}"
            }
            
            req = urllib.request.Request(url, headers=headers)
            
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))
                
                if "results" in data and data["results"]:
                    # Return the best match (first result)
                    return data["results"][0]
                    
        except Exception as e:
            self.logger.warning(f"Discogs release search failed for '{artist_name} - {album_name}': {e}")
            
        return None

    def _get_artist_releases_sync(self, artist_id: str) -> Optional[List[Dict[str, Any]]]:
        """Synchronous version of artist releases fetch for thread pool execution."""
        if not self._api_token:
            return None
            
        try:
            params = {
                "per_page": "20",
                "sort": "year",
                "sort_order": "desc"
            }
            
            url = f"{self._base_url}/artists/{artist_id}/releases?{urllib.parse.urlencode(params)}"
            
            headers = {
                "User-Agent": self._user_agent,
                "Authorization": f"Discogs token={self._api_token}"
            }
            
            req = urllib.request.Request(url, headers=headers)
            
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))
                
                if "releases" in data:
                    return data["releases"]
                    
        except Exception as e:
            self.logger.warning(f"Discogs artist releases fetch failed for artist '{artist_id}': {e}")
            
        return None

    async def enrich(self, request: EnrichmentRequest) -> Optional[EnrichmentData]:
        """Enrich with Discogs data."""
        if not self.can_enrich(request):
            return None

        await self._rate_limit()

        try:
            self.logger.debug("Enriching with Discogs: %s - %s", request.artist, request.album)

            enrichment = EnrichmentData()
            enrichment.last_updated["discogs"] = time.time()

            # If we have an API token, make real API calls
            if self._api_token:
                loop = asyncio.get_event_loop()
                
                with ThreadPoolExecutor(max_workers=3) as executor:
                    # Submit searches concurrently
                    artist_future = loop.run_in_executor(
                        executor, self._search_artist_sync, request.artist
                    )
                    
                    release_future = None
                    if request.album:
                        release_future = loop.run_in_executor(
                            executor, self._search_release_sync, request.artist, request.album
                        )
                    
                    # Get artist info
                    artist_info = await artist_future
                    if artist_info:
                        enrichment.discogs_artist_id = str(artist_info.get("id", ""))
                        
                        # Get artist discography if we have an artist ID
                        if artist_info.get("id"):
                            discography_future = loop.run_in_executor(
                                executor, self._get_artist_releases_sync, str(artist_info["id"])
                            )
                            
                            discography = await discography_future
                            if discography:
                                enrichment.artist_discography = []
                                for release in discography[:10]:  # Top 10 releases
                                    enrichment.artist_discography.append({
                                        "title": release.get("title", ""),
                                        "year": str(release.get("year", "")),
                                        "format": release.get("format", ["Unknown"])[0] if release.get("format") else "Unknown",
                                        "role": release.get("role", "Main"),
                                        "resource_url": release.get("resource_url", "")
                                    })
                    
                    # Get release info
                    if release_future:
                        release_info = await release_future
                        if release_info:
                            enrichment.discogs_release_id = str(release_info.get("id", ""))

            else:
                # Enhanced mock data when no API token
                self.logger.debug("No Discogs API token provided, using enhanced mock data")
                
                enrichment.discogs_artist_id = f"discogs-artist-{hash(request.artist) % 10000}"
                if request.album:
                    enrichment.discogs_release_id = f"discogs-release-{hash(request.album) % 10000}"
                
                # Generate more realistic mock discography
                base_year = 2024
                formats = ["LP", "CD", "Digital", "Cassette", "7\""]
                enrichment.artist_discography = []
                
                # Current album
                if request.album:
                    enrichment.artist_discography.append({
                        "title": request.album,
                        "year": str(base_year),
                        "format": formats[hash(request.album) % len(formats)],
                        "role": "Main"
                    })
                
                # Generate some historical releases
                for i in range(1, 6):
                    year = base_year - (i * 2)
                    title = f"Album #{6-i}" if i < 5 else "Debut Album"
                    enrichment.artist_discography.append({
                        "title": title,
                        "year": str(year),
                        "format": formats[(hash(request.artist) + i) % len(formats)],
                        "role": "Main"
                    })

            return enrichment

        except Exception as e:
            self.logger.error("Discogs enrichment failed: %s", e)
            enrichment = EnrichmentData()
            enrichment.service_errors["discogs"] = str(e)
            return enrichment
