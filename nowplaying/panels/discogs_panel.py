"""
Discogs enrichment panel implementation.

Displays Discogs enrichment results for the current context.
"""

import pygame

from .base import ContentContext, ContentPanel, PanelInfo
from .enrichment_log_buffer import EnrichmentLogBuffer


class DiscogsPanel(ContentPanel):
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
        """Update the current context for this panel."""
        self._context = context

    def can_display(self, context: ContentContext) -> bool:
        """Check if this panel can display the given context."""
        return context is not None

    def handle_event(self, event: pygame.event.Event) -> bool:  # noqa: U100
        """Handle events (not used)."""
        return False

    def render(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        """Render the Discogs enrichment panel."""
        if not self._context:
            return

        font = pygame.font.Font(None, 24)
        header_font = pygame.font.Font(None, 28)
        
        mid_x = rect.left + rect.width // 2
        y = rect.top + 10
        
        # Draw header
        header_text = header_font.render("Discogs Data", True, (255, 255, 255))
        surface.blit(header_text, (rect.left + 20, y))
        y += 40
        
        enrichment = getattr(self._context, "enrichment_data", None)
        
        if enrichment and hasattr(enrichment, "discogs_artist_id"):
            lines = []
            if enrichment.discogs_artist_id:
                lines.append(f"Artist ID: {enrichment.discogs_artist_id}")
            if enrichment.discogs_release_id:
                lines.append(f"Release ID: {enrichment.discogs_release_id}")
            if enrichment.artist_discography:
                lines.append(f"Discography: {len(enrichment.artist_discography)} releases")
            if enrichment.album_reviews:
                lines.append(f"Reviews: {len(enrichment.album_reviews)} available")
        else:
            lines = ["No Discogs enrichment data available."]
            
        for line in lines:
            text = font.render(line, True, (230, 230, 230))
            surface.blit(text, (rect.left + 20, y))
            y += 30
            # Prevent overflow (only check for real pygame.Rect with numeric bottom)
            try:
                if y > rect.bottom - 40:
                    break
            except (TypeError, AttributeError):
                # Skip overflow check for Mock objects in tests
                pass
        
        # Right: logger output
        log_header = header_font.render("Service Logs", True, (200, 200, 200))
        surface.blit(log_header, (mid_x + 20, rect.top + 10))
        
        log_lines = self.log_buffer.get_lines()[-12:]  # Show last 12 lines
        y_log = rect.top + 50
        for line in log_lines:
            # Prevent overflow (only check for real pygame.Rect with numeric bottom)
            try:
                if y_log > rect.bottom - 30:
                    break
            except (TypeError, AttributeError):
                # Skip overflow check for Mock objects in tests
                pass
            text = font.render(line[:60], True, (180, 180, 180))  # Truncate long lines
            surface.blit(text, (mid_x + 20, y_log))
            y_log += 24
