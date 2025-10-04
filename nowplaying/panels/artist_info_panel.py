"""
Artist Information enrichment panel implementation.

Displays artist bio, tags, and similar artists from enrichment data.
"""

import pygame

from .base import ContentContext, ContentPanel, PanelInfo


class ArtistInfoPanel(ContentPanel):
    """Panel for displaying artist information from enrichment."""

    def __init__(self):
        """Initialize the ArtistInfoPanel."""
        super().__init__(
            PanelInfo(
                id="artist_info",
                name="Artist Info",
                description="Artist biography, tags, and similar artists",
                icon="👤",
                category="discovery",
            )
        )

    def can_display(self, context: ContentContext) -> bool:
        """Check if artist context is available."""
        return context is not None and bool(context.artist)

    def update_context(self, context: ContentContext) -> None:
        """Update panel with new context."""
        self._context = context

    def render(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        """Render panel content."""
        if not self._context:
            return

        font = pygame.font.Font(None, 20)
        small_font = pygame.font.Font(None, 16)
        y = rect.top + 10

        enrichment = getattr(self._context, "enrichment_data", None)

        # Title
        title_text = font.render("Artist Information", True, (120, 170, 255))
        surface.blit(title_text, (rect.left + 20, y))
        y += 35

        if enrichment:
            # MusicBrainz Artist ID
            if enrichment.get("musicbrainz_artist_id"):
                mb_id_title = small_font.render("MusicBrainz ID:", True, (230, 230, 230))
                surface.blit(mb_id_title, (rect.left + 20, y))
                y += 20
                mb_id_text = small_font.render(enrichment["musicbrainz_artist_id"], True, (180, 180, 180))
                surface.blit(mb_id_text, (rect.left + 30, y))
                y += 18

            # Artist Tags
            if enrichment.get("artist_tags"):
                tags_title = small_font.render("Tags:", True, (230, 230, 230))
                surface.blit(tags_title, (rect.left + 20, y))
                y += 20
                tags_text = ", ".join(enrichment["artist_tags"][:8])  # Limit tags
                tags_lines = self._wrap_text(tags_text, 50)
                for line in tags_lines:
                    tag_text = small_font.render(line, True, (180, 180, 180))
                    surface.blit(tag_text, (rect.left + 30, y))
                    y += 18
                y += 10

            # Artist Bio (if available from Last.fm)
            if enrichment.get("artist_bio"):
                bio_lines = self._wrap_text(enrichment["artist_bio"], 60)
                bio_title = small_font.render("Biography:", True, (230, 230, 230))
                surface.blit(bio_title, (rect.left + 20, y))
                y += 20
                for line in bio_lines[:3]:  # Limit to 3 lines
                    bio_text = small_font.render(line, True, (200, 200, 200))
                    surface.blit(bio_text, (rect.left + 30, y))
                    y += 18
                y += 10

            # Similar Artists (if available from Last.fm)
            if enrichment.get("similar_artists"):
                similar_title = small_font.render("Similar Artists:", True, (230, 230, 230))
                surface.blit(similar_title, (rect.left + 20, y))
                y += 20
                for _i, artist in enumerate(enrichment["similar_artists"][:5]):
                    if isinstance(artist, dict) and "name" in artist:
                        match = artist.get("match", 0)
                        artist_text = small_font.render(f"{artist['name']} ({match:.1%})", True, (160, 160, 160))
                        surface.blit(artist_text, (rect.left + 30, y))
                        y += 18
        else:
            no_data = font.render("No artist enrichment data available", True, (150, 150, 150))
            surface.blit(no_data, (rect.left + 20, y))

    def _wrap_text(self, text: str, max_chars: int) -> list:
        """Wrap text to fit within specified width."""
        words = text.split()
        lines = []
        current_line = ""
        for word in words:
            if len(current_line + " " + word) <= max_chars:
                current_line += " " + word if current_line else word
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)
        return lines
