"""
MusicBrainz enrichment panel implementation.

Displays MusicBrainz enrichment results for the current context.
"""

import pygame

from .base import ContentContext, ContentPanel, PanelInfo
from .enrichment_log_buffer import EnrichmentLogBuffer


class MusicBrainzPanel(ContentPanel):
    """Panel for displaying MusicBrainz enrichment results."""

    def __init__(self):
        """Initialize the MusicBrainzPanel."""
        super().__init__(
            PanelInfo(
                id="musicbrainz",
                name="MusicBrainz",
                description="MusicBrainz enrichment results",
                icon="🎼",
                category="discovery",
            )
        )
        self.log_buffer = EnrichmentLogBuffer("enrichment.musicbrainz")

    def update_context(self, context: ContentContext) -> None:
        """Update panel context."""
        self._context = context

    def render(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        """Render panel content."""
        if not self._context:
            return
        font = pygame.font.Font(None, 24)
        # Split panel: left = enrichment, right = logs
        mid_x = rect.left + rect.width // 2
        y = rect.top + 10
        enrichment = getattr(self._context, "enrichment_data", None)
        # Left: enrichment data
        if enrichment and hasattr(enrichment, "musicbrainz_artist_id"):
            lines = [
                f"MusicBrainz Artist ID: {enrichment.musicbrainz_artist_id}",
                f"MusicBrainz Album ID: {enrichment.musicbrainz_album_id}",
                f"MusicBrainz Track ID: {enrichment.musicbrainz_track_id}",
                f"Artist Tags: {', '.join(enrichment.artist_tags)}",
                f"Album Credits: {enrichment.album_credits}",
            ]
        else:
            lines = ["No MusicBrainz enrichment data."]
        for line in lines:
            text = font.render(line, True, (230, 230, 230))
            surface.blit(text, (rect.left + 20, y))
            y += 30
        # Right: logger output
        log_lines = self.log_buffer.get_lines()[-15:]
        y_log = rect.top + 10
        for line in log_lines:
            text = font.render(line, True, (180, 180, 180))
            surface.blit(text, (mid_x + 20, y_log))
            y_log += 24
