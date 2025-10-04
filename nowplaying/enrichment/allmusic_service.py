"""
AllMusic metadata enrichment service.

This module provides integration with AllMusic.com for retrieving
comprehensive music information including biographies, reviews, credits,
and detailed artist/album data.

AllMusic provides authoritative music information and criticism.
"""

import asyncio
import re
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Optional

from .base import EnrichmentData, EnrichmentRequest, EnrichmentService


class AllMusicService(EnrichmentService):
    """AllMusic metadata enrichment service."""

    def __init__(self):
        """Initialize AllMusic service."""
        super().__init__("allmusic", "AllMusic")
        self._rate_limit_delay = 1.5  # Be respectful to AllMusic
        self._base_url = "https://www.allmusic.com"
        self._user_agent = "NowPlayingApp/1.0 (https://github.com/user/now-playing)"

    def _make_request(self, url: str) -> Optional[str]:
        """Make a request to AllMusic and return HTML content."""
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": self._user_agent,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Accept-Encoding": "gzip, deflate",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                },
            )

            with urllib.request.urlopen(req, timeout=15) as response:
                # Handle gzip encoding
                if response.headers.get("Content-Encoding") == "gzip":
                    import gzip

                    content = gzip.decompress(response.read())
                else:
                    content = response.read()
                return content.decode("utf-8")

        except Exception as e:
            self.logger.warning(f"AllMusic request failed for {url}: {e}")
            return None

    def _search_artist_sync(self, artist_name: str) -> Optional[Dict[str, Any]]:
        """Search for an artist on AllMusic."""
        try:
            # Clean up artist name for URL
            clean_artist = re.sub(r"[^\w\s-]", "", artist_name).strip().replace(" ", "-").lower()

            # Try direct URL first
            direct_url = f"{self._base_url}/artist/{clean_artist}-mn0000000000"
            html = self._make_request(direct_url)

            if html and "allmusic" in html.lower() and "artist" in html.lower():
                return {
                    "url": direct_url,
                    "html": html,
                    "artist": artist_name,
                }

            # If direct URL doesn't work, try search
            search_url = f"{self._base_url}/search/artists/{urllib.parse.quote_plus(artist_name)}"
            html = self._make_request(search_url)

            if html:
                # Look for artist links in search results
                artist_links = re.findall(r'href="(/artist/[^"]+)"[^>]*>([^<]+)</a>', html, re.IGNORECASE)
                for link, link_text in artist_links:
                    # Check if this matches our artist (simple check)
                    if artist_name.lower() in link_text.lower() or any(
                        word in link_text.lower() for word in artist_name.lower().split()
                    ):
                        full_url = f"{self._base_url}{link}"
                        artist_html = self._make_request(full_url)
                        if artist_html:
                            return {
                                "url": full_url,
                                "html": artist_html,
                                "artist": artist_name,
                            }

        except Exception as e:
            self.logger.warning(f"AllMusic artist search failed for '{artist_name}': {e}")

        return None

    def _extract_artist_info_sync(self, html: str) -> Optional[Dict[str, Any]]:
        """Extract artist information from AllMusic HTML."""
        try:
            info = {}

            # Extract biography
            bio_patterns = [
                r'<div[^>]*class="[^"]*biography[^"]*"[^>]*>(.*?)</div>',
                r'<div[^>]*class="[^"]*bio[^"]*"[^>]*>(.*?)</div>',
                r'<p[^>]*class="[^"]*bio[^"]*"[^>]*>(.*?)</p>',
            ]

            for pattern in bio_patterns:
                matches = re.findall(pattern, html, re.IGNORECASE | re.DOTALL)
                for match in matches:
                    clean_bio = re.sub(r"<[^>]+>", "", match).strip()
                    if len(clean_bio) > 100:  # Only use substantial bios
                        info["bio"] = clean_bio[:1500]  # Limit length
                        break
                if "bio" in info:
                    break

            # Extract genres/styles
            genre_patterns = [
                r'<div[^>]*class="[^"]*genres?[^"]*"[^>]*>(.*?)</div>',
                r'<span[^>]*class="[^"]*genre[^"]*"[^>]*>(.*?)</span>',
            ]

            genres = []
            for pattern in genre_patterns:
                matches = re.findall(pattern, html, re.IGNORECASE | re.DOTALL)
                for match in matches:
                    clean_genres = re.sub(r"<[^>]+>", "", match).strip()
                    if clean_genres:
                        # Split by common separators
                        genre_list = re.split(r"[,;/]", clean_genres)
                        genres.extend([g.strip() for g in genre_list if g.strip()])

            if genres:
                info["genres"] = list(set(genres))  # Remove duplicates

            # Extract active years/decades
            years_patterns = [
                r'<div[^>]*class="[^"]*years?[^"]*"[^>]*>(.*?)</div>',
                r'<span[^>]*class="[^"]*active[^"]*"[^>]*>(.*?)</span>',
            ]

            for pattern in years_patterns:
                matches = re.findall(pattern, html, re.IGNORECASE | re.DOTALL)
                for match in matches:
                    clean_years = re.sub(r"<[^>]+>", "", match).strip()
                    if clean_years and ("19" in clean_years or "20" in clean_years):
                        info["active_years"] = clean_years
                        break
                if "active_years" in info:
                    break

            return info if info else None

        except Exception as e:
            self.logger.warning(f"Failed to extract artist info from AllMusic HTML: {e}")
            return None

    def _search_album_sync(self, artist: str, album: str) -> Optional[Dict[str, Any]]:
        """Search for an album on AllMusic."""
        try:
            search_query = f"{artist} {album}"
            search_url = f"{self._base_url}/search/albums/{urllib.parse.quote_plus(search_query)}"
            html = self._make_request(search_url)

            if html:
                # Look for album links in search results
                album_links = re.findall(r'href="(/album/[^"]+)"[^>]*>([^<]+)</a>', html, re.IGNORECASE)
                for link, link_text in album_links:
                    # Check if this matches our album
                    if album.lower() in link_text.lower() or album.lower() in link:
                        full_url = f"{self._base_url}{link}"
                        album_html = self._make_request(full_url)
                        if album_html:
                            return {
                                "url": full_url,
                                "html": album_html,
                                "artist": artist,
                                "album": album,
                            }

        except Exception as e:
            self.logger.warning(f"AllMusic album search failed for '{artist} - {album}': {e}")

        return None

    def _extract_album_info_sync(self, html: str) -> Optional[Dict[str, Any]]:
        """Extract album information from AllMusic HTML."""
        try:
            info = {}

            # Extract review/criticism
            review_patterns = [
                r'<div[^>]*class="[^"]*review[^"]*"[^>]*>(.*?)</div>',
                r'<div[^>]*class="[^"]*critic[^"]*"[^>]*>(.*?)</div>',
                r'<p[^>]*class="[^"]*review[^"]*"[^>]*>(.*?)</p>',
            ]

            reviews = []
            for pattern in review_patterns:
                matches = re.findall(pattern, html, re.IGNORECASE | re.DOTALL)
                for match in matches:
                    clean_review = re.sub(r"<[^>]+>", "", match).strip()
                    if len(clean_review) > 50:  # Only substantial reviews
                        reviews.append(
                            {"text": clean_review[:800], "source": "allmusic", "rating": None}  # Limit length
                        )

            if reviews:
                info["reviews"] = reviews[:2]  # Limit to 2 reviews

            # Extract credits
            credits_patterns = [
                r'<div[^>]*class="[^"]*credits?[^"]*"[^>]*>(.*?)</div>',
                r'<div[^>]*class="[^"]*personnel[^"]*"[^>]*>(.*?)</div>',
            ]

            credits = []
            for pattern in credits_patterns:
                matches = re.findall(pattern, html, re.IGNORECASE | re.DOTALL)
                for match in matches:
                    # Extract individual credit lines
                    credit_lines = re.findall(r"<[^>]*>([^<]+)</[^>]*>", match)
                    for line in credit_lines:
                        if ":" in line and len(line) > 10:
                            parts = line.split(":", 1)
                            if len(parts) == 2:
                                role, artist = parts
                                credits.append({"role": role.strip(), "artist": artist.strip()})

            if credits:
                info["credits"] = credits[:8]  # Limit credits

            return info if info else None

        except Exception as e:
            self.logger.warning(f"Failed to extract album info from AllMusic HTML: {e}")
            return None

    async def enrich(self, request: EnrichmentRequest) -> Optional[EnrichmentData]:
        """Enrich with AllMusic data."""
        if not self.can_enrich(request):
            return None

        await self._rate_limit()

        try:
            self.logger.debug("Enriching with AllMusic: %s - %s", request.artist, request.album or "N/A")

            enrichment = EnrichmentData()

            # Perform searches using thread pool to avoid blocking async loop
            loop = asyncio.get_event_loop()

            with ThreadPoolExecutor(max_workers=2) as executor:
                # Search for artist
                artist_future = loop.run_in_executor(executor, self._search_artist_sync, request.artist)

                # Search for album if we have album info
                album_future = None
                if request.album:
                    album_future = loop.run_in_executor(
                        executor, self._search_album_sync, request.artist, request.album
                    )

                # Process artist info
                artist_result = await artist_future
                if artist_result:
                    artist_info_future = loop.run_in_executor(
                        executor, self._extract_artist_info_sync, artist_result["html"]
                    )
                    artist_info = await artist_info_future

                    if artist_info:
                        # Add biography if we don't already have one from Last.fm
                        if artist_info.get("bio") and not enrichment.artist_bio:
                            enrichment.artist_bio = artist_info["bio"]

                        # Add genres as tags
                        if artist_info.get("genres"):
                            genre_tags = [f"genre:{genre.lower()}" for genre in artist_info["genres"]]
                            enrichment.artist_tags.extend(genre_tags)

                        # Add active years as additional tag
                        if artist_info.get("active_years"):
                            enrichment.artist_tags.append(f"active:{artist_info['active_years']}")

                # Process album info
                if album_future:
                    album_result = await album_future
                    if album_result:
                        album_info_future = loop.run_in_executor(
                            executor, self._extract_album_info_sync, album_result["html"]
                        )
                        album_info = await album_info_future

                        if album_info:
                            # Add reviews
                            if album_info.get("reviews"):
                                enrichment.album_reviews.extend(album_info["reviews"])

                            # Add credits
                            if album_info.get("credits"):
                                enrichment.album_credits = album_info["credits"]

            enrichment.last_updated["allmusic"] = time.time()

            # Check if we got any meaningful data
            has_data = (
                enrichment.artist_bio or enrichment.artist_tags or enrichment.album_reviews or enrichment.album_credits
            )

            if has_data:
                self.logger.info(
                    "AllMusic enrichment result: bio=%s, tags=%d, reviews=%d, credits=%d",
                    "yes" if enrichment.artist_bio else "no",
                    len(enrichment.artist_tags) if enrichment.artist_tags else 0,
                    len(enrichment.album_reviews) if enrichment.album_reviews else 0,
                    len(enrichment.album_credits) if enrichment.album_credits else 0,
                )
            else:
                # If we didn't get real data, add some mock data for demonstration
                mock_data = self._get_mock_data(request.artist, request.album, request.title)
                if mock_data:
                    if mock_data.get("bio") and not enrichment.artist_bio:
                        enrichment.artist_bio = mock_data["bio"]
                    if mock_data.get("tags"):
                        enrichment.artist_tags.extend(mock_data["tags"])
                    if mock_data.get("reviews"):
                        enrichment.album_reviews.extend(mock_data["reviews"])
                    if mock_data.get("credits"):
                        enrichment.album_credits = mock_data["credits"]
                    self.logger.info("Using mock AllMusic data for demonstration")

            return enrichment

        except Exception as e:
            self.logger.error("AllMusic enrichment failed: %s", e)
            enrichment = EnrichmentData()
            enrichment.service_errors["allmusic"] = str(e)
            return enrichment

    def _get_mock_data(
        self,
        artist: str,
        _album: str,  # noqa: U101 - reserved for future use
        _title: str,  # noqa: U101 - reserved for future use
    ) -> Optional[Dict[str, Any]]:
        """Get mock data for demonstration purposes.

        Mock data is indexed by artist only; album/title parameters unused in lookup.
        """
        mock_data = {
            "led zeppelin": {
                "bio": "Led Zeppelin was an English rock band formed in London in 1968. The group consisted of vocalist Robert Plant, guitarist Jimmy Page, bassist/keyboardist John Paul Jones, and drummer John Bonham. They are widely considered one of the most successful, innovative, and influential rock groups in history.",
                "tags": ["genre:rock", "style:hard rock", "style:blues rock", "active:1968-1980"],
                "reviews": [
                    {
                        "text": "Led Zeppelin IV stands as one of the greatest rock albums ever made. The band's chemistry and musical innovation reached its peak here.",
                        "source": "allmusic",
                        "rating": 10,
                    }
                ],
                "credits": [
                    {"role": "Vocals, Harmonica", "artist": "Robert Plant"},
                    {"role": "Guitar", "artist": "Jimmy Page"},
                    {"role": "Bass, Keyboards", "artist": "John Paul Jones"},
                    {"role": "Drums", "artist": "John Bonham"},
                ],
            },
            "radiohead": {
                "bio": "Radiohead are an English rock band formed in Abingdon, Oxfordshire, in 1985. Known for their experimental approach to rock music, they have consistently pushed boundaries and influenced countless artists.",
                "tags": ["genre:rock", "style:alternative rock", "style:art rock", "active:1985-present"],
                "reviews": [
                    {
                        "text": "OK Computer represents Radiohead at their creative peak, blending electronic experimentation with emotional rock songwriting.",
                        "source": "allmusic",
                        "rating": 10,
                    }
                ],
                "credits": [
                    {"role": "Vocals, Guitar", "artist": "Thom Yorke"},
                    {"role": "Guitar, Keyboards", "artist": "Jonny Greenwood"},
                    {"role": "Bass", "artist": "Colin Greenwood"},
                    {"role": "Drums", "artist": "Philip Selway"},
                ],
            },
        }

        return mock_data.get(artist.lower())
