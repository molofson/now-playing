"""
Last.fm enrichment panel implementation.

Displays Last.fm enrichment results for the current context.
"""

import pygame

from .base import ContentContext, ContentPanel, PanelInfo
from .enrichment_log_buffer import EnrichmentLogBuffer


class LastFmPanel(ContentPanel):
    """Panel for displaying Last.fm enrichment results."""

    def __init__(self):
        """Initialize the LastFmPanel."""
        super().__init__(
            PanelInfo(
                id="lastfm",
                name="Last.fm",
                description="Last.fm enrichment results",
                icon="📻",
                category="discovery",
            )
        )
        self.log_buffer = EnrichmentLogBuffer("enrichment.lastfm")

    def update_context(self, context: ContentContext) -> None:
        """Update panel context."""
        self._context = context

    def render(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        """Render panel content."""
        if not self._context:
            return
        font = pygame.font.Font(None, 24)
        mid_x = rect.left + rect.width // 2
        y = rect.top + 10
        enrichment = getattr(self._context, "enrichment_data", None)
        if enrichment and hasattr(enrichment, "artist_bio"):
            lines = [
                f"Artist Bio: {enrichment.artist_bio}",
                f"Artist Tags: {', '.join(enrichment.artist_tags)}",
                f"Similar Artists: {enrichment.similar_artists}",
                f"Scrobble Count: {enrichment.scrobble_count}",
            ]
        else:
            lines = ["No Last.fm enrichment data."]
        for line in lines:
            text = font.render(line, True, (230, 230, 230))
            surface.blit(text, (rect.left + 20, y))
            y += 30
        log_lines = self.log_buffer.get_lines()[-15:]
        y_log = rect.top + 10
        for line in log_lines:
            text = font.render(line, True, (180, 180, 180))
            surface.blit(text, (mid_x + 20, y_log))
            y_log += 24
