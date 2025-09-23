"""
Enrichment Status panel implementation.

Displays the status of enrichment services and API configuration.
"""

import os

import pygame

from .base import ContentContext, ContentPanel, PanelInfo


class EnrichmentStatusPanel(ContentPanel):
    """Panel for displaying enrichment service status."""

    def __init__(self):
        """Initialize the EnrichmentStatusPanel."""
        super().__init__(
            PanelInfo(
                id="enrichment_status",
                name="Service Status", 
                description="Enrichment service configuration status",
                icon="⚙️",
                category="system",
            )
        )

    def handle_event(self, event: pygame.event.Event) -> bool:  # noqa: U100
        """Handle events (not used)."""
        return False

    def can_display(self, context: ContentContext) -> bool:
        return True  # Always available

    def update_context(self, context: ContentContext) -> None:
        self._context = context

    def render(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        font = pygame.font.Font(None, 22)
        font_small = pygame.font.Font(None, 18)
        y = rect.top + 20
        
        # Title
        title = font.render("Enrichment Service Status", True, (230, 230, 230))
        surface.blit(title, (rect.left + 20, y))
        y += 40
        
        # Check environment variables
        lastfm_key = os.getenv('LASTFM_API_KEY')
        discogs_token = os.getenv('DISCOGS_TOKEN')
        
        services = [
            {
                "name": "MusicBrainz",
                "status": "Always Enabled",
                "color": (100, 200, 100),  # Green
                "description": "Artist, album, and track IDs"
            },
            {
                "name": "Last.fm", 
                "status": "API Enabled" if lastfm_key else "Mock Data Only",
                "color": (100, 200, 100) if lastfm_key else (200, 150, 100),  # Green or Orange
                "description": "Artist bios, tags, similar artists"
            },
            {
                "name": "Discogs",
                "status": "API Enabled" if discogs_token else "Mock Data Only", 
                "color": (100, 200, 100) if discogs_token else (200, 150, 100),  # Green or Orange
                "description": "Artist discographies, release info"
            }
        ]
        
        for service in services:
            # Service name and status
            name_text = font.render(f"{service['name']}:", True, (230, 230, 230))
            surface.blit(name_text, (rect.left + 30, y))
            
            status_text = font.render(service['status'], True, service['color'])
            surface.blit(status_text, (rect.left + 180, y))
            y += 25
            
            # Description
            desc_text = font_small.render(f"  {service['description']}", True, (170, 170, 170))
            surface.blit(desc_text, (rect.left + 40, y))
            y += 30
        
        # Configuration instructions
        y += 20
        if not lastfm_key or not discogs_token:
            config_title = font.render("Configuration:", True, (200, 200, 100))
            surface.blit(config_title, (rect.left + 20, y))
            y += 30
            
            instructions = []
            if not lastfm_key:
                instructions.extend([
                    "For Last.fm API access:",
                    "  export LASTFM_API_KEY=\"your_key\"",
                    ""
                ])
            if not discogs_token:
                instructions.extend([
                    "For Discogs API access:",
                    "  export DISCOGS_TOKEN=\"your_token\"",
                    ""
                ])
            instructions.append("See API_CONFIGURATION.md for details")
            
            for instruction in instructions:
                color = (140, 140, 140) if instruction.startswith("  ") else (170, 170, 170)
                inst_text = font_small.render(instruction, True, color)
                surface.blit(inst_text, (rect.left + 30, y))
                y += 20
                
                if y > rect.bottom - 40:
                    break