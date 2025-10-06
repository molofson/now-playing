"""Lyrics display panel.

Minimal implementation that reads ``enrichment_data['song_lyrics']`` and
renders a short excerpt. Designed for tests without requiring network
access.
"""

import contextlib

import pygame

from .base import ContentContext, ContentPanel, PanelInfo


class LyricsPanel(ContentPanel):
    """Panel that displays song lyrics or an excerpt.

    Reads ``enrichment_data['song_lyrics']`` from the context and renders a
    short excerpt. Drawing operations are suppressed on error to keep tests
    robust in headless environments.
    """

    def __init__(self) -> None:
        """Initialize the Lyrics panel."""
        super().__init__(
            PanelInfo(
                id="lyrics",
                name="Lyrics",
                description="Song lyrics and annotations",
                icon="🎵",
                category="discovery",
            )
        )

    def can_display(self, context: ContentContext) -> bool:
        """Return True when lyrics are available in enrichment data."""
        if not context:
            return False
        enrichment = getattr(context, "enrichment_data", None) or {}
        return bool(enrichment.get("song_lyrics"))

    def render(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        """Render a short excerpt of lyrics to the surface."""
        if not self._context:
            return

        enrichment = getattr(self._context, "enrichment_data", None) or {}
        lyrics = enrichment.get("song_lyrics") or ""

        with contextlib.suppress(Exception):
            pygame.draw.rect(surface, (25, 25, 25), rect)

        if not lyrics:
            return

        # Render only the first two lines to keep it compact in tests
        with contextlib.suppress(Exception):
            font = pygame.font.Font(None, 16)
            first_lines = "\n".join(lyrics.splitlines()[:2])
            text = font.render(first_lines, True, (230, 230, 230))
            surface.blit(text, (rect.left + 10, rect.top + 10))
