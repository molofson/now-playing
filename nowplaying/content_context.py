"""
Pygame-free content context and basic definitions for testing and CLI usage.

This module provides the core content context without pygame dependencies,
allowing the enrichment system to be used independently.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

from .playback_state import PlaybackState


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