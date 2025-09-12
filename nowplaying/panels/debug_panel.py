"""
Debug panel for technical metadata and troubleshooting information.

This panel displays technical metadata and debug information about the current context.
Useful for development and troubleshooting.
"""

import pygame

from .base import ContentContext, ContentPanel, PanelInfo


class DebugPanel(ContentPanel):
    """Debug information panel."""

    def __init__(self):
        """Initialize debug panel with scroll support."""
        super().__init__(
            PanelInfo(
                id="debug",
                name="Debug",
                description="Technical metadata and debug information",
                icon="🔍",
                category="technical",
            )
        )
        self._scroll_offset = 0  # in lines
        self._line_height = 30
        self._touch_scroll_active = False
        self._touch_scroll_start_y = None
        self._touch_scroll_start_offset = 0

    def update_context(self, context: ContentContext) -> None:
        """Update with new context."""
        self._context = context

    def can_display(self, context: ContentContext) -> bool:  # noqa: U100
        """Debug panel can always display."""
        return True

    def render(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        """Render debug information with vertical scrolling."""
        if not hasattr(self, "_context") or not self._context:
            return

        font = pygame.font.Font(None, 24)
        y_offset = rect.top + 10
        line_height = self._line_height

        # Show all known ContentContext attributes
        ctx = self._context
        left_lines = [
            f"Track: {ctx.title or 'Unknown'}",
            f"Artist: {ctx.artist or 'Unknown'}",
            f"Album: {ctx.album or 'Unknown'}",
            f"Genre: {ctx.genre or 'Unknown'}",
            f"Cover Art Path: {ctx.cover_art_path or 'None'}",
            f"Playback State: {getattr(ctx, 'playback_state', 'Unknown')}",
            f"Year: {ctx.year or 'Unknown'}",
            f"Track #: {ctx.track_number or 'Unknown'}",
            f"Album Artist: {ctx.album_artist or 'Unknown'}",
            f"Composer: {ctx.composer or 'Unknown'}",
            f"Duration: {ctx.duration if ctx.duration is not None else 'Unknown'}",
            f"Bitrate: {ctx.bitrate or 'Unknown'}",
            f"Format: {ctx.format or 'Unknown'}",
            f"Audio Levels: {ctx.audio_levels if ctx.audio_levels is not None else 'None'}",
            f"Is Held: {ctx.is_held}",
            f"Held Timestamp: {ctx.held_timestamp or 'None'}",
            f"Source: {ctx.source or 'Unknown'}",
            f"Artist ID: {ctx.artist_id or 'None'}",
            f"Album ID: {ctx.album_id or 'None'}",
        ]

        # Technical info and enrichment (right side)
        right_lines = [
            "Technical Info:",
            f"Context Type: {type(ctx).__name__}",
            f"Metadata Keys: {len([v for v in vars(ctx).values() if v not in (None, '', False)])} fields",
            f"Enrichment: {len(getattr(ctx, 'enrichment', {}))} services",
        ]
        enrichment = getattr(ctx, "enrichment", {})
        for service_id, enrichment_data in enrichment.items():
            meta = getattr(enrichment_data, "metadata", None)
            if isinstance(meta, dict):
                right_lines.append(f"  {service_id}: {len(meta)} fields")
            else:
                right_lines.append(f"  {service_id}: (no metadata)")

        # Calculate visible lines for each column
        max_visible_lines = (rect.height - 20) // line_height
        start = self._scroll_offset
        end_left = min(start + max_visible_lines, len(left_lines))
        end_right = min(start + max_visible_lines, len(right_lines))
        visible_left = left_lines[start:end_left]
        visible_right = right_lines[start:end_right]

        # Left column (main metadata)
        for i, line in enumerate(visible_left):
            text_surface = font.render(line, True, (255, 255, 255))
            surface.blit(text_surface, (rect.left + 10, y_offset + i * line_height))

        # Right column (technical info)
        right_x = rect.left + rect.width // 2 + 10
        for i, line in enumerate(visible_right):
            text_surface = font.render(line, True, (200, 200, 255))
            surface.blit(text_surface, (right_x, y_offset + i * line_height))

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handle events for debug panel (scroll with mouse wheel, arrow keys, or touch)."""
        # Mouse wheel scroll (pygame 2.x: event.type == pygame.MOUSEWHEEL)
        if event.type == pygame.MOUSEWHEEL:
            self._scroll_offset = max(0, self._scroll_offset - event.y)
            return True
        # Keyboard scroll
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self._scroll_offset = max(0, self._scroll_offset - 1)
                return True
            elif event.key == pygame.K_DOWN:
                ctx = self._context
                lines_count = 22
                if ctx:
                    try:
                        lines_count = 22 + len(getattr(ctx, "enrichment", {}))
                    except Exception:
                        pass
                max_scroll = max(0, lines_count - 1)
                self._scroll_offset = min(self._scroll_offset + 1, max_scroll)
                return True
        # Touch scroll (FINGERDOWN/FINGERMOTION)
        elif event.type == pygame.FINGERDOWN:
            self._touch_scroll_active = True
            self._touch_scroll_start_y = event.y
            self._touch_scroll_start_offset = self._scroll_offset
            return True
        elif event.type == pygame.FINGERMOTION and self._touch_scroll_active:
            # event.y is normalized (0.0 to 1.0), so use display height
            display_height = pygame.display.get_surface().get_height()
            display_width = pygame.display.get_surface().get_width()
            dy_pixels = (event.y - self._touch_scroll_start_y) * display_height
            dx_pixels = (event.x - getattr(event, "x0", event.x)) * display_width if hasattr(event, "x0") else 0
            # Only consume if vertical swipe is dominant
            if abs(dy_pixels) > abs(dx_pixels) and abs(dy_pixels) > 10:
                lines_moved = int(-dy_pixels // self._line_height)
                ctx = self._context
                lines_count = 22
                if ctx:
                    try:
                        lines_count = 22 + len(getattr(ctx, "enrichment", {}))
                    except Exception:
                        pass
                max_scroll = max(0, lines_count - 1)
                new_offset = self._touch_scroll_start_offset + lines_moved
                self._scroll_offset = max(0, min(new_offset, max_scroll))
                return True
            # else: let event propagate for navigation
            return False
        elif event.type == pygame.FINGERUP:
            self._touch_scroll_active = False
            self._touch_scroll_start_y = None
            return True
        return False
