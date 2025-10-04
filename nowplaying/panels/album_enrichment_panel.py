"""
Album Enrichment panel implementation.

Displays album reviews, credits, and related album information.
"""

import pygame

from .base import ContentContext, ContentPanel, PanelInfo


class AlbumEnrichmentPanel(ContentPanel):
    """Panel for displaying album enrichment data."""

    def __init__(self):
        """Initialize the AlbumEnrichmentPanel."""
        super().__init__(
            PanelInfo(
                id="album_enrichment",
                name="Album Enrichment",
                description="Album reviews, credits, and release information",
                icon="💿",
                category="discovery",
            )
        )

    def can_display(self, context: ContentContext) -> bool:
        """Check if album context is available."""
        return context is not None and bool(context.album)

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
        title_text = font.render("Album Enrichment", True, (120, 170, 255))
        surface.blit(title_text, (rect.left + 20, y))
        y += 35

        if enrichment:
            # MusicBrainz Album ID
            if enrichment.get("musicbrainz_album_id"):
                mb_id_title = small_font.render("MusicBrainz ID:", True, (230, 230, 230))
                surface.blit(mb_id_title, (rect.left + 20, y))
                y += 20
                mb_id_text = small_font.render(enrichment["musicbrainz_album_id"], True, (180, 180, 180))
                surface.blit(mb_id_text, (rect.left + 30, y))
                y += 18

            # Discogs Release ID
            if enrichment.get("discogs_release_id"):
                discogs_id_title = small_font.render("Discogs ID:", True, (230, 230, 230))
                surface.blit(discogs_id_title, (rect.left + 20, y))
                y += 20
                discogs_id_text = small_font.render(enrichment["discogs_release_id"], True, (180, 180, 180))
                surface.blit(discogs_id_text, (rect.left + 30, y))
                y += 18

            # Album Reviews
            if enrichment.get("album_reviews"):
                reviews_title = small_font.render("Reviews:", True, (230, 230, 230))
                surface.blit(reviews_title, (rect.left + 20, y))
                y += 20
                for _i, review in enumerate(enrichment["album_reviews"][:2]):  # Limit to 2 reviews
                    if isinstance(review, dict):
                        source = review.get("source", "Unknown")
                        rating = review.get("rating", "N/A")
                        review_text = small_font.render(f"{source}: {rating}/10", True, (200, 200, 200))
                        surface.blit(review_text, (rect.left + 30, y))
                        y += 18
                        if "text" in review and review["text"]:
                            text_lines = self._wrap_text(review["text"], 50)
                            for line in text_lines[:2]:  # Limit review text
                                text_render = small_font.render(line, True, (180, 180, 180))
                                surface.blit(text_render, (rect.left + 40, y))
                                y += 16
                y += 10

            # Album Credits
            if enrichment.get("album_credits"):
                credits_title = small_font.render("Credits:", True, (230, 230, 230))
                surface.blit(credits_title, (rect.left + 20, y))
                y += 20
                for _i, credit in enumerate(enrichment["album_credits"][:5]):  # Limit credits
                    if isinstance(credit, dict):
                        role = credit.get("role", "")
                        artist = credit.get("artist", "")
                        credit_text = small_font.render(f"{role}: {artist}", True, (180, 180, 180))
                        surface.blit(credit_text, (rect.left + 30, y))
                        y += 18
                y += 10

            # Recent Releases (related albums)
            if enrichment.get("recent_releases"):
                recent_title = small_font.render("Recent Releases:", True, (230, 230, 230))
                surface.blit(recent_title, (rect.left + 20, y))
                y += 20
                for _i, release in enumerate(enrichment["recent_releases"][:3]):  # Limit releases
                    if isinstance(release, dict):
                        title = release.get("title", "")
                        year = release.get("year", "")
                        release_text = small_font.render(f"{year} - {title}", True, (160, 160, 160))
                        surface.blit(release_text, (rect.left + 30, y))
                        y += 18
        else:
            no_data = font.render("No album enrichment data available", True, (150, 150, 150))
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
