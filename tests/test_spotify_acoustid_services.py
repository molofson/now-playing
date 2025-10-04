"""Tests for the Spotify and AcoustID skeleton enrichment services."""

from nowplaying.enrichment import enrichment_engine


def test_services_registered():
    """Ensure the engine has both services registered."""
    services = enrichment_engine.services
    assert "spotify" in services
    assert "acoustid" in services


def test_services_disabled_by_default(monkeypatch):
    """Without env vars, the services should be disabled by default."""
    monkeypatch.delenv("SPOTIFY_CLIENT_ID", raising=False)
    monkeypatch.delenv("SPOTIFY_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("ACOUSTID_API_KEY", raising=False)

    from nowplaying.enrichment.engine import EnrichmentEngine

    engine = EnrichmentEngine()
    assert engine.services["spotify"].enabled is False
    assert engine.services["acoustid"].enabled is False
