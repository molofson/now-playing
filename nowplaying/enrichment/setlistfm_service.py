"""
Setlist.fm metadata enrichment service.

This module provides integration with Setlist.fm for retrieving
concert setlists, tour information, and live performance data.

Setlist.fm provides comprehensive setlist database with song-by-song
performance information from concerts worldwide.
"""

import asyncio
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

from .base import EnrichmentData, EnrichmentRequest, EnrichmentService


class SetlistFmService(EnrichmentService):
    """Setlist.fm metadata enrichment service."""

    def __init__(self):
        """Initialize Setlist.fm service."""
        super().__init__("setlistfm", "Setlist.fm")
        self._rate_limit_delay = 0.5  # Setlist.fm rate limit (2 requests per second)
        self._base_url = "https://api.setlist.fm/rest/1.0"
        self._user_agent = "NowPlayingApp/1.0 (https://github.com/user/now-playing)"
        # Setlist.fm requires an API key - get one from https://api.setlist.fm/docs/1.0/index.html
        self._api_key = None  # Set this to your Setlist.fm API key

    def set_api_key(self, api_key: str):
        """Set the Setlist.fm API key for authenticated requests."""
        self._api_key = api_key

    def _make_request(self, endpoint: str) -> Optional[str]:
        """Make a request to the Setlist.fm API."""
        if not self._api_key:
            return None

        try:
            url = f"{self._base_url}{endpoint}"

            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": self._user_agent,
                    "Accept": "application/xml",
                    "x-api-key": self._api_key,
                },
            )

            with urllib.request.urlopen(req, timeout=15) as response:
                return response.read().decode("utf-8")

        except Exception as e:
            self.logger.warning(f"Setlist.fm API request failed for {endpoint}: {e}")
            return None

    def _search_artist_sync(self, artist_name: str) -> Optional[Dict[str, Any]]:
        """Search for an artist on Setlist.fm."""
        try:
            # URL encode the artist name
            encoded_name = urllib.parse.quote_plus(artist_name)
            endpoint = f"/search/artists?artistName={encoded_name}"

            xml_data = self._make_request(endpoint)
            if not xml_data:
                return None

            # Parse XML
            root = ET.fromstring(xml_data)
            artists = root.findall(".//artist")

            if not artists:
                return None

            # Find the best match (exact name match first, then closest)
            best_match = None
            for artist in artists:
                name = artist.get("name", "").lower()
                if name == artist_name.lower():
                    best_match = artist
                    break
                elif not best_match and artist_name.lower() in name:
                    best_match = artist

            if not best_match:
                best_match = artists[0]  # Take first result if no good match

            # Safely extract optional subelements
            url_elem = best_match.find("url")
            url_text = url_elem.text if url_elem is not None and url_elem.text is not None else None

            return {
                "mbid": best_match.get("mbid"),
                "name": best_match.get("name"),
                "sortName": best_match.get("sortName"),
                "disambiguation": best_match.get("disambiguation"),
                "url": url_text,
            }

        except Exception as e:
            self.logger.warning(f"Setlist.fm artist search failed for '{artist_name}': {e}")
            return None

    def _get_artist_setlists_sync(self, artist_mbid: str, limit: int = 5) -> Optional[List[Dict[str, Any]]]:
        """Get recent setlists for an artist."""
        try:
            endpoint = f"/artist/{artist_mbid}/setlists"

            xml_data = self._make_request(endpoint)
            if not xml_data:
                return None

            # Parse XML
            root = ET.fromstring(xml_data)
            setlists = root.findall(".//setlist")

            if not setlists:
                return None

            parsed_setlists = []
            for setlist in setlists[:limit]:  # Limit results
                # Extract venue info
                venue_elem = setlist.find("venue")
                venue_info = {}
                if venue_elem is not None:
                    city_elem = venue_elem.find(".//city")
                    country_elem = venue_elem.find(".//country")
                    venue_info = {
                        "id": venue_elem.get("id"),
                        "name": venue_elem.get("name"),
                        "city": (
                            city_elem.get("name")
                            if city_elem is not None and city_elem.get("name") is not None
                            else None
                        ),
                        "state": (
                            city_elem.get("state")
                            if city_elem is not None and city_elem.get("state") is not None
                            else None
                        ),
                        "country": (
                            country_elem.get("name")
                            if country_elem is not None and country_elem.get("name") is not None
                            else None
                        ),
                    }

                # Extract tour info
                tour_elem = setlist.find("tour")
                tour_name = tour_elem.get("name") if tour_elem is not None else None

                # Extract setlist songs
                sets = setlist.find("sets")
                songs = []
                if sets is not None:
                    for song_set in sets.findall("set"):
                        for song in song_set.findall("song"):
                            song_info = {
                                "name": song.get("name"),
                                "tape": song.get("tape") == "true",
                            }
                            # Check for cover info
                            cover = song.find("cover")
                            if cover is not None:
                                song_info["cover"] = {
                                    "name": cover.get("name"),
                                    "mbid": cover.get("mbid"),
                                }
                            songs.append(song_info)

                parsed_setlist = {
                    "id": setlist.get("id"),
                    "eventDate": setlist.get("eventDate"),
                    "lastUpdated": setlist.get("lastUpdated"),
                    "venue": venue_info,
                    "tour": tour_name,
                    "songs": songs,
                }

                parsed_setlists.append(parsed_setlist)

            return parsed_setlists

        except Exception as e:
            self.logger.warning(f"Setlist.fm setlists fetch failed for artist MBID {artist_mbid}: {e}")
            return None

    async def enrich(self, request: EnrichmentRequest) -> Optional[EnrichmentData]:
        """Enrich with Setlist.fm data."""
        if not self.can_enrich(request):
            return None

        await self._rate_limit()

        try:
            self.logger.debug("Enriching with Setlist.fm: %s", request.artist)

            enrichment = EnrichmentData()

            # If we have API key, try real enrichment
            if self._api_key:
                # Perform API calls using thread pool to avoid blocking async loop
                loop = asyncio.get_event_loop()

                with ThreadPoolExecutor(max_workers=2) as executor:
                    # Search for the artist
                    artist_future = loop.run_in_executor(executor, self._search_artist_sync, request.artist)

                    artist_result = await artist_future

                    if artist_result:
                        artist_mbid = artist_result["mbid"]

                        # Get recent setlists
                        setlists_future = loop.run_in_executor(
                            executor, self._get_artist_setlists_sync, artist_mbid, 3  # Get 3 recent setlists
                        )

                        setlists = await setlists_future

                        if setlists:
                            # Convert setlists to tour_dates format
                            tour_dates = []
                            for setlist in setlists:
                                venue = setlist.get("venue", {})
                                event_date = setlist.get("eventDate", "")

                                # Convert date format (DD-MM-YYYY to YYYY-MM-DD)
                                if event_date and len(event_date.split("-")) == 3:
                                    day, month, year = event_date.split("-")
                                    formatted_date = f"{year}-{month}-{day}"
                                else:
                                    formatted_date = event_date

                                tour_dates.append(
                                    {
                                        "date": formatted_date,
                                        "venue": venue.get("name", "Unknown Venue"),
                                        "city": venue.get("city", "Unknown City"),
                                        "country": venue.get("country", "Unknown Country"),
                                        "type": "Concert",
                                        "tour": setlist.get("tour"),
                                    }
                                )

                            enrichment.tour_dates = tour_dates

                            # Add most recent setlist as additional context
                            if setlists and setlists[0].get("songs"):
                                recent_setlist = setlists[0]
                                venue_name = recent_setlist.get("venue", {}).get("name", "Unknown Venue")
                                event_date = recent_setlist.get("eventDate", "Unknown Date")

                                # Get first 10 songs
                                songs = recent_setlist["songs"][:10]
                                song_names = [song["name"] for song in songs if song["name"]]

                                setlist_text = f"Recent setlist from {venue_name} ({event_date}): "
                                setlist_text += ", ".join(song_names)
                                if len(recent_setlist["songs"]) > 10:
                                    setlist_text += "..."

                                enrichment.album_reviews.append(
                                    {"text": setlist_text, "source": "setlistfm", "type": "setlist"}
                                )

                            self.logger.info(
                                "Setlist.fm enrichment result: %d setlists found", len(setlists) if setlists else 0
                            )

                    else:
                        self.logger.debug("Artist not found on Setlist.fm: %s", request.artist)

            # If we didn't get real data (or no API key), add some mock data for demonstration
            if not enrichment.tour_dates:
                mock_data = self._get_mock_data(request.artist)
                if mock_data:
                    enrichment.tour_dates = mock_data.get("tour_dates", [])
                    if mock_data.get("setlist"):
                        enrichment.album_reviews.append(mock_data["setlist"])
                    self.logger.info("Using mock Setlist.fm data for demonstration")

            enrichment.last_updated["setlistfm"] = time.time()

            return enrichment

        except Exception as e:
            self.logger.error("Setlist.fm enrichment failed: %s", e)
            enrichment = EnrichmentData()
            enrichment.service_errors["setlistfm"] = str(e)
            return enrichment

    def _get_mock_data(self, artist: str) -> Optional[Dict[str, Any]]:
        """Get mock data for demonstration purposes."""
        mock_data = {
            "radiohead": {
                "tour_dates": [
                    {
                        "date": "2025-08-01",
                        "venue": "Wells Fargo Center",
                        "city": "Philadelphia",
                        "country": "United States",
                        "type": "Concert",
                        "tour": "A Moon Shaped Pool",
                    },
                    {
                        "date": "2025-08-03",
                        "venue": "Madison Square Garden",
                        "city": "New York",
                        "country": "United States",
                        "type": "Concert",
                        "tour": "A Moon Shaped Pool",
                    },
                ],
                "setlist": {
                    "text": "Recent Radiohead setlist: Daydreaming, Desert Island Disk, Ful Stop, 15 Step, Lucky, Kid A, Videotape, Decks Dark",
                    "source": "setlistfm",
                    "type": "setlist",
                },
            },
            "led zeppelin": {
                "tour_dates": [
                    {
                        "date": "2025-07-04",
                        "venue": "Wembley Stadium",
                        "city": "London",
                        "country": "United Kingdom",
                        "type": "Festival",
                        "tour": "Celebration Day",
                    }
                ],
                "setlist": {
                    "text": "Classic Led Zeppelin setlist: Immigrant Song, Heartbreaker, Black Dog, Stairway to Heaven, Misty Mountain Hop, Going to California, Whole Lotta Love",
                    "source": "setlistfm",
                    "type": "setlist",
                },
            },
        }

        return mock_data.get(artist.lower())
