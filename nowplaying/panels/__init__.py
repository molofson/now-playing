"""
Content panels package for the music discovery interface.

This package provides the base classes and built-in panel implementations
for the swipeable content interface.
"""

# Import base classes
from .base import ContentContext, ContentPanel, ContentPanelRegistry, PanelInfo
from .cover_art_panel import CoverArtPanel
from .debug_panel import DebugPanel
from .discovery_panel import DiscoveryPanel
from .discogs_panel import DiscogsPanel
from .lastfm_panel import LastFmPanel
from .musicbrainz_panel import MusicBrainzPanel
from .now_playing_panel import NowPlayingPanel
from .registry import content_panel_registry
from .vu_meter_panel import VUMeterPanel

__all__ = [
    # Base classes
    "ContentContext",
    "PanelInfo",
    "ContentPanel",
    "ContentPanelRegistry",
    # Built-in panels
    "NowPlayingPanel",
    "CoverArtPanel",
    "VUMeterPanel",
    "DebugPanel",
    "DiscoveryPanel",
    "MusicBrainzPanel",
    "DiscogsPanel",
    "LastFmPanel",
    # Registry instance
    "content_panel_registry",
]
