#!/usr/bin/env python3
"""Simple test to verify the enrichment panels work with MCP data."""

import sys
import time

# Add project root to path
script_dir = "/home/molofson/repos/now-playing"
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from nowplaying.panels import (
    AlbumInfoPanel,
    ArtistInfoPanel,
    ContentContext,
    ServiceStatusPanel,
    SocialStatsPanel,
)


def create_sample_enrichment_data():
    """Create sample enrichment data similar to what MCP returns."""
    return {
        "musicbrainz_artist_id": "b10bbbfc-cf9e-42e0-be17-e2c3e1d2600d",
        "musicbrainz_album_id": "d6010be3-98f8-422c-a6c9-787e2e491e58",
        "discogs_artist_id": "discogs-artist-6135",
        "discogs_release_id": "discogs-release-8712",
        "artist_bio": "The Beatles were an English rock band formed in Liverpool in 1960.",
        "artist_tags": ["rock", "pop", "british", "60s"],
        "similar_artists": [{"name": "The Rolling Stones", "match": 0.85}, {"name": "The Who", "match": 0.78}],
        "album_reviews": [{"source": "Rolling Stone", "rating": 10, "text": "Abbey Road is the Beatles' masterpiece."}],
        "album_credits": [{"role": "producer", "artist": "George Martin"}],
        "artist_discography": [
            {"title": "Abbey Road", "year": "1969", "format": "LP"},
            {"title": "Sgt. Pepper's", "year": "1967", "format": "LP"},
        ],
        "scrobble_count": 586135,
        "popularity_score": 95.2,
        "user_tags": ["classic rock", "favorites"],
        "last_updated": {
            "musicbrainz": time.time() - 3600,
            "discogs": time.time() - 7200,
            "lastfm": time.time() - 1800,
        },
        "service_errors": {},
    }


def test_panels():
    """Test that panels can be created and updated with enrichment data."""
    print("Testing enrichment display panels..")

    # Create context with enrichment data
    context = ContentContext(artist="The Beatles", album="Abbey Road", title="Come Together")
    context.enrichment_data = create_sample_enrichment_data()

    # Create panels
    panels = [
        ("Artist Info", ArtistInfoPanel()),
        ("Album Info", AlbumInfoPanel()),
        ("Social Stats", SocialStatsPanel()),
        ("Service Status", ServiceStatusPanel()),
    ]

    print(f"Created {len(panels)} panels")

    # Test panel creation and context updates
    for name, panel in panels:
        print(f"Testing {name} panel..")
        panel.update_context(context)
        print(f"  ✓ Can display: {panel.can_display(context)}")
        print(f"  ✓ Panel info: {panel.info.name} - {panel.info.description}")

    print("\nAll panels created and updated successfully!")
    print("\nPanel Features:")
    print("• Artist Info: Biography, tags, similar artists")
    print("• Album Info: Reviews, credits, discography")
    print("• Social Stats: Scrobble counts, popularity, user tags")
    print("• Service Status: Data freshness, errors, completeness")


if __name__ == "__main__":
    test_panels()
