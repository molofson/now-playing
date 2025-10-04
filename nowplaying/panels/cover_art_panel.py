"""
Cover Art panel implementation.

This panel displays album cover art in a large format for better viewing.
It includes image loading, scaling, and caching functionality.
"""

import contextlib
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
        if not self._context:
            return

        # Check for local cover art first
        if self._context.cover_art_path and os.path.isfile(self._context.cover_art_path):
            # Use local cover art (existing logic)
            if self._cover_surface is None:
                with contextlib.suppress(Exception):
                    img = pygame.image.load(self._context.cover_art_path)
                    img_w, img_h = img.get_size()
                    target_w, target_h = rect.width - 32, rect.height - 32

                    if img_w > 0 and img_h > 0:
                        scale = min(target_w / img_w, target_h / img_h)
                        new_w = max(1, int(img_w * scale))
                        new_h = max(1, int(img_h * scale))
                        self._cover_surface = pygame.transform.smoothscale(img, (new_w, new_h))

            if self._cover_surface:
                cover_rect = self._cover_surface.get_rect(center=rect.center)
                surface.blit(self._cover_surface, cover_rect)

                if self._context.is_held:
                    pygame.draw.rect(surface, (255, 210, 140), cover_rect, 3)
                return

        # Check for enrichment cover art URLs
        enrichment = getattr(self._context, "enrichment_data", None)
        if enrichment and enrichment.get("cover_art_urls"):
            cover_url_info = enrichment["cover_art_urls"][0]  # Use first available
            url = cover_url_info.get("url")
            thumbnails = cover_url_info.get("thumbnails", {})

            # Try to load from URL (this would need network loading capability)
            # For now, show placeholder with URL info
            pygame.draw.rect(surface, (40, 40, 60), rect, 2)

            font = pygame.font.Font(None, 20)
            lines = [
                "Cover Art Available:",
                f"Source: {cover_url_info.get('source', 'unknown')}",
                f"Type: {cover_url_info.get('type', 'unknown')}",
                f"URL: {url}",
                "Sizes available:",
            ]

            if thumbnails:
                for size_name in sorted(thumbnails.keys()):
                    lines.append(f"  {size_name}: {thumbnails[size_name]}")

            y = rect.top + 20
            for line in lines[:8]:  # Limit lines
                text = font.render(line, True, (180, 180, 200))
                surface.blit(text, (rect.left + 20, y))
                y += 22

            return

        # No cover art available
        pygame.draw.rect(surface, (28, 28, 36), rect, 2)
        font = pygame.font.Font(None, 24)
        text = font.render("No cover art", True, (170, 170, 170))
        text_rect = text.get_rect(center=rect.center)
        surface.blit(text, text_rect)
