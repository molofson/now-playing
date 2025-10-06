"""Unit tests for AcoustID and Lyrics panels."""

import os

import pygame

from nowplaying.panels.acoustid_panel import AcoustIDPanel
from nowplaying.panels.base import ContentContext
from nowplaying.panels.lyrics_panel import LyricsPanel
from nowplaying.playback_state import PlaybackState


def setup_module():
    """Prepare pygame for headless rendering tests."""
    # Use the SDL dummy video driver for headless tests
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.display.init()
    pygame.font.init()


def teardown_module():
    """Tear down pygame subsystems used in tests."""
    try:
        pygame.font.quit()
        pygame.display.quit()
    except Exception:
        pass


def make_surface():
    """Create a small pygame Surface for rendering tests."""
    return pygame.Surface((200, 100))


def test_acoustid_panel_display_and_render():
    """Verify AcoustID panel can_display and render without errors."""
    panel = AcoustIDPanel()
    ctx = ContentContext(
        artist="Test Artist", title="Test Title", track_id="track-123", playback_state=PlaybackState.NO_SESSION
    )

    # No enrichment data -> can_display should be True because track_id is present
    assert panel.can_display(ctx)

    # Render should not raise
    surf = make_surface()
    rect = surf.get_rect()
    panel.update_context(ctx)
    panel.render(surf, rect)

    # If enrichment data provides acoustid_id the panel should prefer that
    ctx.enrichment_data = {"acoustid_id": "acoustid:placeholder:track-123"}
    assert panel.can_display(ctx)
    panel.update_context(ctx)
    panel.render(surf, rect)


def test_lyrics_panel_display_and_render():
    """Verify Lyrics panel can_display and render an excerpt without errors."""
    panel = LyricsPanel()
    ctx = ContentContext(artist="Test Artist", title="Test Title", playback_state=PlaybackState.NO_SESSION)

    # No lyrics -> cannot display
    assert not panel.can_display(ctx)

    # With lyrics in enrichment_data -> can display
    ctx.enrichment_data = {"song_lyrics": "Line one\nLine two\nLine three"}
    assert panel.can_display(ctx)

    surf = make_surface()
    rect = surf.get_rect()
    panel.update_context(ctx)
    panel.render(surf, rect)
