"""
AcoustID enrichment service (skeleton).

This skeleton will be fleshed out later to call Chromaprint/AcoustID for fingerprint
based lookups. For now it provides a safe, no-network default that respects
disabled-by-default behavior when no API key is set.
"""

import time
from typing import Optional

from .base import EnrichmentData, EnrichmentRequest, EnrichmentService


class AcoustIDService(EnrichmentService):
    """Skeleton AcoustID enrichment service.

    This placeholder will later use Chromaprint and AcoustID web services to
    resolve fingerprints to music metadata. For now it provides a safe, no-op
    enrichment result and stays disabled unless explicitly configured.
    """

    def __init__(self):
        """Create a new AcoustIDService instance."""
        super().__init__("acoustid", "AcoustID")
        self._api_key = None

    def set_api_key(self, key: str) -> None:
        """Set the AcoustID API key used for lookups."""
        self._api_key = key

    def can_enrich(self, request: EnrichmentRequest) -> bool:
        """Return True if the service can attempt enrichment for the request."""
        return bool(self._api_key and request.duration and request.track_id)

    async def enrich(self, request: EnrichmentRequest) -> Optional[EnrichmentData]:
        """Return placeholder enrichment; no fingerprinting or network calls yet."""
        enrichment = EnrichmentData()
        enrichment.last_updated["acoustid"] = time.time()
        if request.track_id:
            enrichment.acoustid_id = f"acoustid:placeholder:{request.track_id}"

        return enrichment
