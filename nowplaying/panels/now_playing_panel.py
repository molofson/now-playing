"""
Now Playing panel implementation.

This panel displays the current song metadata and playback state.
It's the primary panel for showing what's currently playing.
"""

import pygame

from .base import ContentContext, ContentPanel, PanelInfo


class NowPlayingPanel(ContentPanel):
    """Primary metadata display panel - artist, album, title, state."""

    def __init__(self):
        """Initialize now playing panel."""
        super().__init__(
            PanelInfo(
                id="now_playing",
                name="Now Playing",
                description="Main metadata display with track info",
                icon="🎵",
                category="core",
            )
        )
        self._fonts = {}

    def _ensure_fonts(self):
        """Lazy load fonts."""
        if not self._fonts:
            try:
                self._fonts = {
                    "title": pygame.font.Font(None, 28),
                    "meta": pygame.font.Font(None, 24),
                    "state": pygame.font.Font(None, 20),
                }
            except pygame.error:
                # Fallback to default font
                self._fonts = {
                    "title": pygame.font.Font(None, 28),
                    "meta": pygame.font.Font(None, 24),
                    "state": pygame.font.Font(None, 20),
                }

    def update_context(self, context: ContentContext) -> None:
        """Update with new content context."""
        self._context = context

    def render(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        """Render the now playing panel."""
        if not self._context:
            return

        self._ensure_fonts()

        # Colors
        text_color = (230, 230, 230)
        dim_color = (170, 170, 170)
        accent_color = (120, 170, 255)
        held_color = (255, 210, 140)

        margin = 16
        y = rect.y + margin

        # Title with context indicator
        title_text = "Now Playing"
        title_color = accent_color
        if self._context.is_held:
            title_text += " (Exploring)"
            title_color = held_color

        title_surface = self._fonts["title"].render(title_text, True, title_color)
        surface.blit(title_surface, (rect.x + margin, y))
        y += title_surface.get_height() + 12

        # Artist
        if self._context.artist:
            artist_surface = self._fonts["meta"].render(f"Artist: {self._context.artist}", True, text_color)
            surface.blit(artist_surface, (rect.x + margin, y))
            y += artist_surface.get_height() + 8

        # Album
        if self._context.album:
            album_surface = self._fonts["meta"].render(f"Album: {self._context.album}", True, text_color)
            surface.blit(album_surface, (rect.x + margin, y))
            y += album_surface.get_height() + 8

        # Title
        if self._context.title:
            title_surface = self._fonts["meta"].render(f"Title: {self._context.title}", True, text_color)
            surface.blit(title_surface, (rect.x + margin, y))
            y += title_surface.get_height() + 8

        # State
        state_text = f"State: {self._context.playback_state.name}"
        state_surface = self._fonts["state"].render(state_text, True, dim_color)
        surface.blit(state_surface, (rect.x + margin, y))
        y += state_surface.get_height() + 8

        # Context info (if held)
        if self._context.is_held and self._context.held_timestamp:
            held_text = f"Held: {self._context.held_timestamp.strftime('%H:%M:%S')}"
            held_surface = self._fonts["state"].render(held_text, True, held_color)
            surface.blit(held_surface, (rect.x + margin, y))

    def handle_event(self, event: pygame.event.Event) -> bool:  # noqa: U100
        """Handle events for now playing panel."""
        return False
