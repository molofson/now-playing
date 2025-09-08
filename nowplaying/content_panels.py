"""
Built-in content panels for the discovery interface.

This module provides concrete implementations of ContentPanel for common use cases:
- Current playing metadata display
- Cover art showcase
- Audio level visualization (VU meters)
- Debug information display
"""

import os
from typing import Any, Dict, List, Optional

import pygame

from .music_views import ContentContext, ContentPanel, PanelInfo


class NowPlayingPanel(ContentPanel):
    """Primary metadata display panel - artist, album, title, state."""

    def __init__(self):
        info = PanelInfo(
            id="now_playing",
            name="Now Playing",
            description="Current song metadata and playback state",
            icon="🎵",
            category="general",
            requires_metadata=True,
        )
        super().__init__(info)
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

    def handle_event(self, _event: pygame.event.Event) -> bool:
        """Handle events - currently none for this panel."""
        return False


class CoverArtPanel(ContentPanel):
    """Large cover art display panel."""

    def __init__(self):
        info = PanelInfo(
            id="cover_art",
            name="Cover Art",
            description="Large album cover display",
            icon="🖼️",
            category="discovery",
            requires_cover_art=True,
        )
        super().__init__(info)
        self._cover_surface = None
        self._cached_path = None

    def update_context(self, context: ContentContext) -> None:
        """Update with new content context."""
        self._context = context
        # Clear cache if cover path changed
        if context.cover_art_path != self._cached_path:
            self._cover_surface = None
            self._cached_path = context.cover_art_path

    def render(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        """Render the cover art panel."""
        if not self._context or not self._context.cover_art_path:
            # Draw placeholder
            pygame.draw.rect(surface, (28, 28, 36), rect, 2)
            font = pygame.font.Font(None, 24)
            text = font.render("No cover art", True, (170, 170, 170))
            text_rect = text.get_rect(center=rect.center)
            surface.blit(text, text_rect)
            return

        # Load cover if needed
        if self._cover_surface is None and os.path.isfile(self._context.cover_art_path):
            try:
                img = pygame.image.load(self._context.cover_art_path)

                # Scale to fit rect while preserving aspect ratio
                img_w, img_h = img.get_size()
                target_w, target_h = rect.width - 32, rect.height - 32  # Margin

                if img_w > 0 and img_h > 0:
                    scale = min(target_w / img_w, target_h / img_h)
                    new_w = max(1, int(img_w * scale))
                    new_h = max(1, int(img_h * scale))
                    self._cover_surface = pygame.transform.smoothscale(img, (new_w, new_h))
            except Exception:
                self._cover_surface = None

        # Draw cover if loaded
        if self._cover_surface:
            # Center the cover
            cover_rect = self._cover_surface.get_rect(center=rect.center)
            surface.blit(self._cover_surface, cover_rect)

            # Draw held indicator if exploring
            if self._context.is_held:
                # Yellow border to indicate held state
                pygame.draw.rect(surface, (255, 210, 140), cover_rect, 3)
        else:
            # Error loading cover
            pygame.draw.rect(surface, (60, 30, 30), rect, 2)
            font = pygame.font.Font(None, 20)
            text = font.render("Cover load failed", True, (255, 120, 120))
            text_rect = text.get_rect(center=rect.center)
            surface.blit(text, text_rect)

    def handle_event(self, _event: pygame.event.Event) -> bool:
        """Handle events - currently none for this panel."""
        return False


class VUMeterPanel(ContentPanel):
    """Audio level visualization panel."""

    def __init__(self):
        info = PanelInfo(
            id="vu_meters",
            name="Audio Levels",
            description="Real-time audio level meters",
            icon="📊",
            category="audio",
            requires_audio_data=True,
        )
        super().__init__(info)

    def supports_hold(self) -> bool:
        """VU meters need live audio data."""
        return False

    def update_context(self, context: ContentContext) -> None:
        """Update with new content context."""
        self._context = context

    def render(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        """Render VU meters."""
        if not self._context or not self._context.audio_levels:
            # Draw placeholder
            font = pygame.font.Font(None, 24)
            text = font.render("No audio data", True, (170, 170, 170))
            text_rect = text.get_rect(center=rect.center)
            surface.blit(text, text_rect)
            return

        # Draw meter bars
        margin = 20
        bar_width = 40
        bar_spacing = 60

        levels = self._context.audio_levels
        x = rect.x + margin

        for channel, level in levels.items():
            # Clamp level to 0-1
            level = max(0.0, min(1.0, level))

            # Meter background
            meter_rect = pygame.Rect(x, rect.y + margin, bar_width, rect.height - 2 * margin)
            pygame.draw.rect(surface, (40, 40, 40), meter_rect)

            # Level bar
            level_height = int(level * meter_rect.height)
            level_rect = pygame.Rect(x, meter_rect.bottom - level_height, bar_width, level_height)

            # Color based on level
            if level > 0.8:
                color = (255, 100, 100)  # Red - clipping
            elif level > 0.6:
                color = (255, 200, 100)  # Orange - loud
            else:
                color = (100, 255, 100)  # Green - normal

            pygame.draw.rect(surface, color, level_rect)

            # Channel label
            font = pygame.font.Font(None, 16)
            label = font.render(channel.upper(), True, (200, 200, 200))
            label_rect = label.get_rect(center=(x + bar_width // 2, rect.bottom - 10))
            surface.blit(label, label_rect)

            x += bar_spacing

    def handle_event(self, _event: pygame.event.Event) -> bool:
        """Handle events - currently none for this panel."""
        return False


class DebugPanel(ContentPanel):
    """Debug information panel."""

    def __init__(self):
        info = PanelInfo(
            id="debug_info",
            name="Debug Info",
            description="Technical metadata and debug information",
            icon="🔧",
            category="debug",
        )
        super().__init__(info)

    def update_context(self, context: ContentContext) -> None:
        """Update with new content context."""
        self._context = context

    def render(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        """Render debug information."""
        if not self._context:
            return

        font = pygame.font.Font(None, 18)
        text_color = (200, 200, 200)
        dim_color = (140, 140, 140)

        y = rect.y + 16
        line_height = 20

        # Debug info
        debug_items = [
            ("Context Source", self._context.source),
            ("Is Held", str(self._context.is_held)),
            ("Playback State", self._context.playback_state.name),
            ("Format", self._context.format or "Unknown"),
            ("Bitrate", self._context.bitrate or "Unknown"),
            ("Year", self._context.year or "Unknown"),
            ("Genre", self._context.genre or "Unknown"),
            ("Cover Path", os.path.basename(self._context.cover_art_path) if self._context.cover_art_path else "None"),
        ]

        for label, value in debug_items:
            if y + line_height > rect.bottom:
                break

            # Label
            label_surface = font.render(f"{label}:", True, dim_color)
            surface.blit(label_surface, (rect.x + 16, y))

            # Value
            value_surface = font.render(str(value), True, text_color)
            surface.blit(value_surface, (rect.x + 140, y))

            y += line_height

    def handle_event(self, _event: pygame.event.Event) -> bool:
        """Handle events - currently none for this panel."""
        return False
