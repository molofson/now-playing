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
        """Render the now playing panel with enhanced visual design."""
        self._ensure_fonts()

        # Modern color scheme
        bg_color = (15, 15, 25)
        text_color = (255, 255, 255)
        secondary_color = (200, 200, 220)
        accent_color = (100, 200, 255)
        held_color = (255, 210, 140)
        
        # Fill background
        surface.fill(bg_color, rect)
        
        # Enhanced fonts
        title_font = pygame.font.Font(None, 36)
        track_font = pygame.font.Font(None, 32)
        info_font = pygame.font.Font(None, 24)
        small_font = pygame.font.Font(None, 20)

        margin = 20
        y = rect.y + margin
        center_x = rect.centerx

        # Panel title with icon
        title_text = "🎵 Now Playing"
        title_color = accent_color
        if self._context and self._context.is_held:
            title_text += " (Exploring)"
            title_color = held_color

        title_surface = title_font.render(title_text, True, title_color)
        title_rect = title_surface.get_rect(centerx=center_x, y=y)
        surface.blit(title_surface, title_rect)
        y += title_surface.get_height() + 20

        if not self._context:
            # No context available
            no_data_text = "Waiting for music..."
            no_data_surface = info_font.render(no_data_text, True, secondary_color)
            no_data_rect = no_data_surface.get_rect(centerx=center_x, y=y + 40)
            surface.blit(no_data_surface, no_data_rect)
            return

        # Track title (main focus)
        if self._context.title:
            title_surface = track_font.render(self._context.title, True, text_color)
            title_rect = title_surface.get_rect(centerx=center_x, y=y)
            surface.blit(title_surface, title_rect)
            y += title_surface.get_height() + 15

        # Artist name
        if self._context.artist:
            artist_text = f"by {self._context.artist}"
            artist_surface = info_font.render(artist_text, True, secondary_color)
            artist_rect = artist_surface.get_rect(centerx=center_x, y=y)
            surface.blit(artist_surface, artist_rect)
            y += artist_surface.get_height() + 15

        # Album with icon
        if self._context.album:
            album_text = f"💿 {self._context.album}"
            album_surface = info_font.render(album_text, True, secondary_color)
            album_rect = album_surface.get_rect(centerx=center_x, y=y)
            surface.blit(album_surface, album_rect)
            y += album_surface.get_height() + 20

        # Playback state with colored indicator
        state_colors = {
            "PLAYING": (50, 255, 50),
            "PAUSED": (255, 255, 50),
            "STOPPED": (255, 100, 100),
            "WAITING": (150, 150, 255),
        }
        
        state_name = self._context.playback_state.name if hasattr(self._context.playback_state, 'name') else str(self._context.playback_state)
        state_color = state_colors.get(state_name, secondary_color)
        
        # State indicator circle
        pygame.draw.circle(surface, state_color, (center_x - 50, y + 10), 6)
        
        state_text = f"Status: {state_name}"
        state_surface = info_font.render(state_text, True, state_color)
        surface.blit(state_surface, (center_x - 30, y))
        y += state_surface.get_height() + 15

        # Context info (if held)
        if self._context.is_held:
            held_text = "🔒 Context held for exploration"
            if self._context.held_timestamp:
                held_text += f" (since {self._context.held_timestamp.strftime('%H:%M:%S')})"
            held_surface = small_font.render(held_text, True, held_color)
            held_rect = held_surface.get_rect(centerx=center_x, y=y)
            surface.blit(held_surface, held_rect)
            y += held_surface.get_height() + 10

        # Navigation hint
        hint_y = rect.bottom - 40
        hint_text = "← → Navigate panels | Space: Hold/Release context"
        hint_surface = small_font.render(hint_text, True, (120, 120, 140))
        hint_rect = hint_surface.get_rect(centerx=center_x, y=hint_y)
        surface.blit(hint_surface, hint_rect)

    def handle_event(self, event: pygame.event.Event) -> bool:  # noqa: U100
        """Handle events for now playing panel."""
        return False
