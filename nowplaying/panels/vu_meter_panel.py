"""
VU Meter panel implementation.

This panel displays real-time audio level meters for visualizing audio levels.
It requires live audio data and doesn't support held contexts.
"""

import pygame

from .base import ContentContext, ContentPanel, PanelInfo


class VUMeterPanel(ContentPanel):
    """Audio level visualization panel."""

    def __init__(self):
        """Initialize VU meter panel."""
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

    def handle_event(self, event: pygame.event.Event) -> bool:  # noqa: U100
        """Handle events for VU meter panel."""
        return False
