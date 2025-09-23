"""
Recommendations panel for music discovery.

Displays recommended songs, similar artists, and discovery suggestions
based on the current track and enrichment data.
"""

import pygame
from typing import Dict, List, Any, Optional

from .base import ContentContext, ContentPanel, PanelInfo


class RecommendationsPanel(ContentPanel):
    """Panel for displaying music recommendations and similar artists."""

    def __init__(self):
        """Initialize the RecommendationsPanel."""
        super().__init__(
            PanelInfo(
                id="recommendations",
                name="Discover",
                description="Music recommendations and similar artists",
                icon="🔍",
                category="discovery",
            )
        )
        self._font = None
        self._title_font = None
        
    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handle events (not used currently)."""
        return False

    def can_display(self, context: ContentContext) -> bool:
        """This panel can always display recommendations."""
        return True

    def update_context(self, context: ContentContext) -> None:
        """Update the context for recommendations."""
        self._context = context

    def _get_demo_recommendations(self) -> Dict[str, List[Dict[str, Any]]]:
        """Generate demo recommendations when no enrichment data is available."""
        if not self._context or not hasattr(self._context, 'metadata'):
            return {
                "similar_artists": [
                    {"name": "Sample Artist 1", "match": 85},
                    {"name": "Sample Artist 2", "match": 78},
                    {"name": "Sample Artist 3", "match": 72},
                ],
                "recommended_tracks": [
                    {"title": "Demo Track 1", "artist": "Demo Artist", "album": "Demo Album"},
                    {"title": "Demo Track 2", "artist": "Another Artist", "album": "Another Album"},
                ]
            }
        
        metadata = self._context.metadata
        current_artist = metadata.get('artist', 'Unknown Artist')
        current_genre = metadata.get('genre', 'Unknown')
        
        # Generate contextual demo data
        return {
            "similar_artists": [
                {"name": f"Artists like {current_artist} #1", "match": 88},
                {"name": f"Artists like {current_artist} #2", "match": 82},
                {"name": f"More {current_genre} Artists", "match": 76},
                {"name": f"Similar {current_genre} Bands", "match": 70},
            ],
            "recommended_tracks": [
                {"title": "Recommended Track 1", "artist": f"Similar to {current_artist}", "album": "Recommended Album"},
                {"title": "You Might Like This", "artist": f"{current_genre} Artist", "album": "Discovery Album"},
                {"title": "Based on Your Taste", "artist": "New Discovery", "album": "Latest Release"},
            ]
        }

    def _get_recommendations_data(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get recommendations from enrichment data or demo data."""
        enrichment = getattr(self._context, "enrichment_data", None) if self._context else None
        
        if enrichment and hasattr(enrichment, 'similar_artists') and enrichment.similar_artists:
            return {
                "similar_artists": enrichment.similar_artists[:5],  # Limit to 5
                "recommended_tracks": getattr(enrichment, 'recommended_tracks', [])[:3],  # Limit to 3
                "recent_releases": getattr(enrichment, 'recent_releases', [])[:3],
            }
        
        return self._get_demo_recommendations()

    def render(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        """Render the recommendations panel."""
        if not self._font:
            self._font = pygame.font.Font(None, 24)
            self._title_font = pygame.font.Font(None, 32)
        
        # Colors
        bg_color = (25, 25, 35)
        title_color = (255, 255, 255)
        subtitle_color = (200, 200, 255)
        text_color = (180, 180, 200)
        highlight_color = (100, 150, 255)
        
        # Fill background
        surface.fill(bg_color, rect)
        
        # Get recommendations data
        recommendations = self._get_recommendations_data()
        
        y = rect.top + 20
        x_margin = 20
        
        # Panel title
        title_text = self._title_font.render("🔍 Music Discovery", True, title_color)
        surface.blit(title_text, (rect.left + x_margin, y))
        y += 50
        
        # Current track info (if available)
        if self._context and hasattr(self._context, 'metadata'):
            metadata = self._context.metadata
            current_info = f"Currently: {metadata.get('artist', 'Unknown')} - {metadata.get('title', 'Unknown')}"
            current_text = self._font.render(current_info, True, subtitle_color)
            surface.blit(current_text, (rect.left + x_margin, y))
            y += 35
        
        # Similar Artists section
        if "similar_artists" in recommendations and recommendations["similar_artists"]:
            section_title = self._font.render("Similar Artists:", True, highlight_color)
            surface.blit(section_title, (rect.left + x_margin, y))
            y += 30
            
            for i, artist in enumerate(recommendations["similar_artists"][:4]):  # Show max 4
                if isinstance(artist, dict):
                    name = artist.get('name', str(artist))
                    match = artist.get('match', '')
                    if match:
                        artist_text = f"• {name} ({match}% match)"
                    else:
                        artist_text = f"• {name}"
                else:
                    artist_text = f"• {str(artist)}"
                
                text_surface = self._font.render(artist_text, True, text_color)
                surface.blit(text_surface, (rect.left + x_margin + 20, y))
                y += 25
        
        y += 15  # Space between sections
        
        # Recommended Tracks section
        if "recommended_tracks" in recommendations and recommendations["recommended_tracks"]:
            section_title = self._font.render("Recommended Tracks:", True, highlight_color)
            surface.blit(section_title, (rect.left + x_margin, y))
            y += 30
            
            for track in recommendations["recommended_tracks"][:3]:  # Show max 3
                if isinstance(track, dict):
                    title = track.get('title', 'Unknown Title')
                    artist = track.get('artist', 'Unknown Artist')
                    track_text = f"♪ {title} - {artist}"
                else:
                    track_text = f"♪ {str(track)}"
                
                text_surface = self._font.render(track_text, True, text_color)
                surface.blit(text_surface, (rect.left + x_margin + 20, y))
                y += 25
        
        # Recent Releases section (if available)
        if "recent_releases" in recommendations and recommendations["recent_releases"]:
            y += 15
            section_title = self._font.render("Recent Releases:", True, highlight_color)
            surface.blit(section_title, (rect.left + x_margin, y))
            y += 30
            
            for release in recommendations["recent_releases"][:2]:  # Show max 2
                if isinstance(release, dict):
                    title = release.get('title', 'Unknown Album')
                    artist = release.get('artist', 'Unknown Artist')
                    release_text = f"🆕 {title} - {artist}"
                else:
                    release_text = f"🆕 {str(release)}"
                
                text_surface = self._font.render(release_text, True, text_color)
                surface.blit(text_surface, (rect.left + x_margin + 20, y))
                y += 25
        
        # Footer with instructions
        footer_y = rect.bottom - 40
        footer_text = "Use ← → to navigate panels • Space to hold context"
        footer_surface = pygame.font.Font(None, 20).render(footer_text, True, (120, 120, 140))
        footer_rect = footer_surface.get_rect()
        footer_rect.centerx = rect.centerx
        footer_rect.y = footer_y
        surface.blit(footer_surface, footer_rect)