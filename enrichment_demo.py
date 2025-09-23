#!/usr/bin/env python3
"""
Music Discovery Enrichment Demo

A command-line demo script that shows the enrichment system in action
without requiring pygame or GUI components.
"""

import asyncio
import sys
import time
from typing import Dict, Any

# Add project root to path
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nowplaying.config_loader import load_config, print_config_status
from nowplaying.enrichment import EnrichmentRequest, EnrichmentEngine
from nowplaying.enrichment.base import EnrichmentData
from nowplaying.content_context import ContentContext
from nowplaying.playback_state import PlaybackState


def create_sample_context(artist: str, album: str, title: str) -> ContentContext:
    """Create a sample content context for testing."""
    return ContentContext(
        artist=artist,
        album=album,
        title=title,
        playback_state=PlaybackState.PLAYING,
        source="demo"
    )


def print_enrichment_results(enrichment: EnrichmentData, artist: str) -> None:
    """Pretty print enrichment results."""
    print(f"\n🎵 Enrichment Results for: {artist}")
    print("=" * 60)
    
    # Service status
    if enrichment.last_updated:
        print("📡 Data Sources:")
        for service, timestamp in enrichment.last_updated.items():
            time_str = time.strftime("%H:%M:%S", time.localtime(timestamp))
            print(f"  ✓ {service.title()}: {time_str}")
    
    if enrichment.service_errors:
        print("❌ Service Errors:")
        for service, error in enrichment.service_errors.items():
            print(f"  ✗ {service.title()}: {error}")
    
    # MusicBrainz data
    if enrichment.musicbrainz_artist_id or enrichment.musicbrainz_album_id:
        print(f"\n🎼 MusicBrainz IDs:")
        if enrichment.musicbrainz_artist_id:
            print(f"  Artist ID: {enrichment.musicbrainz_artist_id}")
        if enrichment.musicbrainz_album_id:
            print(f"  Album ID: {enrichment.musicbrainz_album_id}")
        if enrichment.musicbrainz_track_id:
            print(f"  Track ID: {enrichment.musicbrainz_track_id}")
    
    # Artist information
    if enrichment.artist_bio:
        print(f"\n📝 Artist Biography:")
        # Truncate bio for demo
        bio = enrichment.artist_bio
        if len(bio) > 200:
            bio = bio[:200] + "..."
        print(f"  {bio}")
    
    if enrichment.artist_tags:
        print(f"\n🏷️  Genre Tags:")
        print(f"  {', '.join(enrichment.artist_tags[:8])}")
    
    if enrichment.similar_artists:
        print(f"\n👥 Similar Artists:")
        for artist_info in enrichment.similar_artists[:5]:
            name = artist_info.get("name", "Unknown")
            match = artist_info.get("match", 0)
            if match:
                print(f"  • {name} ({match:.0%} match)")
            else:
                print(f"  • {name}")
    
    # Stats
    if enrichment.scrobble_count:
        print(f"\n📊 Statistics:")
        print(f"  Total plays: {enrichment.scrobble_count:,}")
    
    if enrichment.popularity_score:
        print(f"  Popularity: {enrichment.popularity_score:.1%}")
    
    # Discography
    if enrichment.artist_discography:
        print(f"\n💿 Discography (recent releases):")
        for release in enrichment.artist_discography[:5]:
            title = release.get("title", "Unknown")
            year = release.get("year", "")
            format_info = release.get("format", "")
            
            release_info = title
            if year:
                release_info += f" ({year})"
            if format_info:
                release_info += f" [{format_info}]"
            
            print(f"  • {release_info}")


async def demo_enrichment(artist: str, album: str = "", title: str = "") -> None:
    """Demo the enrichment system with a specific artist/track."""
    print(f"\n🔍 Starting enrichment demo for: {artist}")
    if album:
        print(f"   Album: {album}")
    if title:
        print(f"   Track: {title}")
    
    # Load configuration
    config = load_config()
    
    # Create enrichment engine
    engine = EnrichmentEngine(config=config.enrichment)
    
    # Create context and request
    context = create_sample_context(artist, album, title)
    request = EnrichmentRequest(
        artist=artist,
        album=album,
        title=title,
        context=context
    )
    
    print("⏳ Fetching data from services...")
    start_time = time.time()
    
    # Perform enrichment
    enrichment = await engine.enrich_async(request)
    
    elapsed = time.time() - start_time
    print(f"✅ Enrichment completed in {elapsed:.2f} seconds")
    
    # Display results
    print_enrichment_results(enrichment, artist)
    
    # Cleanup
    engine.shutdown()


def main():
    """Main demo function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Music Discovery Enrichment Demo")
    parser.add_argument("artist", help="Artist name to look up")
    parser.add_argument("--album", help="Album name (optional)")
    parser.add_argument("--title", help="Track title (optional)")
    parser.add_argument("--config", help="Configuration file path")
    parser.add_argument("--show-config", action="store_true", help="Show configuration status")
    
    args = parser.parse_args()
    
    if args.show_config:
        config = load_config(args.config)
        print_config_status(config)
        print("\n" + "="*60)
    
    # Run the demo
    try:
        asyncio.run(demo_enrichment(args.artist, args.album or "", args.title or ""))
    except KeyboardInterrupt:
        print("\n👋 Demo interrupted by user")
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        sys.exit(1)
    
    print(f"\n🎉 Demo completed!")
    print("\nTo run the full GUI app:")
    print("  python3 music_discovery.py --windowed")
    print("\nTo configure API keys:")
    print("  cp config.example.yaml config.yaml")
    print("  # Edit config.yaml with your API keys")


if __name__ == "__main__":
    main()