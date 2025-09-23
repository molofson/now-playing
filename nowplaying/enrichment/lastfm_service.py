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

    def __init__(self, api_key: Optional[str] = None):
        """Initialize Last.fm service.
        
        Args:
            api_key: Last.fm API key. If None, service will use mock data.
        """
        super().__init__("lastfm", "Last.fm")
        self._rate_limit_delay = 0.5  # Last.fm rate limit
        self._api_key = api_key
        self._base_url = "https://ws.audioscrobbler.com/2.0/"
        self._user_agent = "NowPlayingApp/1.0"

    def _fetch_artist_info_sync(self, artist_name: str) -> Optional[Dict[str, Any]]:
        """Synchronous version of artist info fetch for thread pool execution."""
        if not self._api_key:
            return None
            
        try:
            params = {
                "method": "artist.getinfo",
                "artist": artist_name,
                "api_key": self._api_key,
                "format": "json",
                "autocorrect": "1"
            }
            
            url = f"{self._base_url}?{urllib.parse.urlencode(params)}"
            
            req = urllib.request.Request(
                url,
                headers={"User-Agent": self._user_agent}
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))
                
                if "artist" in data:
                    return data["artist"]
                    
        except Exception as e:
            self.logger.warning(f"Last.fm artist info fetch failed for '{artist_name}': {e}")
            
        return None

    def _fetch_similar_artists_sync(self, artist_name: str) -> Optional[List[Dict[str, Any]]]:
        """Synchronous version of similar artists fetch for thread pool execution."""
        if not self._api_key:
            return None
            
        try:
            params = {
                "method": "artist.getsimilar", 
                "artist": artist_name,
                "api_key": self._api_key,
                "format": "json",
                "autocorrect": "1",
                "limit": "10"
            }
            
            url = f"{self._base_url}?{urllib.parse.urlencode(params)}"
            
            req = urllib.request.Request(
                url,
                headers={"User-Agent": self._user_agent}
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))
                
                if "similarartists" in data and "artist" in data["similarartists"]:
                    return data["similarartists"]["artist"]
                    
        except Exception as e:
            self.logger.warning(f"Last.fm similar artists fetch failed for '{artist_name}': {e}")
            
        return None

    def _fetch_track_info_sync(self, artist_name: str, track_name: str) -> Optional[Dict[str, Any]]:
        """Synchronous version of track info fetch for thread pool execution."""
        if not self._api_key:
            return None
            
        try:
            params = {
                "method": "track.getinfo",
                "artist": artist_name,
                "track": track_name,
                "api_key": self._api_key,
                "format": "json",
                "autocorrect": "1"
            }
            
            url = f"{self._base_url}?{urllib.parse.urlencode(params)}"
            
            req = urllib.request.Request(
                url,
                headers={"User-Agent": self._user_agent}
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))
                
                if "track" in data:
                    return data["track"]
                    
        except Exception as e:
            self.logger.warning(f"Last.fm track info fetch failed for '{artist_name} - {track_name}': {e}")
            
        return None

    async def enrich(self, request: EnrichmentRequest) -> Optional[EnrichmentData]:
        """Enrich with Last.fm data."""
        if not self.can_enrich(request):
            return None

        await self._rate_limit()

        try:
            self.logger.debug("Enriching with Last.fm: %s", request.artist)

            enrichment = EnrichmentData()
            enrichment.last_updated["lastfm"] = time.time()

            # If we have an API key, make real API calls
            if self._api_key:
                loop = asyncio.get_event_loop()
                
                with ThreadPoolExecutor(max_workers=3) as executor:
                    # Submit all requests concurrently
                    artist_future = loop.run_in_executor(
                        executor, self._fetch_artist_info_sync, request.artist
                    )
                    
                    similar_future = loop.run_in_executor(
                        executor, self._fetch_similar_artists_sync, request.artist  
                    )
                    
                    track_future = None
                    if request.title:
                        track_future = loop.run_in_executor(
                            executor, self._fetch_track_info_sync, request.artist, request.title
                        )
                    
                    # Collect results
                    artist_info = await artist_future
                    if artist_info:
                        # Extract bio
                        bio = artist_info.get("bio", {})
                        if bio.get("content"):
                            enrichment.artist_bio = bio["content"][:500] + "..." if len(bio["content"]) > 500 else bio["content"]
                        
                        # Extract tags
                        tags = artist_info.get("tags", {})
                        if tags.get("tag"):
                            enrichment.artist_tags = [tag.get("name", "") for tag in tags["tag"] if tag.get("name")][:10]
                        
                        # Extract stats
                        stats = artist_info.get("stats", {})
                        if stats.get("playcount"):
                            try:
                                enrichment.scrobble_count = int(stats["playcount"])
                            except (ValueError, TypeError):
                                pass
                    
                    # Get similar artists
                    similar_artists = await similar_future
                    if similar_artists:
                        enrichment.similar_artists = []
                        for artist in similar_artists[:5]:  # Top 5 similar
                            if artist.get("name"):
                                match_score = 1.0
                                if artist.get("match"):
                                    try:
                                        match_score = float(artist["match"])
                                    except (ValueError, TypeError):
                                        pass
                                enrichment.similar_artists.append({
                                    "name": artist["name"],
                                    "match": match_score
                                })
                    
                    # Get track info
                    if track_future:
                        track_info = await track_future
                        if track_info:
                            # Extract additional track-specific metadata if needed
                            pass

            else:
                # Fallback to enhanced mock data when no API key
                self.logger.debug("No Last.fm API key provided, using enhanced mock data")
                
                enrichment.artist_bio = f"Mock biography for {request.artist}. To get real Last.fm data, configure an API key."
                enrichment.artist_tags = ["alternative", "rock", "indie", "experimental"]
                enrichment.similar_artists = [
                    {"name": f"Artist Similar to {request.artist[:10]}", "match": 0.85},
                    {"name": f"Related Band {hash(request.artist) % 100}", "match": 0.72},
                    {"name": "Inspired Artist", "match": 0.68},
                ]
                enrichment.scrobble_count = hash(request.artist) % 1000000

            return enrichment

        except Exception as e:
            self.logger.error("Last.fm enrichment failed: %s", e)
            enrichment = EnrichmentData()
            enrichment.service_errors["lastfm"] = str(e)
            return enrichment
