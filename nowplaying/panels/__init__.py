"""
Content panels package for the music discovery interface.

This package provides the base classes and built-in panel implementations
for the swipeable content interface.
"""

from .acoustid_panel import AcoustIDPanel
from .album_enrichment_panel import AlbumEnrichmentPanel
from .album_info_panel import AlbumInfoPanel
from .artist_enrichment_panel import ArtistEnrichmentPanel
from .artist_info_panel import ArtistInfoPanel
from .base import ContentContext, ContentPanel, ContentPanelRegistry, PanelInfo  # Base classes
from .cover_art_panel import CoverArtPanel
from .debug_panel import DebugPanel
from .discography_panel import DiscographyPanel
from .discogs_panel import DiscogsPanel
from .lastfm_panel import LastFmPanel
from .lyrics_panel import LyricsPanel
from .musicbrainz_panel import MusicBrainzPanel
from .now_playing_panel import NowPlayingPanel
from .registry import content_panel_registry
from .service_status_panel import ServiceStatusPanel
from .social_stats_panel import SocialStatsPanel
from .song_enrichment_panel import SongEnrichmentPanel
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
    "MusicBrainzPanel",
    "DiscogsPanel",
    "LastFmPanel",
    "LyricsPanel",
    "AcoustIDPanel",
    "ArtistInfoPanel",
    "AlbumInfoPanel",
    "ArtistEnrichmentPanel",
    "AlbumEnrichmentPanel",
    "SongEnrichmentPanel",
    "DiscographyPanel",
    "SocialStatsPanel",
    "ServiceStatusPanel",
    # Registry instance
    "content_panel_registry",
]
