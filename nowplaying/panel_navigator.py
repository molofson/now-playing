"""
Navigation controller for swipeable content panels.

Handles left-right swipe navigation between registered content panels,
manages the hold/release functionality for exploration contexts.
"""

import time
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
        """Initialize the panel navigator."""
        self.registry = content_panel_registry
        self._current_panel_index = 0
        self._available_panels: List[ContentPanel] = []

        # Enhanced swipe detection
        self._swipe_start_pos: Optional[Tuple[int, int]] = None
        self._swipe_start_time: Optional[float] = None
        self._swipe_threshold = 50  # Minimum distance for swipe
        self._swipe_velocity_threshold = 100  # Minimum velocity for momentum swipes (pixels/second)
        self._swipe_in_progress = False
        self._last_swipe_pos: Optional[Tuple[int, int]] = None
        self._last_swipe_time: Optional[float] = None

        # Enhanced panel transition animation
        self._transition_offset = 0.0
        self._transition_speed = 12.0  # Animation speed (higher = faster)
        self._transition_easing = 0.85  # Easing factor for smooth transitions
        self._is_transitioning = False
        self._target_panel_index = 0

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
            "target_index": self._target_panel_index if self._is_transitioning else self._current_panel_index,
            "total_panels": len(self._available_panels),
            "current_panel_id": current.info.id if current else None,
            "current_panel_name": current.info.name if current else None,
            "has_held_context": self.registry.has_held_context(),
            "can_swipe_left": self._current_panel_index > 0,
            "can_swipe_right": self._current_panel_index < len(self._available_panels) - 1,
            "is_transitioning": self._is_transitioning,
            "transition_progress": 1.0 - abs(self._transition_offset) if self._is_transitioning else 1.0,
        }

    def navigate_to_panel(self, panel_id: str) -> bool:
        """Navigate directly to a panel by ID."""
        for i, panel in enumerate(self._available_panels):
            if panel.info.id == panel_id:
                self._current_panel_index = i
                return True
        return False

    def navigate_left(self) -> bool:
        """Navigate to previous panel with smooth transition."""
        if self._current_panel_index > 0:
            self._start_transition(self._current_panel_index - 1)
            return True
        return False

    def navigate_right(self) -> bool:
        """Navigate to next panel with smooth transition."""
        if self._current_panel_index < len(self._available_panels) - 1:
            self._start_transition(self._current_panel_index + 1)
            return True
        return False

    def _start_transition(self, target_index: int) -> None:
        """Start a smooth transition to the target panel."""
        if target_index == self._current_panel_index:
            return

        self._target_panel_index = target_index
        self._is_transitioning = True
        # Direction determines initial offset direction
        if target_index > self._current_panel_index:
            self._transition_offset = -1.0  # Moving right, start from left
        else:
            self._transition_offset = 1.0   # Moving left, start from right

    def update_transitions(self, dt: float) -> None:
        """Update transition animations. Call this each frame with delta time."""
        if not self._is_transitioning:
            return

        # Smooth easing toward target (0.0)
        self._transition_offset *= self._transition_easing
        
        # Check if transition is complete (close enough to target)
        if abs(self._transition_offset) < 0.01:
            self._transition_offset = 0.0
            self._is_transitioning = False
            self._current_panel_index = self._target_panel_index

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
                self._swipe_start_time = time.time()
                self._swipe_in_progress = True
                self._last_swipe_pos = event.pos
                self._last_swipe_time = self._swipe_start_time
                return True

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1 and self._swipe_in_progress:
                self._handle_swipe_end(event.pos, time.time())
                self._reset_swipe_state()
                return True

        elif event.type == pygame.MOUSEMOTION and self._swipe_in_progress:
            # Track mouse movement for velocity calculation
            current_time = time.time()
            self._last_swipe_pos = event.pos
            self._last_swipe_time = current_time
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
            self._swipe_start_time = time.time()
            self._swipe_in_progress = True
            self._last_swipe_pos = self._swipe_start_pos
            self._last_swipe_time = self._swipe_start_time
            return True

        elif hasattr(pygame, "FINGERUP") and event.type == pygame.FINGERUP and self._swipe_in_progress:
            end_pos = (
                event.x * pygame.display.get_surface().get_width(),
                event.y * pygame.display.get_surface().get_height(),
            )
            self._handle_swipe_end(end_pos, time.time())
            self._reset_swipe_state()
            return True

        elif hasattr(pygame, "FINGERMOTION") and event.type == pygame.FINGERMOTION and self._swipe_in_progress:
            current_pos = (
                event.x * pygame.display.get_surface().get_width(),
                event.y * pygame.display.get_surface().get_height(),
            )
            current_time = time.time()
            self._last_swipe_pos = current_pos
            self._last_swipe_time = current_time
            return True

        return False

    def _handle_swipe_end(self, end_pos: Tuple[int, int], end_time: float) -> None:
        """Handle end of swipe gesture with velocity detection."""
        if not self._swipe_start_pos or not self._swipe_start_time:
            return

        # Calculate total distance and time
        dx = end_pos[0] - self._swipe_start_pos[0]
        dy = end_pos[1] - self._swipe_start_pos[1]
        total_distance = (dx ** 2 + dy ** 2) ** 0.5
        total_time = end_time - self._swipe_start_time

        # Calculate velocity (pixels per second)
        velocity = total_distance / max(total_time, 0.001)  # Avoid division by zero

        # Determine if this is a horizontal swipe
        is_horizontal_swipe = abs(dx) > abs(dy)
        
        # Check for swipe based on distance or velocity
        distance_threshold_met = abs(dx) > self._swipe_threshold if is_horizontal_swipe else abs(dy) > self._swipe_threshold
        velocity_threshold_met = velocity > self._swipe_velocity_threshold

        if is_horizontal_swipe and (distance_threshold_met or velocity_threshold_met):
            # Horizontal swipe navigation
            if dx > 0:
                # Swipe right -> go to previous panel
                self.navigate_left()
            else:
                # Swipe left -> go to next panel
                self.navigate_right()

        elif not is_horizontal_swipe and (distance_threshold_met or velocity_threshold_met):
            # Vertical swipe for hold/release gesture
            if dy < 0:
                # Swipe up -> hold current context
                self._hold_current_context()
            else:
                # Swipe down -> release held context
                self._release_held_context()

    def _reset_swipe_state(self) -> None:
        """Reset swipe tracking state."""
        self._swipe_start_pos = None
        self._swipe_start_time = None
        self._swipe_in_progress = False
        self._last_swipe_pos = None
        self._last_swipe_time = None

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
        """Render enhanced navigation hints/indicators with visual feedback."""
        font = pygame.font.Font(None, 16)
        hint_color = (140, 140, 140)
        active_color = (180, 220, 255)

        # Panel indicator
        panel_info = self.get_panel_info()
        current = self.get_current_panel()

        if current:
            # Panel name and position with transition status
            if panel_info["is_transitioning"]:
                progress = panel_info["transition_progress"]
                panel_text = f"{current.info.name} ({panel_info['current_index'] + 1}/{panel_info['total_panels']}) [transitioning {progress:.0%}]"
            else:
                panel_text = f"{current.info.name} ({panel_info['current_index'] + 1}/{panel_info['total_panels']})"
            
            panel_surface = font.render(panel_text, True, hint_color)
            surface.blit(panel_surface, (rect.x + 10, rect.bottom - 40))

            # Enhanced navigation hints with visual indicators
            hints = []
            if panel_info["can_swipe_left"]:
                hints.append("← Prev" if not self._swipe_in_progress else "← Prev")
            if panel_info["can_swipe_right"]:
                hints.append("Next →" if not self._swipe_in_progress else "Next →")

            # Context management hints
            if self.registry.has_held_context():
                hints.append("Space: Release 📌")
            else:
                hints.append("Space: Hold")

            # Swipe hints
            hints.append("Swipe: Navigate")
            if panel_info["total_panels"] > 1:
                hints.append("↕ Hold/Release")

            if hints:
                hint_text = " | ".join(hints)
                hint_surface = font.render(hint_text, True, hint_color)
                surface.blit(hint_surface, (rect.x + 10, rect.bottom - 20))

            # Visual panel dots indicator
            self._render_panel_dots(surface, rect, panel_info)

    def _render_panel_dots(self, surface: pygame.Surface, rect: pygame.Rect, panel_info: dict) -> None:
        """Render visual dots indicating current panel position."""
        if panel_info["total_panels"] <= 1:
            return

        dot_size = 6
        dot_spacing = 12
        active_color = (180, 220, 255)
        inactive_color = (80, 80, 80)
        transition_color = (120, 160, 200)

        total_width = (panel_info["total_panels"] - 1) * dot_spacing + dot_size
        start_x = rect.centerx - total_width // 2
        dot_y = rect.bottom - 45

        for i in range(panel_info["total_panels"]):
            dot_x = start_x + i * dot_spacing
            
            # Determine dot color based on state
            if i == panel_info["current_index"]:
                if panel_info["is_transitioning"]:
                    # Blend between active and transition color based on progress
                    progress = panel_info["transition_progress"]
                    color = tuple(
                        int(active_color[j] * progress + transition_color[j] * (1 - progress))
                        for j in range(3)
                    )
                else:
                    color = active_color
            elif panel_info["is_transitioning"] and i == panel_info["target_index"]:
                # Target panel during transition
                progress = panel_info["transition_progress"]
                color = tuple(
                    int(transition_color[j] * progress + inactive_color[j] * (1 - progress))
                    for j in range(3)
                )
            else:
                color = inactive_color

            # Draw dot
            pygame.draw.circle(surface, color, (dot_x + dot_size // 2, dot_y), dot_size // 2)

    def get_transition_info(self) -> dict:
        """Get detailed transition state information."""
        return {
            "is_transitioning": self._is_transitioning,
            "transition_offset": self._transition_offset,
            "current_index": self._current_panel_index,
            "target_index": self._target_panel_index,
            "progress": 1.0 - abs(self._transition_offset) if self._is_transitioning else 1.0,
        }

    def get_navigation_status(self) -> dict:
        """Get detailed navigation status for debugging."""
        return {
            **self.get_panel_info(),
            "registry_status": self.registry.get_registry_status(),
            "swipe_in_progress": self._swipe_in_progress,
            "swipe_start_pos": self._swipe_start_pos,
            "last_swipe_pos": self._last_swipe_pos,
            "transition_info": self.get_transition_info(),
            "swipe_thresholds": {
                "distance": self._swipe_threshold,
                "velocity": self._swipe_velocity_threshold,
            },
        }
