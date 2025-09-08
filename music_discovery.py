#!/usr/bin/env python3
"""
Music Discovery Application

A swipeable interface for exploring music content with enriched metadata
from external services. Supports user-extensible panels and plugins.

Usage:
    python3 music_discovery.py [--config CONFIG_FILE] [--windowed] [--fullscreen]
"""

import argparse
import logging
import os
import signal
import sys
from typing import Any, Dict, Optional

# Suppress pygame startup messages
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
os.environ["PYGAME_DETECT_AVX2"] = "0"

import pygame

# Add project root to path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from nowplaying.config import AppConfig
from nowplaying.content_panels import CoverArtPanel, DebugPanel, NowPlayingPanel, VUMeterPanel
from nowplaying.enrichment_services import EnrichmentRequest, enrichment_engine
from nowplaying.metadata_monitor import StateMonitor
from nowplaying.music_views import ContentContext, content_panel_registry
from nowplaying.panel_navigator import PanelNavigator
from nowplaying.playback_state import PlaybackState


class DiscoveryApp:
    """Main music discovery application."""

    def __init__(self, config: AppConfig, windowed: bool = False):
        """Initialize the discovery application."""
        self.config = config
        self.windowed = windowed

        # Core components
        self.monitor: Optional[StateMonitor] = None
        self.navigator = PanelNavigator()

        # Display
        self.screen: Optional[pygame.Surface] = None
        self.clock = pygame.time.Clock()
        self.running = False

        # Current context
        self.current_context: Optional[ContentContext] = None
        self.enrichment_data: Dict[str, Any] = {}

        # Setup logging
        self._setup_logging()
        self.logger = logging.getLogger("discovery")

        # Register built-in panels
        self._register_builtin_panels()

        # Setup enrichment callbacks
        self._setup_enrichment()

    def _setup_logging(self):
        """Setup logging configuration."""
        logging.basicConfig(
            level=getattr(logging, self.config.log_level), format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    def _register_builtin_panels(self):
        """Register built-in content panels."""
        try:
            content_panel_registry.register_panel(NowPlayingPanel())
            content_panel_registry.register_panel(CoverArtPanel())
            content_panel_registry.register_panel(VUMeterPanel())
            content_panel_registry.register_panel(DebugPanel())

            self.logger.info("Registered %d built-in panels", len(content_panel_registry.get_panel_ids()))
        except Exception as e:
            self.logger.error("Failed to register built-in panels: %s", e)

    def _setup_enrichment(self):
        """Setup metadata enrichment."""

        def on_enrichment_complete(enrichment_data, context):
            """Handle enrichment completion."""
            self.logger.debug("Enrichment completed for: %s - %s", context.artist, context.title)
            # Store enrichment data (could be passed to panels)
            key = f"{context.artist}:{context.album}:{context.title}"
            self.enrichment_data[key] = enrichment_data

        enrichment_engine.add_enrichment_callback(on_enrichment_complete)

    def initialize_display(self) -> bool:
        """Initialize pygame display."""
        try:
            pygame.init()

            if self.windowed:
                self.screen = pygame.display.set_mode((1200, 800))
                pygame.display.set_caption("Music Discovery")
            else:
                # Fullscreen
                self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)

            # Hide mouse cursor in fullscreen
            if not self.windowed:
                pygame.mouse.set_visible(False)

            self.logger.info("Display initialized: %dx%d", self.screen.get_width(), self.screen.get_height())
            return True

        except Exception as e:
            self.logger.error("Failed to initialize display: %s", e)
            return False

    def initialize_monitor(self) -> bool:
        """Initialize metadata monitor."""
        try:
            self.monitor = StateMonitor(
                config=self.config.state_monitor, metadata_callback=self._on_metadata, state_callback=self._on_state
            )

            self.monitor.start()
            self.logger.info("Metadata monitor started")
            return True

        except Exception as e:
            self.logger.error("Failed to initialize monitor: %s", e)
            return False

    def _on_metadata(self, metadata: dict) -> None:
        """Handle metadata updates."""
        try:
            # Create content context
            state = self.monitor.get_state() if self.monitor else PlaybackState.NO_SESSION
            context = ContentContext.from_metadata(metadata, state, is_live=True)

            self.current_context = context

            # Update navigator with live context
            self.navigator.update_live_context(context)

            # Trigger enrichment (async)
            if context.artist or context.album or context.title:
                request = EnrichmentRequest(
                    artist=context.artist, album=context.album, title=context.title, context=context
                )
                enrichment_engine.enrich_sync(request)

            self.logger.debug("Metadata updated: %s - %s", context.artist, context.title)

        except Exception as e:
            self.logger.error("Error handling metadata: %s", e)

    def _on_state(self, state: PlaybackState) -> None:
        """Handle state changes."""
        try:
            self.logger.debug("State changed: %s", state)

            # Update current context state if we have one
            if self.current_context:
                self.current_context.playback_state = state
                self.navigator.update_live_context(self.current_context)

        except Exception as e:
            self.logger.error("Error handling state change: %s", e)

    def handle_events(self) -> bool:
        """Handle pygame events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE or event.key == pygame.K_q:
                    return False
                elif event.key == pygame.K_F11:
                    self._toggle_fullscreen()

            # Let navigator handle navigation events
            self.navigator.handle_event(event)

        return True

    def _toggle_fullscreen(self):
        """Toggle between windowed and fullscreen mode."""
        self.windowed = not self.windowed

        if self.windowed:
            self.screen = pygame.display.set_mode((1200, 800))
            pygame.mouse.set_visible(True)
        else:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            pygame.mouse.set_visible(False)

        self.logger.info("Toggled to %s mode", "windowed" if self.windowed else "fullscreen")

    def render(self) -> None:
        """Render the current frame."""
        if not self.screen:
            return

        # Clear screen
        self.screen.fill((10, 10, 14))  # Dark background

        # Get current panel
        current_panel = self.navigator.get_current_panel()

        if current_panel:
            # Render current panel
            screen_rect = self.screen.get_rect()
            # Leave space for navigation hints at bottom
            panel_rect = pygame.Rect(0, 0, screen_rect.width, screen_rect.height - 60)

            try:
                current_panel.render(self.screen, panel_rect)
            except Exception as e:
                self.logger.error("Error rendering panel %s: %s", current_panel.info.id, e)
                # Draw error message
                font = pygame.font.Font(None, 24)
                error_text = f"Panel Error: {e}"
                error_surface = font.render(error_text, True, (255, 100, 100))
                error_rect = error_surface.get_rect(center=panel_rect.center)
                self.screen.blit(error_surface, error_rect)

            # Render navigation hints
            hint_rect = pygame.Rect(0, screen_rect.height - 60, screen_rect.width, 60)
            self.navigator.render_navigation_hints(self.screen, hint_rect)

        else:
            # No panels available
            font = pygame.font.Font(None, 36)
            text = font.render("No content panels available", True, (170, 170, 170))
            text_rect = text.get_rect(center=self.screen.get_rect().center)
            self.screen.blit(text, text_rect)

        # Update display
        pygame.display.flip()

    def run(self) -> int:
        """Main application loop."""
        self.logger.info("Starting Music Discovery application")

        # Initialize components
        if not self.initialize_display():
            return 1

        if not self.initialize_monitor():
            return 1

        # Update navigator with available panels
        self.navigator.update_available_panels()

        # Main loop
        self.running = True
        try:
            while self.running:
                # Handle events
                if not self.handle_events():
                    break

                # Render frame
                self.render()

                # Control frame rate
                self.clock.tick(self.config.ui.target_fps)

        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt")

        except Exception as e:
            self.logger.error("Unexpected error in main loop: %s", e)
            return 1

        finally:
            self.cleanup()

        self.logger.info("Music Discovery application stopped")
        return 0

    def cleanup(self) -> None:
        """Clean up resources."""
        self.running = False

        if self.monitor:
            try:
                self.monitor.stop()
                self.logger.info("Metadata monitor stopped")
            except Exception as e:
                self.logger.warning("Error stopping monitor: %s", e)

        # Shutdown enrichment engine
        try:
            enrichment_engine.shutdown()
            self.logger.info("Enrichment engine shutdown")
        except Exception as e:
            self.logger.warning("Error shutting down enrichment engine: %s", e)

        # Quit pygame
        try:
            pygame.quit()
            self.logger.info("Pygame shutdown complete")
        except Exception as e:
            self.logger.warning("Error during pygame shutdown: %s", e)


def load_user_panels(config: AppConfig) -> None:
    """Load user-defined panels from config or plugins directory."""
    # This would implement plugin loading
    # For now, just log that it would happen
    logger = logging.getLogger("discovery.plugins")
    logger.info("User panel loading not yet implemented")


def setup_signal_handlers(app: DiscoveryApp) -> None:
    """Setup signal handlers for graceful shutdown."""

    def signal_handler(signum, _frame):
        logging.getLogger("discovery").info("Received signal %d, shutting down", signum)
        app.running = False

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def main():
    """Main entry point for the music discovery application."""
    parser = argparse.ArgumentParser(description="Music Discovery Interface")
    parser.add_argument("--config", help="Path to config file")
    parser.add_argument(
        "--windowed", action="store_true", help="Run in windowed mode"
    )
    parser.add_argument(
        "--fullscreen", action="store_true", help="Run in fullscreen mode"
    )
    parser.add_argument(
        "--debug", action="store_true", help="Enable debug logging"
    )

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    # Load configuration
    config = AppConfig(config_file=args.config)

    # Create and run application
    app = DiscoveryApp(config, windowed=args.windowed)
    try:
        app.run()
    except KeyboardInterrupt:
        logging.info("Discovery app interrupted by user")
    except Exception as e:
        logging.error(f"Discovery app error: {e}")
        raise


if __name__ == "__main__":
    sys.exit(main())
