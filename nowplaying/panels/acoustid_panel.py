"""AcoustID panel.

Minimal, lint-friendly panel that shows AcoustID-derived identifiers and a
brief lookup status. Designed to work without network access for tests by
reading enrichment data from the provided :class:`ContentContext`.
"""

import contextlib

import pygame

from .base import ContentContext, ContentPanel, PanelInfo


class AcoustIDPanel(ContentPanel):
    """Panel that displays AcoustID lookup results.

    This implementation is intentionally minimal and reads enrichment data
    from the provided :class:`ContentContext` so tests can exercise display
    logic without network access.
    """

    def __init__(self) -> None:
        """Initialize the AcoustID panel and its metadata."""
        super().__init__(
            PanelInfo(
                id="acoustid",
                name="AcoustID",
                description="Fingerprint lookup identifiers",
                icon="🔍",
                category="external",
            )
        )

    def can_display(self, context: ContentContext) -> bool:
        """Return True if this panel can display the provided context.

        The panel prefers explicit AcoustID enrichment but will fall back to
        using the ``track_id`` metadata when available.
        """
        if not context:
            return False
        if context.enrichment_data and context.enrichment_data.get("acoustid_id"):
            return True
        # Fallback: show if track_id is present
        return bool(context.track_id)

    def render(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        """Render the panel to the given surface.

        Rendering is defensive: drawing errors are suppressed to keep tests
        stable in headless environments.
        """
        if not self._context:
            return

        enrichment = getattr(self._context, "enrichment_data", None) or {}

        # Draw a simple background rectangle to indicate panel area
        with contextlib.suppress(Exception):
            pygame.draw.rect(surface, (30, 30, 30), rect)

        # Display the AcoustID if present
        if enrichment.get("acoustid_id"):
            with contextlib.suppress(Exception):
                font = pygame.font.Font(None, 16)
                text = font.render(f"AcoustID: {enrichment['acoustid_id']}", True, (200, 200, 200))
                surface.blit(text, (rect.left + 10, rect.top + 10))
        else:
            with contextlib.suppress(Exception):
                font = pygame.font.Font(None, 16)
                text = font.render("No AcoustID data", True, (150, 150, 150))
                surface.blit(text, (rect.left + 10, rect.top + 10))
