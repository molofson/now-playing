"""
Debug panel for technical metadata and troubleshooting information.

This panel displays technical metadata and debug information about the current context.
Useful for development and troubleshooting.
"""

import os

import pygame

from .base import ContentContext, ContentPanel, PanelInfo


class DebugPanel(ContentPanel):
    """Debug information panel."""

    def __init__(self):
        """Initialize debug panel."""
        super().__init__(
            PanelInfo(
                id="debug",
                name="Debug",
                description="Technical metadata and debug information",
                icon="🔍",
                category="technical",
            )
        )

    def update_context(self, context: ContentContext) -> None:
        """Update with new context."""
        self._context = context

    def can_display(self, context: ContentContext) -> bool:  # noqa: U100
        """Debug panel can always display."""
        return True

    def render(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        """Render debug information."""
        if not hasattr(self, "_context") or not self._context:
            return

        font = pygame.font.Font(None, 24)
        y_offset = rect.top + 10
        line_height = 30

        # Basic metadata
        lines = [
            f"Track: {self._context.metadata.get('title', 'Unknown')}",
            f"Artist: {self._context.metadata.get('artist', 'Unknown')}",
            f"Album: {self._context.metadata.get('album', 'Unknown')}",
            f"Duration: {self._context.metadata.get('duration', 'Unknown')}",
            f"File: {os.path.basename(self._context.metadata.get('file', 'Unknown'))}",
            "",
            "Technical Info:",
            f"Context Type: {type(self._context).__name__}",
            f"Metadata Keys: {len(self._context.metadata)} fields",
            f"Enrichment: {len(self._context.enrichment)} services",
        ]

        # Add enrichment details
        for service_id, enrichment_data in self._context.enrichment.items():
            lines.append(f"  {service_id}: {len(enrichment_data.metadata)} fields")

        for i, line in enumerate(lines):
            text_surface = font.render(line, True, (255, 255, 255))
            surface.blit(text_surface, (rect.left + 10, y_offset + i * line_height))

    def handle_event(self, event: pygame.event.Event) -> bool:  # noqa: U100
        """Handle events for debug panel."""
        return False
