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
            
        font = pygame.font.Font(None, 20)
        font_small = pygame.font.Font(None, 16)
        mid_x = rect.left + rect.width // 2
        y = rect.top + 10
        
        enrichment = getattr(self._context, "enrichment_data", None)
        
        if enrichment and hasattr(enrichment, "discogs_artist_id"):
            lines = [
                f"Artist: {self._context.artist}",
                f"Album: {self._context.album}",
                "",
            ]
            
            # Add IDs if available
            if enrichment.discogs_artist_id:
                lines.append(f"Artist ID: {enrichment.discogs_artist_id}")
            if enrichment.discogs_release_id:
                lines.append(f"Release ID: {enrichment.discogs_release_id}")
            
            # Add discography
            if enrichment.artist_discography:
                lines.append("")
                lines.append("Artist Discography:")
                for release in enrichment.artist_discography[:8]:  # Show up to 8 releases
                    title = release.get("title", "Unknown")
                    year = release.get("year", "????")
                    format_type = release.get("format", "Unknown")
                    lines.append(f"  • {title} ({year}) [{format_type}]")
        else:
            lines = [
                f"Artist: {self._context.artist}",
                f"Album: {self._context.album}",
                "",
                "No Discogs enrichment data available.",
                "",
                "To enable real Discogs data:",
                "Set DISCOGS_TOKEN environment variable"
            ]
        
        # Render left side content
        for line in lines:
            if line.startswith("  •"):
                # Indent discography items
                text = font_small.render(line, True, (200, 200, 200))
                surface.blit(text, (rect.left + 40, y))
            elif line == "":
                # Empty line for spacing
                pass
            else:
                color = (230, 230, 230) if not line.startswith("To enable") else (170, 170, 170)
                text = font.render(line, True, color)
                surface.blit(text, (rect.left + 20, y))
            y += 20
            
            # Don't go below the panel
            if y > rect.bottom - 40:
                break
        
        # Render log buffer on right side
        log_lines = self.log_buffer.get_lines()[-15:]
        y_log = rect.top + 10
        for line in log_lines:
            text = font_small.render(line, True, (140, 140, 140))
            surface.blit(text, (mid_x + 20, y_log))
            y_log += 18
            if y_log > rect.bottom - 20:
                break
