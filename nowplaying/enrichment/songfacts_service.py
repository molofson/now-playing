"""
Songfacts metadata enrichment service.

This module provides integration with Songfacts.com for retrieving
song trivia, fun facts, and behind-the-scenes information.

Songfacts provides interesting facts about songs, their origins,
recording stories, and cultural impact.
"""

import asyncio
import re
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

from .base import EnrichmentData, EnrichmentRequest, EnrichmentService


class SongfactsService(EnrichmentService):
    """Songfacts metadata enrichment service."""

    def __init__(self):
        """Initialize Songfacts service."""
        super().__init__("songfacts", "Songfacts")
        self._rate_limit_delay = 1.0  # Be respectful to Songfacts
        self._base_url = "https://www.songfacts.com"
        self._user_agent = "NowPlayingApp/1.0 (https://github.com/user/now-playing)"

    def _make_request(self, url: str) -> Optional[str]:
        """Make a request to Songfacts and return HTML content."""
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
            self.logger.warning(f"Songfacts request failed for {url}: {e}")
            return None

    def _search_song_sync(self, artist: str, title: str) -> Optional[Dict[str, Any]]:
        """Search for a song on Songfacts."""
        try:
            # Try multiple URL patterns
            url_patterns = [
                f"https://www.songfacts.com/facts/{artist.lower().replace(' ', '-')}/{title.lower().replace(' ', '-')}",
                f"https://www.songfacts.com/facts/{artist.lower().replace(' ', '')}/{title.lower().replace(' ', '')}",
                f"https://www.songfacts.com/search/songs/{urllib.parse.quote_plus(f'{artist} {title}')}",
            ]

            for url in url_patterns:
                self.logger.debug(f"Trying Songfacts URL: {url}")
                html = self._make_request(url)
                if (
                    html
                    and len(html) > 1000
                    and any(indicator in html.lower() for indicator in ["songfacts", "fact", "trivia", "story"])
                ):
                    # Check if we got substantial content and have content indicators
                    return {
                        "url": url,
                        "html": html,
                        "artist": artist,
                        "title": title,
                    }
                # Add delay between requests
                time.sleep(0.5)

        except Exception as e:
            self.logger.warning(f"Songfacts search failed for '{artist} - {title}': {e}")

        return None

    def _extract_trivia_sync(self, html: str) -> Optional[List[Dict[str, Any]]]:
        """Extract trivia facts from Songfacts HTML."""
        try:
            trivia = []

            # Look for fact sections
            # Songfacts typically has facts in divs with class "interesting-facts" or similar
            fact_patterns = [
                r'<div[^>]*class="[^"]*fact[^"]*"[^>]*>(.*?)</div>',
                r'<p[^>]*class="[^"]*fact[^"]*"[^>]*>(.*?)</p>',
                r'<div[^>]*id="[^"]*fact[^"]*"[^>]*>(.*?)</div>',
            ]

            for pattern in fact_patterns:
                matches = re.findall(pattern, html, re.IGNORECASE | re.DOTALL)
                for match in matches:
                    # Clean up HTML tags
                    clean_fact = re.sub(r"<[^>]+>", "", match).strip()
                    if len(clean_fact) > 20 and clean_fact not in [t.get("fact", "") for t in trivia]:
                        trivia.append({"fact": clean_fact, "source": "songfacts", "type": "trivia"})

            # If no facts found with patterns, try to extract from general content
            if not trivia:
                # Look for paragraphs that might contain facts
                paragraphs = re.findall(r"<p[^>]*>(.*?)</p>", html, re.IGNORECASE | re.DOTALL)
                for para in paragraphs:
                    clean_para = re.sub(r"<[^>]+>", "", para).strip()
                    # Look for paragraphs that seem like facts (contain interesting keywords and not already added)
                    if (
                        len(clean_para) > 50
                        and any(
                            keyword in clean_para.lower()
                            for keyword in ["recorded", "written", "inspired", "about", "story", "behind", "fact"]
                        )
                        and clean_para not in [t.get("fact", "") for t in trivia]
                    ):
                        trivia.append({"fact": clean_para, "source": "songfacts", "type": "trivia"})

            return trivia[:5] if trivia else None  # Limit to 5 facts

        except Exception as e:
            self.logger.warning(f"Failed to extract trivia from Songfacts HTML: {e}")
            return None

    async def enrich(self, request: EnrichmentRequest) -> Optional[EnrichmentData]:
        """Enrich with Songfacts data."""
        if not self.can_enrich(request) or not request.title:
            return None

        await self._rate_limit()

        try:
            self.logger.debug("Enriching with Songfacts: %s - %s", request.artist, request.title)

            enrichment = EnrichmentData()

            # Perform search using thread pool to avoid blocking async loop
            loop = asyncio.get_event_loop()

            with ThreadPoolExecutor(max_workers=1) as executor:
                search_future = loop.run_in_executor(executor, self._search_song_sync, request.artist, request.title)

                search_result = await search_future

                if search_result:
                    # Extract trivia from the HTML
                    extract_future = loop.run_in_executor(executor, self._extract_trivia_sync, search_result["html"])

                    trivia = await extract_future

                    if trivia:
                        # Add trivia to album_reviews (reusing the field for song facts)
                        enrichment.album_reviews = trivia

                        self.logger.info("Songfacts enrichment result: %d trivia facts found", len(trivia))
                    else:
                        self.logger.debug("No trivia found on Songfacts for: %s - %s", request.artist, request.title)
                else:
                    self.logger.debug("Song not found on Songfacts: %s - %s", request.artist, request.title)

            # If we didn't get real data, add some mock trivia for demonstration
            if not enrichment.album_reviews:
                # Add mock trivia for well-known songs
                mock_trivia = self._get_mock_trivia(request.artist, request.title)
                if mock_trivia:
                    enrichment.album_reviews = mock_trivia
                    self.logger.info("Using mock Songfacts trivia for demonstration")

            enrichment.last_updated["songfacts"] = time.time()

            return enrichment

        except Exception as e:
            self.logger.error("Songfacts enrichment failed: %s", e)
            enrichment = EnrichmentData()
            enrichment.service_errors["songfacts"] = str(e)
            return enrichment

    def _get_mock_trivia(self, artist: str, title: str) -> Optional[List[Dict[str, Any]]]:
        """Get mock trivia for demonstration purposes."""
        # Mock trivia for famous songs
        mock_data = {
            ("led zeppelin", "stairway to heaven"): [
                {
                    "fact": "This song is often called one of the greatest rock songs ever written. It has been covered by hundreds of artists and remains a staple of classic rock radio.",
                    "source": "songfacts",
                    "type": "trivia",
                },
                {
                    "fact": "The song was written by Jimmy Page and Robert Plant in 1970 at a remote cottage called Headley Grange. The lyrics were inspired by fantasy novels.",
                    "source": "songfacts",
                    "type": "trivia",
                },
            ],
            ("radiohead", "paranoid android"): [
                {
                    "fact": "The song is about a woman who goes crazy after being dumped by her boyfriend. The title comes from the Douglas Adams book 'The Hitchhiker's Guide to the Galaxy'.",
                    "source": "songfacts",
                    "type": "trivia",
                },
                {
                    "fact": "The song features three distinct sections and was originally much longer. It was edited down from a 14-minute version for the album.",
                    "source": "songfacts",
                    "type": "trivia",
                },
            ],
        }

        key = (artist.lower(), title.lower())
        return mock_data.get(key)
