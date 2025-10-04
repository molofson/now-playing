"""
MCP Server for Music Information Enrichment.

This module provides an MCP server that exposes music enrichment tools
using the existing enrichment engine from the now-playing application.
"""

import json

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.shared.exceptions import McpError
from mcp.types import EmbeddedResource, ImageContent, TextContent, Tool
from pydantic import BaseModel

from .enrichment.base import ContentContext, EnrichmentRequest
from .enrichment.engine import enrichment_engine


class MusicEnrichmentInput(BaseModel):
    """Input for music enrichment tool."""

    artist: str
    album: str = ""
    title: str = ""


class MusicEnrichmentResult(BaseModel):
    """Result from music enrichment."""

    artist: str
    album: str
    title: str
    enrichment_data: dict


class MusicInfoServer:
    """MCP server for music information."""

    def __init__(self):
        """Initialize the MCP server."""
        self.server = Server("music-info-server")

    async def enrich_music(self, artist: str, album: str = "", title: str = "") -> MusicEnrichmentResult:
        """Enrich music metadata for the given track."""
        # Create enrichment request
        context = ContentContext(source="mcp")
        request = EnrichmentRequest(artist=artist, album=album, title=title, context=context)

        # Get enrichment data
        enrichment_data = await enrichment_engine.enrich_async(request)

        # Convert to dict for JSON serialization
        enrichment_dict = {
            "musicbrainz_artist_id": enrichment_data.musicbrainz_artist_id,
            "musicbrainz_album_id": enrichment_data.musicbrainz_album_id,
            "musicbrainz_track_id": enrichment_data.musicbrainz_track_id,
            "discogs_artist_id": enrichment_data.discogs_artist_id,
            "discogs_release_id": enrichment_data.discogs_release_id,
            "spotify_artist_id": enrichment_data.spotify_artist_id,
            "spotify_album_id": enrichment_data.spotify_album_id,
            "artist_bio": enrichment_data.artist_bio,
            "artist_tags": enrichment_data.artist_tags,
            "similar_artists": enrichment_data.similar_artists,
            "album_reviews": enrichment_data.album_reviews,
            "album_credits": enrichment_data.album_credits,
            "tour_dates": enrichment_data.tour_dates,
            "recent_releases": enrichment_data.recent_releases,
            "artist_discography": enrichment_data.artist_discography,
            "scrobble_count": enrichment_data.scrobble_count,
            "popularity_score": enrichment_data.popularity_score,
            "user_tags": enrichment_data.user_tags,
            "last_updated": dict(enrichment_data.last_updated),
            "service_errors": dict(enrichment_data.service_errors),
        }

        return MusicEnrichmentResult(artist=artist, album=album, title=title, enrichment_data=enrichment_dict)

    async def serve(self) -> None:
        """Run the MCP server."""

        @self.server.list_tools()
        async def handle_list_tools() -> list[Tool]:
            """List available tools."""
            return [
                Tool(
                    name="enrich_music",
                    description="Enrich music metadata by fetching additional information from various music databases and services",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "artist": {"type": "string", "description": "The artist name"},
                            "album": {"type": "string", "description": "The album name (optional)"},
                            "title": {"type": "string", "description": "The track title (optional)"},
                        },
                        "required": ["artist"],
                    },
                )
            ]

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict) -> list[TextContent | ImageContent | EmbeddedResource]:
            """Handle tool calls."""
            if name == "enrich_music":
                try:
                    # Validate input
                    input_data = MusicEnrichmentInput(**arguments)

                    # Call enrichment
                    result = await self.enrich_music(
                        artist=input_data.artist, album=input_data.album, title=input_data.title
                    )

                    # Return result as JSON
                    return [TextContent(type="text", text=json.dumps(result.model_dump(), indent=2))]

                except Exception as e:
                    raise McpError(f"Failed to enrich music data: {str(e)}")
            else:
                raise McpError(f"Unknown tool: {name}")

        # Run the server
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(read_stream, write_stream, self.server.create_initialization_options())


# Global server instance
music_info_server = MusicInfoServer()


async def serve_mcp():
    """Entry point for running the MCP server."""
    await music_info_server.serve()
