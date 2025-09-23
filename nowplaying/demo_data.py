"""
Demo data generator for testing the music discovery interface.

Provides sample metadata and enrichment data when no real music source is available.
"""

import random
import time
from typing import Dict, Any, List
from datetime import datetime

from .enrichment.base import EnrichmentData
from .panels.base import ContentContext
from .playback_state import PlaybackState


class DemoDataGenerator:
    """Generates realistic demo data for testing the music discovery interface."""
    
    def __init__(self):
        """Initialize the demo data generator."""
        self._demo_tracks = [
            {
                "title": "Moonlight Sonata",
                "artist": "Ludwig van Beethoven",
                "album": "Piano Sonatas Collection",
                "genre": "Classical",
                "year": "1801",
                "duration": "15:32",
                "track_number": "14",
            },
            {
                "title": "Bohemian Rhapsody",
                "artist": "Queen",
                "album": "A Night at the Opera",
                "genre": "Rock",
                "year": "1975",
                "duration": "5:55",
                "track_number": "11",
            },
            {
                "title": "Take Five",
                "artist": "Dave Brubeck Quartet",
                "album": "Time Out",
                "genre": "Jazz",
                "year": "1959",
                "duration": "5:24",
                "track_number": "3",
            },
            {
                "title": "Billie Jean",
                "artist": "Michael Jackson",
                "album": "Thriller",
                "genre": "Pop",
                "year": "1982",
                "duration": "4:54",
                "track_number": "2",
            },
            {
                "title": "Hotel California",
                "artist": "Eagles",
                "album": "Hotel California",
                "genre": "Rock",
                "year": "1976",
                "duration": "6:30",
                "track_number": "1",
            }
        ]
        self._current_track_index = 0
        self._last_change_time = time.time()
        self._demo_enrichment_cache = {}
    
    def get_current_track(self) -> Dict[str, Any]:
        """Get the current demo track metadata."""
        # Change track every 30 seconds in demo mode
        current_time = time.time()
        if current_time - self._last_change_time > 30:
            self._current_track_index = (self._current_track_index + 1) % len(self._demo_tracks)
            self._last_change_time = current_time
        
        return self._demo_tracks[self._current_track_index].copy()
    
    def get_demo_playback_state(self) -> PlaybackState:
        """Get a rotating demo playback state."""
        states = [PlaybackState.PLAYING, PlaybackState.PLAYING, PlaybackState.PAUSED]
        return random.choice(states)
    
    def create_demo_context(self) -> ContentContext:
        """Create a demo content context with current track."""
        track = self.get_current_track()
        context = ContentContext.from_metadata(
            metadata=track,
            state=self.get_demo_playback_state(),
            is_live=True
        )
        
        # Add enrichment data
        context.enrichment_data = self.get_demo_enrichment_data(track)
        return context
    
    def get_demo_enrichment_data(self, track: Dict[str, Any]) -> EnrichmentData:
        """Generate demo enrichment data for a track."""
        track_key = f"{track['artist']}_{track['title']}"
        
        if track_key in self._demo_enrichment_cache:
            return self._demo_enrichment_cache[track_key]
        
        artist = track["artist"]
        genre = track.get("genre", "Unknown")
        
        # Generate contextual similar artists
        similar_artists = self._generate_similar_artists(artist, genre)
        
        # Generate recommendations
        recommended_tracks = self._generate_recommended_tracks(artist, genre)
        
        # Generate recent releases
        recent_releases = self._generate_recent_releases(artist, genre)
        
        enrichment = EnrichmentData(
            # Core IDs (simulated)
            musicbrainz_artist_id=f"mb-{hash(artist) % 100000}",
            musicbrainz_album_id=f"mb-album-{hash(track.get('album', '')) % 100000}",
            discogs_artist_id=f"discogs-{hash(artist) % 100000}",
            spotify_artist_id=f"spotify-{hash(artist) % 100000}",
            
            # Extended metadata
            artist_bio=f"{artist} is a renowned {genre.lower()} artist known for their innovative style and compelling performances.",
            artist_tags=[genre.lower(), "popular", "acclaimed", "influential"],
            similar_artists=similar_artists,
            
            # Discovery data
            recent_releases=recent_releases,
            artist_discography=recommended_tracks,  # Use discography field for recommendations
            
            # Community data
            scrobble_count=random.randint(10000, 1000000),
            popularity_score=random.uniform(60.0, 95.0),
            user_tags=[genre.lower(), "favorite", "classic"],
            
            # Service metadata
            last_updated={
                "musicbrainz": time.time(),
                "discogs": time.time(),
                "lastfm": time.time(),
            }
        )
        
        # Add recommended tracks as a custom attribute (not in the dataclass)
        enrichment.recommended_tracks = recommended_tracks
        
        self._demo_enrichment_cache[track_key] = enrichment
        return enrichment
    
    def _generate_similar_artists(self, artist: str, genre: str) -> List[Dict[str, Any]]:
        """Generate similar artists based on the current artist and genre."""
        base_artists = {
            "Classical": ["Johann Sebastian Bach", "Wolfgang Amadeus Mozart", "Frédéric Chopin", "Johannes Brahms"],
            "Rock": ["Led Zeppelin", "The Rolling Stones", "Pink Floyd", "The Beatles"],
            "Jazz": ["Miles Davis", "John Coltrane", "Ella Fitzgerald", "Duke Ellington"],
            "Pop": ["Madonna", "Prince", "Whitney Houston", "Stevie Wonder"],
        }
        
        artists = base_artists.get(genre, ["Artist A", "Artist B", "Artist C", "Artist D"])
        
        similar = []
        for i, similar_artist in enumerate(artists[:4]):
            if similar_artist != artist:  # Don't include the same artist
                similar.append({
                    "name": similar_artist,
                    "match": random.randint(70, 95),
                    "reason": f"Similar {genre.lower()} style"
                })
        
        return similar
    
    def _generate_recommended_tracks(self, artist: str, genre: str) -> List[Dict[str, Any]]:
        """Generate recommended tracks."""
        track_templates = [
            "Symphony in {key}",
            "Concerto No. {num}",
            "Sonata in {key} Major",
            "Blues in {key}",
            "Love Song #{num}",
            "Rock Anthem {num}",
            "Jazz Standard #{num}",
            "Pop Hit {year}",
        ]
        
        recommendations = []
        for i in range(3):
            template = random.choice(track_templates)
            title = template.format(
                key=random.choice(["C", "D", "E", "F", "G", "A", "B"]),
                num=random.randint(1, 10),
                year=random.randint(1960, 2023)
            )
            
            recommendations.append({
                "title": title,
                "artist": f"Recommended {genre} Artist {i+1}",
                "album": f"Great {genre} Album",
                "match_reason": f"Similar to {artist}",
                "confidence": random.uniform(0.7, 0.95)
            })
        
        return recommendations
    
    def _generate_recent_releases(self, artist: str, genre: str) -> List[Dict[str, Any]]:
        """Generate recent releases."""
        releases = []
        for i in range(2):
            releases.append({
                "title": f"New {genre} Release {i+1}",
                "artist": f"{genre} Artist {i+1}",
                "release_date": "2023",
                "type": random.choice(["album", "single", "EP"]),
                "related_reason": f"Fans of {artist} also like"
            })
        
        return releases


# Global demo data generator instance
demo_data_generator = DemoDataGenerator()