"""
Enrichment services package for extending core music metadata.

This package provides a pluggable system for enriching core metadata with
information from external services like MusicBrainz, Discogs, Last.fm, etc.
"""

from .base import EnrichmentData, EnrichmentRequest, EnrichmentService
from .discogs_service import DiscogsService
from .engine import EnrichmentEngine, enrichment_engine
from .lastfm_service import LastFmService
from .musicbrainz_service import MusicBrainzService
from .setlistfm_service import SetlistFmService

__all__ = [
    "EnrichmentData",
    "EnrichmentRequest",
    "EnrichmentService",
    "EnrichmentEngine",
    "MusicBrainzService",
    "DiscogsService",
    "LastFmService",
    "SetlistFmService",
    "enrichment_engine",
]
