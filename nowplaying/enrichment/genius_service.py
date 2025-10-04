"""
Genius metadata enrichment service.

This module provides integration with Genius.com for retrieving
lyrics, annotations, and song explanations.

Genius provides crowd-sourced lyrics with annotations explaining
references, meanings, and cultural context.
"""

import asyncio
import json
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

from .base import EnrichmentData, EnrichmentRequest, EnrichmentService


class GeniusService(EnrichmentService):
    """Genius metadata enrichment service."""

    def __init__(self):
        """Initialize Genius service."""
        super().__init__("genius", "Genius")
        self._rate_limit_delay = 0.5  # Genius rate limit (2 requests per second)
        self._base_url = "https://api.genius.com"
        self._user_agent = "NowPlayingApp/1.0 (https://github.com/user/now-playing)"
        # Genius requires an API key - you can get one from https://genius.com/api-clients
        self._api_key = None  # Set this to your Genius API key

    def set_api_key(self, api_key: str):
        """Set the Genius API key for authenticated requests."""
        self._api_key = api_key

    def _make_request(self, endpoint: str, params: Optional[Dict[str, str]] = None) -> Optional[Dict[str, Any]]:
        """Make a request to the Genius API."""
        if not self._api_key:
            return None

        try:
            url = f"{self._base_url}{endpoint}"
            if params:
                url += "?" + urllib.parse.urlencode(params)

            req = urllib.request.Request(
                url,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "User-Agent": self._user_agent,
                },
            )

            with urllib.request.urlopen(req, timeout=15) as response:
                data = json.loads(response.read().decode("utf-8"))
                return data

        except Exception as e:
            self.logger.warning(f"Genius API request failed for {endpoint}: {e}")
            return None

    def _search_song_sync(self, artist: str, title: str) -> Optional[Dict[str, Any]]:
        """Search for a song on Genius."""
        try:
            query = f"{artist} {title}"
            params = {"q": query}

            data = self._make_request("/search", params)
            if data and "response" in data and "hits" in data["response"]:
                hits = data["response"]["hits"]

                # Find the best match
                for hit in hits:
                    if "result" in hit:
                        result = hit["result"]
                        song_title = result.get("title", "").lower()
                        song_artist = result.get("primary_artist", {}).get("name", "").lower()

                        # Check if this is a good match
                        if title.lower() in song_title and artist.lower() in song_artist:
                            return {
                                "id": result.get("id"),
                                "title": result.get("title"),
                                "artist": result.get("primary_artist", {}).get("name"),
                                "url": result.get("url"),
                                "api_path": result.get("api_path"),
                            }

                # If no exact match, return the first result
                if hits:
                    result = hits[0]["result"]
                    return {
                        "id": result.get("id"),
                        "title": result.get("title"),
                        "artist": result.get("primary_artist", {}).get("name"),
                        "url": result.get("url"),
                        "api_path": result.get("api_path"),
                    }

        except Exception as e:
            self.logger.warning(f"Genius song search failed for '{artist} - {title}': {e}")

        return None

    def _get_song_details_sync(self, song_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed song information from Genius."""
        try:
            data = self._make_request(f"/songs/{song_id}")
            if data and "response" in data and "song" in data["response"]:
                song = data["response"]["song"]
                return {
                    "id": song.get("id"),
                    "title": song.get("title"),
                    "artist": song.get("primary_artist", {}).get("name"),
                    "lyrics": song.get("lyrics", {}).get("plain"),
                    "description": song.get("description", {}).get("plain"),
                    "release_date": song.get("release_date"),
                    "featured_artists": [artist.get("name") for artist in song.get("featured_artists", [])],
                    "producer_artists": [artist.get("name") for artist in song.get("producer_artists", [])],
                    "writer_artists": [artist.get("name") for artist in song.get("writer_artists", [])],
                }

        except Exception as e:
            self.logger.warning(f"Genius song details fetch failed for song ID {song_id}: {e}")

        return None

    def _get_song_annotations_sync(self, song_id: int) -> Optional[List[Dict[str, Any]]]:
        """Get annotations for a song from Genius."""
        try:
            # Get referents (annotations) for the song
            params = {"song_id": str(song_id), "per_page": "10"}
            data = self._make_request("/referents", params)

            if data and "response" in data and "referents" in data["response"]:
                annotations = []
                for referent in data["response"]["referents"][:5]:  # Limit to 5 annotations
                    if referent.get("annotations"):
                        annotation = referent["annotations"][0]
                        annotations.append(
                            {
                                "text": referent.get("fragment", ""),
                                "range": referent.get("range", {}),
                                "explanation": annotation.get("body", {}).get("plain", ""),
                                "author": annotation.get("authors", [{}])[0].get("name", "Anonymous"),
                                "votes": annotation.get("votes_total", 0),
                            }
                        )

                return annotations

        except Exception as e:
            self.logger.warning(f"Genius annotations fetch failed for song ID {song_id}: {e}")

        return None

    async def enrich(self, request: EnrichmentRequest) -> Optional[EnrichmentData]:
        """Enrich with Genius data."""
        if not self.can_enrich(request) or not request.title:
            return None

        await self._rate_limit()

        try:
            self.logger.debug("Enriching with Genius: %s - %s", request.artist, request.title)

            enrichment = EnrichmentData()

            # If we have API key, try real enrichment
            if self._api_key:
                # Perform API calls using thread pool to avoid blocking async loop
                loop = asyncio.get_event_loop()

                with ThreadPoolExecutor(max_workers=3) as executor:
                    # Search for the song
                    search_future = loop.run_in_executor(
                        executor, self._search_song_sync, request.artist, request.title
                    )

                    search_result = await search_future

                    if search_result:
                        song_id = search_result["id"]

                        # Get song details (lyrics, description, credits)
                        details_future = loop.run_in_executor(executor, self._get_song_details_sync, song_id)

                        # Get annotations
                        annotations_future = loop.run_in_executor(executor, self._get_song_annotations_sync, song_id)

                        # Process results
                        song_details = await details_future
                        if song_details:
                            # Add lyrics if available
                            if song_details.get("lyrics"):
                                enrichment.song_lyrics = song_details["lyrics"]

                            # Add description as additional context
                            if song_details.get("description"):
                                # Add to album_reviews as song description
                                enrichment.album_reviews.append(
                                    {"text": song_details["description"], "source": "genius", "type": "description"}
                                )

                            # Add credits information
                            credits = []
                            if song_details.get("featured_artists"):
                                for artist in song_details["featured_artists"]:
                                    credits.append({"role": "Featured Artist", "artist": artist})
                            if song_details.get("producer_artists"):
                                for artist in song_details["producer_artists"]:
                                    credits.append({"role": "Producer", "artist": artist})
                            if song_details.get("writer_artists"):
                                for artist in song_details["writer_artists"]:
                                    credits.append({"role": "Writer", "artist": artist})

                            if credits:
                                enrichment.album_credits.extend(credits)

                        # Process annotations
                        annotations = await annotations_future
                        if annotations:
                            enrichment.song_annotations = annotations

                        self.logger.info(
                            "Genius enrichment result: lyrics=%s, annotations=%d, credits=%d",
                            "yes" if enrichment.song_lyrics else "no",
                            len(enrichment.song_annotations) if enrichment.song_annotations else 0,
                            len(enrichment.album_credits) if enrichment.album_credits else 0,
                        )

                    else:
                        self.logger.debug("Song not found on Genius: %s - %s", request.artist, request.title)

            # If we didn't get real data (or no API key), add mock data for demonstration
            if not enrichment.song_lyrics and not enrichment.song_annotations:
                mock_data = self._get_mock_data(request.artist, request.title)
                if mock_data:
                    if mock_data.get("lyrics"):
                        enrichment.song_lyrics = mock_data["lyrics"]
                    if mock_data.get("annotations"):
                        enrichment.song_annotations = mock_data["annotations"]
                    self.logger.info("Using mock Genius data for demonstration")

            enrichment.last_updated["genius"] = time.time()

            return enrichment

        except Exception as e:
            self.logger.error("Genius enrichment failed: %s", e)
            enrichment = EnrichmentData()
            enrichment.service_errors["genius"] = str(e)
            return enrichment

    def _get_mock_data(self, artist: str, title: str) -> Optional[Dict[str, Any]]:
        """Get mock data for demonstration purposes."""
        mock_data = {
            ("radiohead", "paranoid android"): {
                "lyrics": "[Verse 1]\nPlease could you stop the noise, I'm trying to get some rest\nFrom all the unborn chicken voices in my head\nWhat's that...? (I may be paranoid, but not an android)\nWhat's that...? (I may be paranoid, but not an android)",
                "annotations": [
                    {
                        "text": "unborn chicken voices",
                        "explanation": "Reference to the chaotic, overwhelming thoughts that plague the narrator. The 'chicken' might refer to cowardice or the idea of thoughts that haven't fully formed.",
                        "author": "Genius User",
                        "votes": 42,
                    },
                    {
                        "text": "I may be paranoid, but not an android",
                        "explanation": "The title line that contrasts human paranoia with mechanical detachment. Yorke has said this song is about alienation and the fear of becoming emotionally numb.",
                        "author": "Radiohead Expert",
                        "votes": 156,
                    },
                ],
            },
            ("led zeppelin", "stairway to heaven"): {
                "lyrics": "[Intro]\nThere's a lady who's sure all that glitters is gold\nAnd she's buying a stairway to heaven\nWhen she gets there she knows, if the stores are all closed\nWith a word she can get what she came for",
                "annotations": [
                    {
                        "text": "stairway to heaven",
                        "explanation": "The song's iconic title has been interpreted as both a path to spiritual enlightenment and a critique of materialism. Page and Plant drew from fantasy literature.",
                        "author": "Classic Rock Scholar",
                        "votes": 89,
                    }
                ],
            },
        }

        key = (artist.lower(), title.lower())
        return mock_data.get(key)
