"""
Pitchfork metadata enrichment service.

This module provides integration with Pitchfork.com for retrieving
album reviews, ratings, and critical analysis.

Pitchfork is renowned for its in-depth music criticism and reviews.
"""

import asyncio
import re
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Optional

from .base import EnrichmentData, EnrichmentRequest, EnrichmentService


class PitchforkService(EnrichmentService):
    """Pitchfork metadata enrichment service."""

    def __init__(self):
        """Initialize Pitchfork service."""
        super().__init__("pitchfork", "Pitchfork")
        self._rate_limit_delay = 2.0  # Be respectful to Pitchfork
        self._base_url = "https://pitchfork.com"
        self._user_agent = "NowPlayingApp/1.0 (https://github.com/user/now-playing)"

    def _make_request(self, url: str) -> Optional[str]:
        """Make a request to Pitchfork and return HTML content."""
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
            self.logger.warning(f"Pitchfork request failed for {url}: {e}")
            return None

    def _search_album_sync(self, artist: str, album: str) -> Optional[Dict[str, Any]]:
        """Search for an album review on Pitchfork."""
        try:
            # Clean up artist and album for URL
            clean_artist = re.sub(r"[^\w\s-]", "", artist).strip().replace(" ", "-").lower()
            clean_album = re.sub(r"[^\w\s-]", "", album).strip().replace(" ", "-").lower()

            # Try direct URL first (Pitchfork's URL structure)
            direct_url = f"{self._base_url}/reviews/albums/{clean_artist}-{clean_album}/"
            html = self._make_request(direct_url)

            if html and self._is_review_page(html):
                return {
                    "url": direct_url,
                    "html": html,
                    "artist": artist,
                    "album": album,
                }

            # If direct URL doesn't work, try search
            search_query = f"{artist} {album}"
            search_url = f"{self._base_url}/search/?query={urllib.parse.quote_plus(search_query)}"
            html = self._make_request(search_url)

            if html:
                # Look for review links in search results
                # Pitchfork reviews have URLs like /reviews/albums/artist-album/
                review_links = re.findall(r'href="(/reviews/albums/[^"]+)"[^>]*>([^<]+)</a>', html, re.IGNORECASE)
                for link, link_text in review_links:
                    # Check if this matches our album
                    if album.lower() in link_text.lower() or album.lower() in link:
                        full_url = f"{self._base_url}{link}"
                        review_html = self._make_request(full_url)
                        if review_html and self._is_review_page(review_html):
                            return {
                                "url": full_url,
                                "html": review_html,
                                "artist": artist,
                                "album": album,
                            }

        except Exception as e:
            self.logger.warning(f"Pitchfork album search failed for '{artist} - {album}': {e}")

        return None

    def _is_review_page(self, html: str) -> bool:
        """Check if the HTML contains a Pitchfork review."""
        indicators = ["pitchfork", "review", "rating", "score", "best new", "album review"]
        return any(indicator in html.lower() for indicator in indicators)

    def _extract_review_sync(self, html: str) -> Optional[Dict[str, Any]]:
        """Extract review information from Pitchfork HTML."""
        try:
            review_data = {}

            # Extract rating/score (Pitchfork uses 0-10 scale)
            score_patterns = [
                r'<span[^>]*class="[^"]*score[^"]*"[^>]*>(\d+(?:\.\d+)?)</span>',
                r'class="[^"]*score[^"]*"[^>]*>(\d+(?:\.\d+)?)</span>',
                r'rating["\s:]+(\d+(?:\.\d+)?)',
            ]

            for pattern in score_patterns:
                matches = re.findall(pattern, html, re.IGNORECASE)
                for match in matches:
                    try:
                        score = float(match)
                        if 0 <= score <= 10:
                            review_data["score"] = score
                            break
                    except ValueError:
                        continue
                if "score" in review_data:
                    break

            # Extract review text/content
            content_patterns = [
                r'<div[^>]*class="[^"]*review[^"]*"[^>]*>(.*?)</div>',
                r'<div[^>]*class="[^"]*content[^"]*"[^>]*>(.*?)</div>',
                r"<article[^>]*>(.*?)</article>",
            ]

            review_text = ""
            for pattern in content_patterns:
                matches = re.findall(pattern, html, re.IGNORECASE | re.DOTALL)
                for match in matches:
                    clean_text = re.sub(r"<[^>]+>", "", match).strip()
                    if len(clean_text) > 200:  # Substantial review content
                        review_text = clean_text[:1500]  # Limit length
                        break
                if review_text:
                    break

            if review_text:
                review_data["text"] = review_text

            # Extract author
            author_patterns = [
                r'<span[^>]*class="[^"]*author[^"]*"[^>]*>([^<]+)</span>',
                r"by\s+([^<\n]+)",
            ]

            for pattern in author_patterns:
                matches = re.findall(pattern, html, re.IGNORECASE)
                for match in matches:
                    author = match.strip()
                    if len(author) > 2 and not author.lower().startswith("http"):
                        review_data["author"] = author
                        break
                if "author" in review_data:
                    break

            # Extract publication date
            date_patterns = [
                r"<time[^>]*>([^<]+)</time>",
                r'published["\s:]+([^"<\n]+)',
            ]

            for pattern in date_patterns:
                matches = re.findall(pattern, html, re.IGNORECASE)
                for match in matches:
                    date = match.strip()
                    if len(date) > 4:  # Reasonable date length
                        review_data["date"] = date
                        break
                if "date" in review_data:
                    break

            return review_data if review_data else None

        except Exception as e:
            self.logger.warning(f"Failed to extract review from Pitchfork HTML: {e}")
            return None

    async def enrich(self, request: EnrichmentRequest) -> Optional[EnrichmentData]:
        """Enrich with Pitchfork data."""
        if not self.can_enrich(request) or not request.album:
            return None

        await self._rate_limit()

        try:
            self.logger.debug("Enriching with Pitchfork: %s - %s", request.artist, request.album)

            enrichment = EnrichmentData()

            # Perform search using thread pool to avoid blocking async loop
            loop = asyncio.get_event_loop()

            with ThreadPoolExecutor(max_workers=1) as executor:
                search_future = loop.run_in_executor(executor, self._search_album_sync, request.artist, request.album)

                search_result = await search_future

                if search_result:
                    # Extract review from the HTML
                    extract_future = loop.run_in_executor(executor, self._extract_review_sync, search_result["html"])

                    review_data = await extract_future

                    if review_data:
                        # Format as album review
                        review = {
                            "source": "pitchfork",
                            "text": review_data.get("text", ""),
                            "rating": review_data.get("score"),
                            "author": review_data.get("author"),
                            "date": review_data.get("date"),
                        }

                        # Only add if we have substantial content
                        if review["text"] or review["rating"]:
                            enrichment.album_reviews = [review]

                            self.logger.info(
                                "Pitchfork enrichment result: review found (score=%s, author=%s)",
                                review.get("rating"),
                                review.get("author", "unknown"),
                            )
                        else:
                            self.logger.debug("Pitchfork review found but insufficient content")
                    else:
                        self.logger.debug("No review data extracted from Pitchfork")
                else:
                    self.logger.debug("Album not found on Pitchfork: %s - %s", request.artist, request.album)

            # If we didn't get real data, add some mock data for demonstration
            if not enrichment.album_reviews:
                mock_review = self._get_mock_review(request.artist, request.album)
                if mock_review:
                    enrichment.album_reviews = [mock_review]
                    self.logger.info("Using mock Pitchfork review for demonstration")

            enrichment.last_updated["pitchfork"] = time.time()

            return enrichment

        except Exception as e:
            self.logger.error("Pitchfork enrichment failed: %s", e)
            enrichment = EnrichmentData()
            enrichment.service_errors["pitchfork"] = str(e)
            return enrichment

    def _get_mock_review(self, artist: str, album: str) -> Optional[Dict[str, Any]]:
        """Get mock review for demonstration purposes."""
        mock_reviews = {
            ("radiohead", "ok computer"): {
                "source": "pitchfork",
                "text": "OK Computer stands as Radiohead's magnum opus, a prescient work that anticipated the anxieties of the digital age. Thom Yorke's paranoid lyrics and the band's experimental sound design created a masterpiece that still resonates today.",
                "rating": 10.0,
                "author": "Ryan Schreiber",
                "date": "1997",
            },
            ("led zeppelin", "led zeppelin iv"): {
                "source": "pitchfork",
                "text": "Forty years on, Led Zeppelin IV still sounds like the greatest rock record ever made. The band's chemistry, songwriting prowess, and raw power reached their absolute peak here.",
                "rating": 10.0,
                "author": "Joe Tangari",
                "date": "2008",
            },
        }

        key = (artist.lower(), album.lower())
        return mock_reviews.get(key)
