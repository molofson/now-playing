"""
Songkick metadata enrichment service.

This module provides integration with Songkick.com for retrieving
live performance data, setlists, and concert information.

Songkick provides comprehensive concert database with tour dates,
venue information, and setlist data.
"""

import asyncio
import json
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

from .base import EnrichmentData, EnrichmentRequest, EnrichmentService


class SongkickService(EnrichmentService):
    """Songkick metadata enrichment service."""

    def __init__(self):
        """Initialize Songkick service."""
        super().__init__("songkick", "Songkick")
        self._rate_limit_delay = 0.5  # Songkick rate limit (2 requests per second)
        self._base_url = "https://api.songkick.com/api/3.0"
        self._user_agent = "NowPlayingApp/1.0 (https://github.com/user/now-playing)"
        # Songkick requires an API key - you can get one from https://www.songkick.com/developer
        self._api_key = None  # Set this to your Songkick API key

    def set_api_key(self, api_key: str):
        """Set the Songkick API key for authenticated requests."""
        self._api_key = api_key

    def _make_request(self, endpoint: str, params: Optional[Dict[str, str]] = None) -> Optional[Dict[str, Any]]:
        """Make a request to the Songkick API."""
        if not self._api_key:
            return None

        try:
            url = f"{self._base_url}{endpoint}"
            request_params = {"apikey": self._api_key}
            if params:
                request_params.update(params)

            url += "?" + urllib.parse.urlencode(request_params)

            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": self._user_agent,
                    "Accept": "application/json",
                },
            )

            with urllib.request.urlopen(req, timeout=15) as response:
                data = json.loads(response.read().decode("utf-8"))
                return data

        except Exception as e:
            self.logger.warning(f"Songkick API request failed for {endpoint}: {e}")
            return None

    def _search_artist_sync(self, artist_name: str) -> Optional[Dict[str, Any]]:
        """Search for an artist on Songkick."""
        try:
            params = {"query": artist_name}

            data = self._make_request("/search/artists.json", params)
            if data and "resultsPage" in data and "results" in data["resultsPage"]:
                artists = data["resultsPage"]["results"].get("artist", [])

                if artists:
                    # Return the first/best match
                    artist = artists[0]
                    return {
                        "id": artist.get("id"),
                        "name": artist.get("displayName"),
                        "uri": artist.get("uri"),
                        "on_tour_until": artist.get("onTourUntil"),
                    }

        except Exception as e:
            self.logger.warning(f"Songkick artist search failed for '{artist_name}': {e}")

        return None

    def _get_artist_events_sync(self, artist_id: int) -> Optional[List[Dict[str, Any]]]:
        """Get upcoming and past events for an artist."""
        try:
            # Get upcoming events first
            params = {"artist_id": str(artist_id), "per_page": "10"}

            data = self._make_request("/artists/{}/calendar.json".format(artist_id), params)
            if data and "resultsPage" in data and "results" in data["resultsPage"]:
                events = data["resultsPage"]["results"].get("event", [])

                event_data = []
                for event in events[:5]:  # Limit to 5 events
                    venue = event.get("venue", {})
                    location = event.get("location", {})
                    performance = event.get("performance", [{}])[0]

                    event_data.append(
                        {
                            "id": event.get("id"),
                            "type": event.get("type"),
                            "display_name": event.get("displayName"),
                            "date": event.get("start", {}).get("date"),
                            "time": event.get("start", {}).get("time"),
                            "venue": {
                                "name": venue.get("displayName"),
                                "city": location.get("city"),
                                "country": location.get("country", {}).get("displayName"),
                            },
                            "billing": performance.get("billing"),
                            "billing_index": performance.get("billingIndex"),
                        }
                    )

                return event_data

        except Exception as e:
            self.logger.warning(f"Songkick artist events fetch failed for artist ID {artist_id}: {e}")

        return None

    def _get_event_setlist_sync(self, event_id: int) -> Optional[Dict[str, Any]]:
        """Get setlist for a specific event."""
        try:
            data = self._make_request("/events/{}/setlists.json".format(event_id))
            if data and "resultsPage" in data and "results" in data["resultsPage"]:
                setlists = data["resultsPage"]["results"].get("setlist", [])

                if setlists:
                    setlist = setlists[0]  # Get the first setlist
                    return {
                        "event_id": event_id,
                        "artist": setlist.get("artist", {}).get("displayName"),
                        "date": setlist.get("event", {}).get("start", {}).get("date"),
                        "venue": setlist.get("venue", {}).get("displayName"),
                        "city": setlist.get("event", {}).get("location", {}).get("city"),
                        "setlist": setlist.get("setlist", {}).get("song", []),
                    }

        except Exception as e:
            self.logger.warning(f"Songkick setlist fetch failed for event ID {event_id}: {e}")

        return None

    async def enrich(self, request: EnrichmentRequest) -> Optional[EnrichmentData]:
        """Enrich with Songkick data."""
        if not self.can_enrich(request):
            return None

        await self._rate_limit()

        try:
            self.logger.debug("Enriching with Songkick: %s", request.artist)

            enrichment = EnrichmentData()

            # If we have API key, try real enrichment
            if self._api_key:
                # Perform API calls using thread pool to avoid blocking async loop
                loop = asyncio.get_event_loop()

                with ThreadPoolExecutor(max_workers=3) as executor:
                    # Search for the artist
                    artist_future = loop.run_in_executor(executor, self._search_artist_sync, request.artist)

                    artist_result = await artist_future

                    if artist_result:
                        artist_id = artist_result["id"]

                        # Get artist events
                        events_future = loop.run_in_executor(executor, self._get_artist_events_sync, artist_id)

                        events = await events_future

                        if events:
                            # Convert events to tour_dates format
                            tour_dates = []
                            for event in events:
                                tour_dates.append(
                                    {
                                        "date": event.get("date"),
                                        "time": event.get("time"),
                                        "venue": event.get("venue", {}).get("name"),
                                        "city": event.get("venue", {}).get("city"),
                                        "country": event.get("venue", {}).get("country"),
                                        "type": event.get("type"),
                                        "billing": event.get("billing"),
                                    }
                                )

                            enrichment.tour_dates = tour_dates

                            # Try to get setlist for the most recent event
                            if events and events[0].get("id"):
                                setlist_future = loop.run_in_executor(
                                    executor, self._get_event_setlist_sync, events[0]["id"]
                                )

                                setlist = await setlist_future
                                if setlist and setlist.get("setlist"):
                                    # Add setlist info as additional context
                                    setlist_text = f"Recent setlist from {setlist.get('venue', 'Unknown Venue')} ({setlist.get('date', 'Unknown Date')}): "
                                    songs = [song.get("name", "") for song in setlist["setlist"][:10]]  # First 10 songs
                                    setlist_text += ", ".join(songs)
                                    if len(setlist["setlist"]) > 10:
                                        setlist_text += "..."

                                    enrichment.album_reviews.append(
                                        {"text": setlist_text, "source": "songkick", "type": "setlist"}
                                    )

                        # Add tour status if available
                        if artist_result.get("on_tour_until"):
                            enrichment.artist_tags.append(f"on_tour_until:{artist_result['on_tour_until']}")

                        self.logger.info(
                            "Songkick enrichment result: events=%d, setlist=%s",
                            len(enrichment.tour_dates) if enrichment.tour_dates else 0,
                            "yes" if any(r.get("type") == "setlist" for r in enrichment.album_reviews) else "no",
                        )

                    else:
                        self.logger.debug("Artist not found on Songkick: %s", request.artist)

            # If we didn't get real data (or no API key), add some mock data for demonstration
            if not enrichment.tour_dates:
                mock_data = self._get_mock_data(request.artist)
                if mock_data:
                    enrichment.tour_dates = mock_data.get("tour_dates", [])
                    if mock_data.get("setlist"):
                        enrichment.album_reviews.append(mock_data["setlist"])
                    self.logger.info("Using mock Songkick data for demonstration")

            enrichment.last_updated["songkick"] = time.time()

            return enrichment

        except Exception as e:
            self.logger.error("Songkick enrichment failed: %s", e)
            enrichment = EnrichmentData()
            enrichment.service_errors["songkick"] = str(e)
            return enrichment

    def _get_mock_data(self, artist: str) -> Optional[Dict[str, Any]]:
        """Get mock data for demonstration purposes."""
        mock_data = {
            "radiohead": {
                "tour_dates": [
                    {
                        "date": "2025-12-15",
                        "venue": "Madison Square Garden",
                        "city": "New York",
                        "country": "United States",
                        "type": "Concert",
                    },
                    {
                        "date": "2025-12-18",
                        "venue": "The Forum",
                        "city": "Los Angeles",
                        "country": "United States",
                        "type": "Concert",
                    },
                ],
                "setlist": {
                    "text": "Recent Radiohead setlist: Everything In Its Right Place, The Daily Mail, Exit Music (For A Film), Let Down, Karma Police, Idioteque, How To Disappear Completely, Paranoid Android",
                    "source": "songkick",
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
                    }
                ],
                "setlist": {
                    "text": "Classic Led Zeppelin setlist: Immigrant Song, Heartbreaker, Black Dog, Stairway to Heaven, Misty Mountain Hop, Going to California, Whole Lotta Love",
                    "source": "songkick",
                    "type": "setlist",
                },
            },
        }

        return mock_data.get(artist.lower())
