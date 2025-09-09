"""
Base classes for content panels in the music discovery interface.

This module provides the core abstractions for swipeable content panels:
- ContentContext: Data class for content context
- PanelInfo: Metadata about a panel
- ContentPanel: Base interface for panel implementations
- ContentPanelRegistry: Registry for managing available panels
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import pygame

from ..playback_state import PlaybackState


@dataclass
class ContentContext:
    """Content context that can be live (auto-updating) or held (user-frozen) for exploration."""

    # Core metadata
    artist: str = ""
    album: str = ""
    title: str = ""
    genre: str = ""
    cover_art_path: Optional[str] = None

    # State info
    playback_state: PlaybackState = PlaybackState.NO_SESSION

    # Extended metadata (for discovery)
    year: Optional[str] = None
    track_number: Optional[str] = None
    album_artist: Optional[str] = None
    composer: Optional[str] = None
    duration: Optional[float] = None

    # Technical/audio info
    bitrate: Optional[str] = None
    format: Optional[str] = None
    audio_levels: Optional[Dict[str, float]] = None  # For VU meters

    # Context management
    is_held: bool = False  # True if user has "pinned" this context for exploration
    held_timestamp: Optional[datetime] = None  # When this context was held
    source: str = "live"  # "live" or "held" or "manual"

    # External content hints (for discovery panes)
    artist_id: Optional[str] = None  # For artist catalog lookups
    album_id: Optional[str] = None  # For album info lookups

    @classmethod
    def from_metadata(cls, metadata: dict, state: PlaybackState, is_live: bool = True) -> "ContentContext":
        """Create context from metadata dict and state."""
        return cls(
            artist=metadata.get("artist", ""),
            album=metadata.get("album", ""),
            title=metadata.get("title", ""),
            genre=metadata.get("genre", ""),
            cover_art_path=metadata.get("cover_art_path"),
            playback_state=state,
            year=metadata.get("year"),
            track_number=metadata.get("track_number"),
            album_artist=metadata.get("album_artist"),
            composer=metadata.get("composer"),
            duration=metadata.get("duration"),
            bitrate=metadata.get("bitrate"),
            format=metadata.get("format"),
            audio_levels=metadata.get("audio_levels"),
            is_held=False,
            source="live" if is_live else "manual",
            artist_id=metadata.get("artist_id"),
            album_id=metadata.get("album_id"),
        )

    def hold(self) -> "ContentContext":
        """Create a held copy of this context for exploration."""
        held_copy = ContentContext(
            artist=self.artist,
            album=self.album,
            title=self.title,
            genre=self.genre,
            cover_art_path=self.cover_art_path,
            playback_state=self.playback_state,
            year=self.year,
            track_number=self.track_number,
            album_artist=self.album_artist,
            composer=self.composer,
            duration=self.duration,
            bitrate=self.bitrate,
            format=self.format,
            audio_levels=self.audio_levels,
            is_held=True,
            held_timestamp=datetime.now(),
            source="held",
            artist_id=self.artist_id,
            album_id=self.album_id,
        )
        return held_copy


@dataclass
class PanelInfo:
    """Metadata about a content panel."""

    id: str
    name: str
    description: str
    icon: str  # Unicode emoji or symbol
    category: str = "general"  # general, debug, discovery, technical, audio, external
    enabled: bool = True
    requires_cover_art: bool = False
    requires_metadata: bool = True
    requires_audio_data: bool = False  # For VU meters, spectrum analyzers
    requires_network: bool = False  # For artist catalogs, tour dates


class ContentPanel(ABC):
    """Base interface for swipeable content panels."""

    def __init__(self, panel_info: PanelInfo):
        """Initialize content panel with panel info."""
        self.panel_info = panel_info
        self._context: Optional[ContentContext] = None

    @property
    def info(self) -> PanelInfo:
        """Get panel info."""
        return self.panel_info

    @abstractmethod
    def update_context(self, context: ContentContext) -> None:
        """Update with new content context (live or held)."""
        self._context = context

    @abstractmethod
    def render(self, surface: pygame.Surface, rect: pygame.Rect) -> None:  # noqa: U100
        """Render the panel to the given surface area."""
        pass

    @abstractmethod
    def handle_event(self, event: pygame.event.Event) -> bool:  # noqa: U100
        """Handle pygame events. Return True if event was consumed."""
        return False

    def can_display(self, context: ContentContext) -> bool:
        """Check if this panel can display the given context."""
        if self.info.requires_metadata and not any([context.artist, context.album, context.title]):
            return False

        if self.info.requires_cover_art and not context.cover_art_path:
            return False

        if self.info.requires_audio_data and not context.audio_levels:
            return False

        return True

    def get_title(self) -> str:
        """Get display title for this panel."""
        return self.info.name

    def get_status_info(self) -> Dict[str, Any]:
        """Get status information for debugging."""
        return {
            "panel_id": self.info.id,
            "name": self.info.name,
            "category": self.info.category,
            "has_context": self._context is not None,
            "can_display": self.can_display(self._context) if self._context else False,
            "context_source": self._context.source if self._context else None,
            "context_is_held": self._context.is_held if self._context else False,
        }

    def supports_hold(self) -> bool:
        """Whether this panel benefits from context holding."""
        # Most panels benefit, but some (like VU meters) work better with live data
        return not self.info.requires_audio_data


class ContentPanelRegistry:
    """Registry for managing available content panels with dual-context support."""

    def __init__(self):
        """Initialize content panel registry."""
        self._panels: Dict[str, ContentPanel] = {}
        self._panel_order: List[str] = []
        self._live_context: Optional[ContentContext] = None
        self._held_context: Optional[ContentContext] = None

    def register_panel(self, panel: ContentPanel) -> None:
        """Register a new content panel."""
        panel_id = panel.info.id
        if panel_id in self._panels:
            raise ValueError(f"Panel with id '{panel_id}' already registered")

        self._panels[panel_id] = panel
        self._panel_order.append(panel_id)

    def unregister_panel(self, panel_id: str) -> bool:
        """Unregister a panel by id."""
        if panel_id in self._panels:
            del self._panels[panel_id]
            self._panel_order.remove(panel_id)
            return True
        return False

    def get_panel(self, panel_id: str) -> Optional[ContentPanel]:
        """Get a panel by id."""
        return self._panels.get(panel_id)

    def get_available_panels(self, context: Optional[ContentContext] = None) -> List[ContentPanel]:
        """Get all available panels, optionally filtered by context compatibility."""
        panels = [self._panels[panel_id] for panel_id in self._panel_order if panel_id in self._panels]

        if context:
            return [panel for panel in panels if panel.info.enabled and panel.can_display(context)]

        return [panel for panel in panels if panel.info.enabled]

    def get_panel_ids(self) -> List[str]:
        """Get ordered list of panel ids."""
        return self._panel_order.copy()

    def get_panels_by_category(self, category: str) -> List[ContentPanel]:
        """Get all panels in a specific category."""
        return [panel for panel in self._panels.values() if panel.info.category == category and panel.info.enabled]

    # === Context Management ===

    def update_live_context(self, context: ContentContext) -> None:
        """Update the live context (what's currently playing)."""
        self._live_context = context

        # Update panels that prefer live data or don't have held context
        for panel in self._panels.values():
            if not panel.supports_hold() or self._held_context is None:
                panel.update_context(context)

    def set_held_context(self, context: ContentContext) -> None:
        """Set the held context for exploration."""
        self._held_context = context.hold()

        # Update panels that support holding with the held context
        for panel in self._panels.values():
            if panel.supports_hold():
                panel.update_context(self._held_context)

    def release_held_context(self) -> None:
        """Release held context and return to live updates."""
        self._held_context = None

        # Update all panels with live context
        if self._live_context:
            for panel in self._panels.values():
                panel.update_context(self._live_context)

    def get_live_context(self) -> Optional[ContentContext]:
        """Get current live context."""
        return self._live_context

    def get_held_context(self) -> Optional[ContentContext]:
        """Get current held context."""
        return self._held_context

    def has_held_context(self) -> bool:
        """Check if there's a held context for exploration."""
        return self._held_context is not None

    def get_registry_status(self) -> Dict[str, Any]:
        """Get status of the entire registry for debugging."""
        return {
            "total_panels": len(self._panels),
            "enabled_panels": len([p for p in self._panels.values() if p.info.enabled]),
            "panel_order": self._panel_order.copy(),
            "categories": {p.info.category for p in self._panels.values()},
            "has_live_context": self._live_context is not None,
            "has_held_context": self._held_context is not None,
            "live_artist": self._live_context.artist if self._live_context else None,
            "held_artist": self._held_context.artist if self._held_context else None,
        }
