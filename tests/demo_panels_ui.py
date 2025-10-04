#!/usr/bin/env python3
"""
Test script to demonstrate the new enrichment display panels.

This script shows how the MCP enrichment data can be displayed
using the new panel components.
"""

import sys
import time
from typing import Any, Dict

import pygame

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
    content_panel_registry,
)


def create_sample_enrichment_data() -> Dict[str, Any]:
    """Create sample enrichment data similar to what MCP returns."""
    return {
        "musicbrainz_artist_id": "b10bbbfc-cf9e-42e0-be17-e2c3e1d2600d",
        "musicbrainz_album_id": "d6010be3-98f8-422c-a6c9-787e2e491e58",
        "musicbrainz_track_id": None,
        "discogs_artist_id": "discogs-artist-6135",
        "discogs_release_id": "discogs-release-8712",
        "spotify_artist_id": None,
        "spotify_album_id": None,
        "artist_bio": "The Beatles were an English rock band formed in Liverpool in 1960. With a line-up comprising John Lennon, Paul McCartney, George Harrison and Ringo Starr, they are regarded as the most influential band of all time.",
        "artist_tags": ["rock", "pop", "british", "60s", "legendary", "innovative"],
        "similar_artists": [
            {"name": "The Rolling Stones", "match": 0.85},
            {"name": "The Who", "match": 0.78},
            {"name": "Bob Dylan", "match": 0.72},
            {"name": "The Beach Boys", "match": 0.68},
            {"name": "Led Zeppelin", "match": 0.65},
        ],
        "album_reviews": [
            {
                "source": "Rolling Stone",
                "rating": 10,
                "text": "Abbey Road is the Beatles' masterpiece, a flawless blend of rock, pop, and orchestral elements.",
            },
            {
                "source": "AllMusic",
                "rating": 9.5,
                "text": "One of the greatest albums ever made, showcasing the band's incredible versatility.",
            },
        ],
        "album_credits": [
            {"role": "producer", "artist": "George Martin"},
            {"role": "engineer", "artist": "Geoff Emerick"},
            {"role": "photography", "artist": "Iain Macmillan"},
        ],
        "tour_dates": [],  # No current tours
        "recent_releases": [],
        "artist_discography": [
            {"title": "Abbey Road", "year": "1969", "format": "LP"},
            {"title": "Sgt. Pepper's Lonely Hearts Club Band", "year": "1967", "format": "LP"},
            {"title": "Revolver", "year": "1966", "format": "LP"},
            {"title": "Rubber Soul", "year": "1965", "format": "LP"},
        ],
        "scrobble_count": 586135,
        "popularity_score": 95.2,
        "user_tags": ["classic rock", "favorites", "masterpiece"],
        "last_updated": {
            "musicbrainz": time.time() - 3600,  # 1 hour ago
            "discogs": time.time() - 7200,  # 2 hours ago
            "lastfm": time.time() - 1800,  # 30 minutes ago
        },
        "service_errors": {},
    }


def test_panels():
    """Test the enrichment panels with touchscreen navigation."""
    pygame.init()

    # Enable touchscreen support - use fullscreen for touch devices
    screen = pygame.display.set_mode((1200, 800), pygame.FULLSCREEN)
    pygame.display.set_caption("MCP Enrichment Data Display")

    # Hide mouse cursor for touchscreen experience
    pygame.mouse.set_visible(False)

    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 24)
    button_font = pygame.font.Font(None, 32)

    # Colors
    DARK_BG = (10, 10, 14)
    BUTTON_COLOR = (120, 170, 255)
    BUTTON_HOVER = (150, 200, 255)
    TEXT_COLOR = (230, 230, 230)
    EXIT_BUTTON_COLOR = (255, 120, 120)

    # Create context with enrichment data
    context = ContentContext(artist="The Beatles", album="Abbey Road", title="Come Together")
    context.enrichment_data = create_sample_enrichment_data()

    # Create panels
    panels = [ArtistInfoPanel(), AlbumInfoPanel(), SocialStatsPanel(), ServiceStatusPanel()]

    # Register panels
    for panel in panels:
        content_panel_registry.register_panel(panel)

    # Update panels with context
    for panel in panels:
        panel.update_context(context)

    running = True
    current_panel = 0
    auto_advance = True  # Auto-advance every 10 seconds
    last_advance = time.time()
    ADVANCE_INTERVAL = 10.0

    # Touch button areas
    prev_button = pygame.Rect(50, 720, 150, 60)
    next_button = pygame.Rect(220, 720, 150, 60)
    auto_button = pygame.Rect(400, 720, 200, 60)
    exit_button = pygame.Rect(1050, 720, 100, 60)  # Exit button in top-right

    while running:
        current_time = time.time()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()

                # Check exit button (top-right corner)
                if exit_button.collidepoint(mouse_pos):
                    running = False

                # Check navigation buttons
                elif prev_button.collidepoint(mouse_pos):
                    current_panel = (current_panel - 1) % len(panels)
                    last_advance = current_time
                elif next_button.collidepoint(mouse_pos):
                    current_panel = (current_panel + 1) % len(panels)
                    last_advance = current_time
                elif auto_button.collidepoint(mouse_pos):
                    auto_advance = not auto_advance
                    last_advance = current_time

                # Check main panel area for tap-to-advance
                panel_area = pygame.Rect(50, 100, 1100, 600)
                if panel_area.collidepoint(mouse_pos):
                    current_panel = (current_panel + 1) % len(panels)
                    last_advance = current_time

        # Auto-advance if enabled
        if auto_advance and (current_time - last_advance) >= ADVANCE_INTERVAL:
            current_panel = (current_panel + 1) % len(panels)
            last_advance = current_time

        # Clear screen
        screen.fill(DARK_BG)

        # Draw current panel
        panel = panels[current_panel]
        panel_rect = pygame.Rect(50, 100, 1100, 600)
        panel.render(screen, panel_rect)

        # Draw panel title
        title_text = font.render(f"{panel.info.name} - {panel.info.description}", True, TEXT_COLOR)
        screen.blit(title_text, (50, 60))

        # Draw navigation buttons
        mouse_pos = pygame.mouse.get_pos()

        # Previous button
        prev_color = BUTTON_HOVER if prev_button.collidepoint(mouse_pos) else BUTTON_COLOR
        pygame.draw.rect(screen, prev_color, prev_button, border_radius=8)
        prev_text = button_font.render("◀ PREV", True, (0, 0, 0))
        text_rect = prev_text.get_rect(center=prev_button.center)
        screen.blit(prev_text, text_rect)

        # Next button
        next_color = BUTTON_HOVER if next_button.collidepoint(mouse_pos) else BUTTON_COLOR
        pygame.draw.rect(screen, next_color, next_button, border_radius=8)
        next_text = button_font.render("NEXT ▶", True, (0, 0, 0))
        text_rect = next_text.get_rect(center=next_button.center)
        screen.blit(next_text, text_rect)

        # Auto-advance button
        auto_color = BUTTON_HOVER if auto_button.collidepoint(mouse_pos) else BUTTON_COLOR
        pygame.draw.rect(screen, auto_color, auto_button, border_radius=8)
        auto_text = button_font.render(f"{'⏸' if auto_advance else '▶'} AUTO", True, (0, 0, 0))
        text_rect = auto_text.get_rect(center=auto_button.center)
        screen.blit(auto_text, text_rect)

        # Exit button
        exit_color = (255, 150, 150) if exit_button.collidepoint(mouse_pos) else EXIT_BUTTON_COLOR
        pygame.draw.rect(screen, exit_color, exit_button, border_radius=8)
        exit_text = button_font.render("✕", True, (0, 0, 0))
        text_rect = exit_text.get_rect(center=exit_button.center)
        screen.blit(exit_text, text_rect)

        # Draw panel indicator dots
        dot_y = 690
        for i in range(len(panels)):
            dot_color = BUTTON_COLOR if i == current_panel else (80, 80, 80)
            dot_x = 650 + i * 30
            pygame.draw.circle(screen, dot_color, (dot_x, dot_y), 8)

        # Draw instructions
        if auto_advance:
            time_left = int(ADVANCE_INTERVAL - (current_time - last_advance))
            instr_text = font.render(f"Tap screen to advance • Auto-advance in {time_left}s", True, (150, 150, 150))
        else:
            instr_text = font.render("Tap screen or use buttons to navigate • ✕ to exit", True, (150, 150, 150))
        screen.blit(instr_text, (50, 750))

        pygame.display.flip()
        clock.tick(30)

    pygame.quit()


if __name__ == "__main__":
    test_panels()
