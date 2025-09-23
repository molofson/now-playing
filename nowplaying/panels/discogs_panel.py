"""
Discogs enrichment panel implementation.

Displays Discogs enrichment results for the current context.
"""

import pygame

from .base import ContentContext, ContentPanel, PanelInfo
from .enrichment_log_buffer import EnrichmentLogBuffer


class DiscogsPanel(ContentPanel):
    def handle_event(self, event: pygame.event.Event) -> bool:  # noqa: U100
        """Handle events (not used)."""
        return False

    def can_display(self, context: ContentContext) -> bool:
        return context is not None

    """Panel for displaying Discogs enrichment results."""

    def __init__(self):
        """Initialize the DiscogsPanel."""
        super().__init__(
            PanelInfo(
                id="discogs",
                name="Discogs",
                description="Discogs enrichment results",
                icon="💿",
                category="discovery",
            )
        )
        self.log_buffer = EnrichmentLogBuffer("enrichment.discogs")

    def update_context(self, context: ContentContext) -> None:
        self._context = context

    def render(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        if not self._context:
            return
        font = pygame.font.Font(None, 24)
        mid_x = rect.left + rect.width // 2
        y = rect.top + 10
        enrichment = getattr(self._context, "enrichment_data", None)
        if enrichment and hasattr(enrichment, "discogs_artist_id"):
            lines = [
                f"Discogs Artist ID: {enrichment.discogs_artist_id}",
                f"Discogs Release ID: {enrichment.discogs_release_id}",
                f"Artist Discography: {enrichment.artist_discography}",
            ]
        else:
            lines = ["No Discogs enrichment data."]
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
