"""
Last.fm enrichment panel implementation.

Displays Last.fm enrichment results for the current context.
"""

import pygame

from .base import ContentContext, ContentPanel, PanelInfo
from .enrichment_log_buffer import EnrichmentLogBuffer


class LastFmPanel(ContentPanel):
    def handle_event(self, event: pygame.event.Event) -> bool:  # noqa: U100
        """Handle events (not used)."""
        return False

    def can_display(self, context: ContentContext) -> bool:
        return context is not None

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
        self._context = context

    def render(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        if not self._context:
            return
            
        font = pygame.font.Font(None, 20)
        font_small = pygame.font.Font(None, 16)
        mid_x = rect.left + rect.width // 2
        y = rect.top + 10
        
        enrichment = getattr(self._context, "enrichment_data", None)
        
        if enrichment and hasattr(enrichment, "artist_bio"):
            # Artist Bio (truncated)
            bio = enrichment.artist_bio or ""
            if len(bio) > 200:
                bio = bio[:200] + "..."
            
            lines = [
                f"Artist: {self._context.artist}",
                "",
                "Biography:",
                bio,
                "",
                f"Tags: {', '.join(enrichment.artist_tags) if enrichment.artist_tags else 'None'}",
            ]
            
            # Add scrobble count if available
            if enrichment.scrobble_count:
                lines.append(f"Play count: {enrichment.scrobble_count:,}")
            
            # Add similar artists
            if enrichment.similar_artists:
                lines.append("")
                lines.append("Similar Artists:")
                for artist in enrichment.similar_artists[:3]:  # Show top 3
                    name = artist.get("name", "Unknown")
                    match = artist.get("match", 0)
                    lines.append(f"  • {name} ({match:.0%} match)")
        else:
            lines = [
                f"Artist: {self._context.artist}",
                "",
                "No Last.fm enrichment data available.",
                "",
                "To enable real Last.fm data:",
                "Set LASTFM_API_KEY environment variable"
            ]
        
        # Render left side content
        for line in lines:
            if line.startswith("  •"):
                # Indent similar artists
                text = font_small.render(line, True, (200, 200, 200))
                surface.blit(text, (rect.left + 40, y))
            elif line == "":
                # Empty line for spacing
                pass
            else:
                color = (230, 230, 230) if not line.startswith("To enable") else (170, 170, 170)
                text = font.render(line, True, color)
                surface.blit(text, (rect.left + 20, y))
            y += 22
            
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
