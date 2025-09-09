"""
Tests for MusicBrainz enrichment service.
"""

import asyncio
import json
import os
import sys
import time
import unittest.mock
from unittest.mock import Mock, patch

import pytest

# Add the project root to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from nowplaying.enrichment import EnrichmentData, EnrichmentRequest, MusicBrainzService  # noqa: E402
from nowplaying.music_views import ContentContext  # noqa: E402


class TestMusicBrainzService:
    """Test cases for MusicBrainz enrichment service."""

    @pytest.fixture
    def service(self):
        """Create MusicBrainz service instance."""
        return MusicBrainzService()

    @pytest.fixture
    def sample_request(self):
        """Create sample enrichment request."""
        context = Mock(spec=ContentContext)
        return EnrichmentRequest(artist="The Beatles", album="Abbey Road", title="Come Together", context=context)

    @pytest.fixture
    def mock_artist_response(self):
        """Mock MusicBrainz artist search response."""
        return {
            "artists": [
                {
                    "id": "12345-67890-abcdef",
                    "name": "The Beatles",
                    "sort-name": "Beatles, The",
                    "type": "Group",
                    "country": "GB",
                    "life-span": {"begin": "1960", "end": "1970"},
                    "score": 100,
                }
            ]
        }

    @pytest.fixture
    def mock_release_response(self):
        """Mock MusicBrainz release search response."""
        return {
            "releases": [
                {
                    "id": "release-12345",
                    "title": "Abbey Road",
                    "status": "Official",
                    "date": "1969-09-26",
                    "country": "GB",
                    "packaging": "Jewel Case",
                    "artist-credit": [{"artist": {"id": "12345-67890-abcdef", "name": "The Beatles"}}],
                    "score": 100,
                }
            ]
        }

    @pytest.fixture
    def mock_recording_response(self):
        """Mock MusicBrainz recording search response."""
        return {
            "recordings": [
                {
                    "id": "recording-12345",
                    "title": "Come Together",
                    "length": 259000,
                    "artist-credit": [{"artist": {"id": "12345-67890-abcdef", "name": "The Beatles"}}],
                    "releases": [{"id": "release-12345"}],
                    "score": 100,
                }
            ]
        }

    def test_service_initialization(self, service):
        """Test service initialization."""
        assert service.service_id == "musicbrainz"
        assert service.service_name == "MusicBrainz"
        assert service.enabled is True
        assert service._rate_limit_delay == 1.0
        assert service._base_url == "https://musicbrainz.org/ws/2"
        assert "NowPlayingApp" in service._user_agent

    @pytest.mark.asyncio
    async def test_search_artist_success(self, service, mock_artist_response):
        """Test successful artist search."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = Mock()
            mock_response.read.return_value = json.dumps(mock_artist_response).encode("utf-8")
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=None)
            mock_urlopen.return_value = mock_response

            result = await service._search_artist("The Beatles")

            assert result is not None
            assert result["id"] == "12345-67890-abcdef"
            assert result["name"] == "The Beatles"
            assert result["type"] == "Group"
            assert result["country"] == "GB"
            assert result["score"] == 100

    @pytest.mark.asyncio
    async def test_search_artist_no_results(self, service):
        """Test artist search with no results."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = Mock()
            mock_response.read.return_value = json.dumps({"artists": []}).encode("utf-8")
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=None)
            mock_urlopen.return_value = mock_response

            result = await service._search_artist("Unknown Artist")
            assert result is None

    @pytest.mark.asyncio
    async def test_search_artist_network_error(self, service):
        """Test artist search with network error."""
        with patch("urllib.request.urlopen", side_effect=Exception("Network error")):
            result = await service._search_artist("The Beatles")
            assert result is None

    @pytest.mark.asyncio
    async def test_search_release_success(self, service, mock_release_response):
        """Test successful release search."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = Mock()
            mock_response.read.return_value = json.dumps(mock_release_response).encode("utf-8")
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=None)
            mock_urlopen.return_value = mock_response

            result = await service._search_release("The Beatles", "Abbey Road")

            assert result is not None
            assert result["id"] == "release-12345"
            assert result["title"] == "Abbey Road"
            assert result["status"] == "Official"
            assert result["date"] == "1969-09-26"

    @pytest.mark.asyncio
    async def test_search_recording_success(self, service, mock_recording_response):
        """Test successful recording search."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = Mock()
            mock_response.read.return_value = json.dumps(mock_recording_response).encode("utf-8")
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=None)
            mock_urlopen.return_value = mock_response

            result = await service._search_recording("The Beatles", "Come Together")

            assert result is not None
            assert result["id"] == "recording-12345"
            assert result["title"] == "Come Together"
            assert result["length"] == 259000

    @pytest.mark.asyncio
    async def test_enrich_full_metadata(
        self, service, sample_request, mock_artist_response, mock_release_response, mock_recording_response
    ):
        """Test enrichment with full metadata available."""
        # Mock all three API calls
        def mock_urlopen_side_effect(request, timeout=None):  # noqa: U100
            url = request.get_full_url()
            mock_response = Mock()
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=None)

            if "/artist/" in url:
                mock_response.read.return_value = json.dumps(mock_artist_response).encode("utf-8")
            elif "/release/" in url:
                mock_response.read.return_value = json.dumps(mock_release_response).encode("utf-8")
            elif "/recording/" in url:
                mock_response.read.return_value = json.dumps(mock_recording_response).encode("utf-8")
            else:
                mock_response.read.return_value = json.dumps({}).encode("utf-8")

            return mock_response

        with patch("urllib.request.urlopen", side_effect=mock_urlopen_side_effect):

            async def mock_rate_limit():
                pass

            with patch.object(service, "_rate_limit", side_effect=mock_rate_limit):
                result = await service.enrich(sample_request)

                assert result is not None
                assert result.musicbrainz_artist_id == "12345-67890-abcdef"
                assert result.musicbrainz_album_id == "release-12345"
                assert result.musicbrainz_track_id == "recording-12345"

                # Check artist tags
                assert "type:group" in result.artist_tags
                assert "country:GB" in result.artist_tags

                # Check album credits
                assert len(result.album_credits) > 0
                credit = result.album_credits[0]
                assert credit["role"] == "artist"
                assert credit["artist"] == "The Beatles"
                assert credit["musicbrainz_id"] == "12345-67890-abcdef"

                # Check timestamp
                assert "musicbrainz" in result.last_updated
                assert result.last_updated["musicbrainz"] > 0

    @pytest.mark.asyncio
    async def test_enrich_partial_metadata(self, service):
        """Test enrichment with only artist available."""
        # Create request with only artist
        context = Mock(spec=ContentContext)
        request = EnrichmentRequest(artist="The Beatles", album="", title="", context=context)

        mock_artist_response = {
            "artists": [{"id": "12345-67890-abcdef", "name": "The Beatles", "type": "Group", "score": 100}]
        }

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = Mock()
            mock_response.read.return_value = json.dumps(mock_artist_response).encode("utf-8")
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=None)
            mock_urlopen.return_value = mock_response

            async def mock_rate_limit():
                pass

            with patch.object(service, "_rate_limit", side_effect=mock_rate_limit):
                result = await service.enrich(request)

                assert result is not None
                assert result.musicbrainz_artist_id == "12345-67890-abcdef"
                assert result.musicbrainz_album_id is None
                assert result.musicbrainz_track_id is None

    @pytest.mark.asyncio
    async def test_enrich_service_disabled(self, service, sample_request):
        """Test enrichment when service is disabled."""
        service.enabled = False

        result = await service.enrich(sample_request)
        assert result is None

    @pytest.mark.asyncio
    async def test_enrich_network_error(self, service, sample_request):
        """Test enrichment with network errors."""
        with patch("urllib.request.urlopen", side_effect=Exception("Network error")):

            async def mock_rate_limit():
                pass

            with patch.object(service, "_rate_limit", side_effect=mock_rate_limit):
                result = await service.enrich(sample_request)

                assert result is not None
                # When individual searches fail due to network errors,
                # we get an enrichment with no data rather than a service error
                assert result.musicbrainz_artist_id is None
                assert result.musicbrainz_album_id is None
                assert result.musicbrainz_track_id is None
                assert "musicbrainz" in result.last_updated  # Service ran but got no data

    @pytest.mark.asyncio
    async def test_enrich_service_level_error(self, service, sample_request):
        """Test enrichment with service-level errors."""
        # Mock an error at the service level (not individual search level)
        async def mock_rate_limit():
            pass

        with (
            patch.object(service, "_rate_limit", side_effect=mock_rate_limit),
            patch.object(service, "_search_artist_sync", side_effect=RuntimeError("Service unavailable")),
        ):
            result = await service.enrich(sample_request)

            assert result is not None
            assert "musicbrainz" in result.service_errors
            assert "Service unavailable" in result.service_errors["musicbrainz"]

    @pytest.mark.asyncio
    async def test_rate_limiting(self, service):
        """Test rate limiting functionality."""
        # First call should not be delayed
        await service._rate_limit()
        first_call_time = time.time()

        # Second call should be delayed
        await service._rate_limit()
        second_call_time = time.time()

        # Should be at least 1 second between calls
        assert (second_call_time - first_call_time) >= service._rate_limit_delay

    def test_user_agent_format(self, service):
        """Test user agent string format."""
        user_agent = service._user_agent
        assert "NowPlayingApp" in user_agent
        assert "/" in user_agent
        assert "http" in user_agent

    @pytest.mark.asyncio
    async def test_url_encoding(self, service):
        """Test proper URL encoding of search queries."""
        artist_name = "AC/DC & Friends"

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = Mock()
            mock_response.read.return_value = json.dumps({"artists": []}).encode("utf-8")
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=None)
            mock_urlopen.return_value = mock_response

            await service._search_artist(artist_name)

            # Check that the URL was properly encoded
            call_args = mock_urlopen.call_args[0][0]
            url = call_args.get_full_url()
            assert "AC%2FDC" in url  # Forward slash should be encoded
            assert "%26" in url  # Ampersand should be encoded

    @pytest.mark.asyncio
    async def test_json_parsing_error(self, service):
        """Test handling of malformed JSON responses."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = Mock()
            mock_response.read.return_value = b"Invalid JSON {"
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=None)
            mock_urlopen.return_value = mock_response

            result = await service._search_artist("The Beatles")
            assert result is None

    @pytest.mark.asyncio
    async def test_timeout_handling(self, service):
        """Test timeout handling in API calls."""
        with patch("urllib.request.urlopen", side_effect=TimeoutError("Request timeout")):
            result = await service._search_artist("The Beatles")
            assert result is None
