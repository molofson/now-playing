#!/usr/bin/env python3
"""
Touchscreen demo for MCP service data display panels.

This script demonstrates the enrichment data display panels
designed for touchscreen devices with no keyboard.
"""

import time

import pygame

from nowplaying.panels import (
    AlbumInfoPanel,
    ArtistInfoPanel,
    ContentContext,
    ServiceStatusPanel,
    SocialStatsPanel,
)

# Sample enrichment data from MCP server
SAMPLE_ENRICHMENT_DATA = {
    "musicbrainz_artist_id": "b10bbbfc-cf9e-42e0-be17-e2c3e1d2600d",
    "musicbrainz_album_id": "d6010be3-98f8-422c-a6c9-787e2e491e58",
    "discogs_artist_id": "discogs-artist-6135",
    "discogs_release_id": "discogs-release-8712",
    "artist_bio": "The Beatles were an English rock band formed in Liverpool in 1960. With members John Lennon, Paul McCartney, George Harrison and Ringo Starr, they became widely regarded as the foremost and most influential music band in history.",
    "artist_tags": ["rock", "pop", "british", "60s", "legendary"],
    "similar_artists": [
        {"name": "The Rolling Stones", "match": 0.85},
        {"name": "The Who", "match": 0.78},
        {"name": "Bob Dylan", "match": 0.72},
    ],
    "album_reviews": [
        {"source": "Rolling Stone", "rating": 10, "text": "Abbey Road is the Beatles' masterpiece."},
        {"source": "AllMusic", "rating": 10, "text": "One of the greatest albums ever made."},
    ],
    "album_credits": [{"role": "producer", "artist": "George Martin"}, {"role": "engineer", "artist": "Geoff Emerick"}],
    "artist_discography": [
        {"title": "Abbey Road", "year": "1969", "format": "LP"},
        {"title": "Sgt. Pepper's", "year": "1967", "format": "LP"},
    ],
    "scrobble_count": 586135,
    "popularity_score": 95.5,
    "user_tags": ["classic", "favorite", "masterpiece"],
    "last_updated": {"musicbrainz": time.time() - 3600, "discogs": time.time() - 7200, "lastfm": time.time() - 1800},
    "service_errors": {},
}


def create_touchscreen_demo():
    """Create a fullscreen touchscreen demo of MCP data panels."""
    pygame.init()

    # Fullscreen for touchscreen
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    pygame.display.set_caption("MCP Music Data Display")

    # Hide mouse cursor
    pygame.mouse.set_visible(False)

    # Get screen dimensions
    screen_width, screen_height = screen.get_size()

    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 28)
    title_font = pygame.font.Font(None, 36)
    button_font = pygame.font.Font(None, 32)

    # Colors
    DARK_BG = (10, 10, 14)
    PANEL_BG = (20, 20, 24)
    BUTTON_COLOR = (120, 170, 255)
    BUTTON_HOVER = (150, 200, 255)
    TEXT_COLOR = (230, 230, 230)
    ACCENT_COLOR = (120, 170, 255)
    EXIT_COLOR = (255, 120, 120)

    # Create context with enrichment data
    context = ContentContext(artist="The Beatles", album="Abbey Road", title="Come Together", source="touchscreen_demo")
    context.enrichment_data = SAMPLE_ENRICHMENT_DATA

    # Create panels
    panels = [ArtistInfoPanel(), AlbumInfoPanel(), SocialStatsPanel(), ServiceStatusPanel()]

    # Update panels with context
    for panel in panels:
        panel.update_context(context)

    # Layout
    current_panel = 0
    auto_advance = True
    last_advance = time.time()
    ADVANCE_INTERVAL = 15.0  # 15 seconds for touchscreen viewing

    # Button layout - bottom of screen
    button_height = 80
    button_y = screen_height - button_height - 20

    prev_button = pygame.Rect(20, button_y, 150, button_height)
    next_button = pygame.Rect(190, button_y, 150, button_height)
    auto_button = pygame.Rect(360, button_y, 200, button_height)
    exit_button = pygame.Rect(screen_width - 120, button_y, 100, button_height)

    running = True

    while running:
        current_time = time.time()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()

                # Exit button
                if exit_button.collidepoint(mouse_pos):
                    running = False

                # Navigation buttons
                elif prev_button.collidepoint(mouse_pos):
                    current_panel = (current_panel - 1) % len(panels)
                    last_advance = current_time
                elif next_button.collidepoint(mouse_pos):
                    current_panel = (current_panel + 1) % len(panels)
                    last_advance = current_time
                elif auto_button.collidepoint(mouse_pos):
                    auto_advance = not auto_advance
                    last_advance = current_time

                # Tap anywhere else to advance
                else:
                    current_panel = (current_panel + 1) % len(panels)
                    last_advance = current_time

        # Auto-advance
        if auto_advance and (current_time - last_advance) >= ADVANCE_INTERVAL:
            current_panel = (current_panel + 1) % len(panels)
            last_advance = current_time

        # Clear screen
        screen.fill(DARK_BG)

        # Draw current panel
        panel = panels[current_panel]
        panel_rect = pygame.Rect(20, 80, screen_width - 40, screen_height - 200)
        pygame.draw.rect(screen, PANEL_BG, panel_rect, border_radius=12)

        # Panel content
        content_rect = pygame.Rect(40, 100, screen_width - 80, screen_height - 240)
        panel.render(screen, content_rect)

        # Panel title
        title_text = title_font.render(panel.info.name, True, ACCENT_COLOR)
        screen.blit(title_text, (40, 30))

        # Subtitle
        subtitle_text = font.render(panel.info.description, True, TEXT_COLOR)
        screen.blit(subtitle_text, (40, 65))

        # Draw buttons
        mouse_pos = pygame.mouse.get_pos()

        # Previous button
        prev_color = BUTTON_HOVER if prev_button.collidepoint(mouse_pos) else BUTTON_COLOR
        pygame.draw.rect(screen, prev_color, prev_button, border_radius=12)
        prev_text = button_font.render("◀", True, (0, 0, 0))
        text_rect = prev_text.get_rect(center=prev_button.center)
        screen.blit(prev_text, text_rect)

        # Next button
        next_color = BUTTON_HOVER if next_button.collidepoint(mouse_pos) else BUTTON_COLOR
        pygame.draw.rect(screen, next_color, next_button, border_radius=12)
        next_text = button_font.render("▶", True, (0, 0, 0))
        text_rect = next_text.get_rect(center=next_button.center)
        screen.blit(next_text, text_rect)

        # Auto button
        auto_color = BUTTON_HOVER if auto_button.collidepoint(mouse_pos) else BUTTON_COLOR
        pygame.draw.rect(screen, auto_color, auto_button, border_radius=12)
        auto_text = button_font.render("AUTO" if auto_advance else "MANUAL", True, (0, 0, 0))
        text_rect = auto_text.get_rect(center=auto_button.center)
        screen.blit(auto_text, text_rect)

        # Exit button
        exit_btn_color = (255, 150, 150) if exit_button.collidepoint(mouse_pos) else EXIT_COLOR
        pygame.draw.rect(screen, exit_btn_color, exit_button, border_radius=12)
        exit_text = button_font.render("✕", True, (0, 0, 0))
        text_rect = exit_text.get_rect(center=exit_button.center)
        screen.blit(exit_text, text_rect)

        # Panel indicators
        indicator_y = button_y - 40
        for i in range(len(panels)):
            indicator_color = ACCENT_COLOR if i == current_panel else (80, 80, 80)
            indicator_x = screen_width // 2 + (i - len(panels) // 2) * 40
            pygame.draw.circle(screen, indicator_color, (indicator_x, indicator_y), 8)

        # Status text
        if auto_advance:
            time_left = int(ADVANCE_INTERVAL - (current_time - last_advance))
            status_text = font.render(f"Auto-advance in {time_left}s • Tap to advance", True, (150, 150, 150))
        else:
            status_text = font.render("Manual mode • Tap to advance", True, (150, 150, 150))
        screen.blit(status_text, (20, screen_height - 15))

        pygame.display.flip()
        clock.tick(30)

    pygame.quit()


if __name__ == "__main__":
    create_touchscreen_demo()
