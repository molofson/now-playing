"""
Navigation controller for swipeable content panels.

Handles left-right swipe navigation between registered content panels,
manages the hold/release functionality for exploration contexts.
"""

from enum import Enum
from typing import List, Optional, Tuple

import pygame

from .music_views import ContentContext, ContentPanel, content_panel_registry


class SwipeDirection(Enum):
    """Swipe direction enumeration."""

    LEFT = "left"
    RIGHT = "right"
    NONE = "none"


class PanelNavigator:
    """Manages navigation between content panels with swipe support."""

    def __init__(self):
        self.registry = content_panel_registry
        self._current_panel_index = 0
        self._available_panels: List[ContentPanel] = []

        # Swipe detection
        self._swipe_start_pos: Optional[Tuple[int, int]] = None
        self._swipe_threshold = 50  # Minimum distance for swipe
        self._swipe_in_progress = False

        # Panel transition animation (optional)
        self._transition_offset = 0.0
        self._transition_speed = 8.0  # Animation speed

        # Context management
        self._last_live_context: Optional[ContentContext] = None

    def update_available_panels(self, context: Optional[ContentContext] = None) -> None:
        """Update the list of available panels based on context."""
        self._available_panels = self.registry.get_available_panels(context)

        # Ensure current index is valid
        if self._available_panels:
            self._current_panel_index = max(0, min(self._current_panel_index, len(self._available_panels) - 1))
        else:
            self._current_panel_index = 0

    def get_current_panel(self) -> Optional[ContentPanel]:
        """Get the currently active panel."""
        if self._available_panels and 0 <= self._current_panel_index < len(self._available_panels):
            return self._available_panels[self._current_panel_index]
        return None

    def get_panel_info(self) -> dict:
        """Get information about current panel state."""
        current = self.get_current_panel()
        return {
            "current_index": self._current_panel_index,
            "total_panels": len(self._available_panels),
            "current_panel_id": current.info.id if current else None,
            "current_panel_name": current.info.name if current else None,
            "has_held_context": self.registry.has_held_context(),
            "can_swipe_left": self._current_panel_index > 0,
            "can_swipe_right": self._current_panel_index < len(self._available_panels) - 1,
        }

    def navigate_to_panel(self, panel_id: str) -> bool:
        """Navigate directly to a panel by ID."""
        for i, panel in enumerate(self._available_panels):
            if panel.info.id == panel_id:
                self._current_panel_index = i
                return True
        return False

    def navigate_left(self) -> bool:
        """Navigate to previous panel."""
        if self._current_panel_index > 0:
            self._current_panel_index -= 1
            return True
        return False

    def navigate_right(self) -> bool:
        """Navigate to next panel."""
        if self._current_panel_index < len(self._available_panels) - 1:
            self._current_panel_index += 1
            return True
        return False

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handle navigation events (swipes, key presses)."""
        # Let current panel handle event first
        current_panel = self.get_current_panel()
        if current_panel and current_panel.handle_event(event):
            return True

        # Handle navigation events
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left mouse button
                self._swipe_start_pos = event.pos
                self._swipe_in_progress = True
                return True

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1 and self._swipe_in_progress:
                self._handle_swipe_end(event.pos)
                self._swipe_start_pos = None
                self._swipe_in_progress = False
                return True

        elif event.type == pygame.KEYDOWN:
            # Keyboard navigation
            if event.key == pygame.K_LEFT or event.key == pygame.K_a:
                return self.navigate_left()
            elif event.key == pygame.K_RIGHT or event.key == pygame.K_d:
                return self.navigate_right()
            elif event.key == pygame.K_SPACE:
                # Toggle hold/release
                return self._toggle_hold_context()
            elif event.key == pygame.K_h:
                # Hold current context
                return self._hold_current_context()
            elif event.key == pygame.K_r:
                # Release held context
                return self._release_held_context()

        # Touch/finger events (if supported)
        elif hasattr(pygame, "FINGERDOWN") and event.type == pygame.FINGERDOWN:
            self._swipe_start_pos = (
                event.x * pygame.display.get_surface().get_width(),
                event.y * pygame.display.get_surface().get_height(),
            )
            self._swipe_in_progress = True
            return True

        elif hasattr(pygame, "FINGERUP") and event.type == pygame.FINGERUP and self._swipe_in_progress:
            end_pos = (
                event.x * pygame.display.get_surface().get_width(),
                event.y * pygame.display.get_surface().get_height(),
            )
            self._handle_swipe_end(end_pos)
            self._swipe_start_pos = None
            self._swipe_in_progress = False
            return True

        return False

    def _handle_swipe_end(self, end_pos: Tuple[int, int]) -> None:
        """Handle end of swipe gesture."""
        if not self._swipe_start_pos:
            return

        dx = end_pos[0] - self._swipe_start_pos[0]
        dy = end_pos[1] - self._swipe_start_pos[1]

        # Check if it's a horizontal swipe
        if abs(dx) > abs(dy) and abs(dx) > self._swipe_threshold:
            if dx > 0:
                # Swipe right -> go to previous panel
                self.navigate_left()
            else:
                # Swipe left -> go to next panel
                self.navigate_right()

        # Check for vertical swipe (hold/release gesture)
        elif abs(dy) > abs(dx) and abs(dy) > self._swipe_threshold:
            if dy < 0:
                # Swipe up -> hold current context
                self._hold_current_context()
            else:
                # Swipe down -> release held context
                self._release_held_context()

    def _toggle_hold_context(self) -> bool:
        """Toggle between held and live context."""
        if self.registry.has_held_context():
            return self._release_held_context()
        else:
            return self._hold_current_context()

    def _hold_current_context(self) -> bool:
        """Hold the current live context for exploration."""
        live_context = self.registry.get_live_context()
        if live_context and not self.registry.has_held_context():
            self.registry.set_held_context(live_context)
            return True
        return False

    def _release_held_context(self) -> bool:
        """Release held context and return to live updates."""
        if self.registry.has_held_context():
            self.registry.release_held_context()
            return True
        return False

    def update_live_context(self, context: ContentContext) -> None:
        """Update live context and refresh available panels if needed."""
        self._last_live_context = context
        self.registry.update_live_context(context)

        # Update available panels if context changed significantly
        # (e.g., new artist means different panels might be available)
        if self._context_changed_significantly(context):
            self.update_available_panels(context)

    def _context_changed_significantly(self, new_context: ContentContext) -> bool:
        """Check if context changed enough to refresh panel availability."""
        if not self._last_live_context:
            return True

        # Check key fields that might affect panel availability
        return (
            self._last_live_context.artist != new_context.artist
            or self._last_live_context.album != new_context.album
            or bool(self._last_live_context.cover_art_path) != bool(new_context.cover_art_path)
            or bool(self._last_live_context.audio_levels) != bool(new_context.audio_levels)
        )

    def render_navigation_hints(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        """Render navigation hints/indicators."""
        font = pygame.font.Font(None, 16)
        hint_color = (140, 140, 140)

        # Panel indicator
        panel_info = self.get_panel_info()
        current = self.get_current_panel()

        if current:
            # Panel name and position
            panel_text = f"{current.info.name} ({panel_info['current_index'] + 1}/{panel_info['total_panels']})"
            panel_surface = font.render(panel_text, True, hint_color)
            surface.blit(panel_surface, (rect.x + 10, rect.bottom - 40))

            # Navigation hints
            hints = []
            if panel_info["can_swipe_left"]:
                hints.append("← Prev")
            if panel_info["can_swipe_right"]:
                hints.append("Next →")

            if self.registry.has_held_context():
                hints.append("Space: Release")
            else:
                hints.append("Space: Hold")

            if hints:
                hint_text = " | ".join(hints)
                hint_surface = font.render(hint_text, True, hint_color)
                surface.blit(hint_surface, (rect.x + 10, rect.bottom - 20))

    def get_navigation_status(self) -> dict:
        """Get detailed navigation status for debugging."""
        return {
            **self.get_panel_info(),
            "registry_status": self.registry.get_registry_status(),
            "swipe_in_progress": self._swipe_in_progress,
            "transition_offset": self._transition_offset,
        }
