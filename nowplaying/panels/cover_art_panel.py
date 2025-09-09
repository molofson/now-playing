"""
Cover Art panel implementation.

This panel displays album cover art in a large format for better viewing.
It includes image loading, scaling, and caching functionality.
"""

import os

import pygame

from .base import ContentContext, ContentPanel, PanelInfo


class CoverArtPanel(ContentPanel):
    """Large cover art display panel."""

    def __init__(self):
        """Initialize cover art panel."""
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

    def handle_event(self, event: pygame.event.Event) -> bool:  # noqa: U100
        """Handle events for cover art panel."""
        return False
