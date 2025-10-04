#!/usr/bin/env python3
# metadata_display.py
# Simple fullscreen pygame display for shairport-sync metadata
#
# Layout:
# - Left side: metadata (artist/album/title/state) + album art
# - Right side: scrolling log output with debug filtering
#
# Controls:
# - 'D': Toggle debug message visibility
# - 'Q'/'Esc': Quit application
# - 'F': Toggle fullscreen mode
# - Ctrl+C: Graceful shutdown
#
# Usage:
#   python3 devtools/metadata_display.py [--windowed|--fullscreen|--kiosk|--cli]

"""Pygame-based display application for now-playing metadata from shairport-sync.

This module provides a graphical display for music metadata and playback state,
with support for multiple display modes including fullscreen, windowed, and
headless CLI operation. It integrates with the nowplaying package to show
enriched metadata from various music services.
"""

import os

# Suppress pygame startup messages - do this early so pygame does not print on import
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
os.environ["PYGAME_DETECT_AVX2"] = "0"

import logging
import signal
import sys
import threading
import time
from typing import List, Optional, Tuple

import pygame

from nowplaying.metadata_monitor import MetadataMonitor
from nowplaying.module_registry import module_registry
from nowplaying.panels import (
    AlbumEnrichmentPanel,
    ArtistEnrichmentPanel,
    ContentContext,
    CoverArtPanel,
    DiscographyPanel,
    NowPlayingPanel,
    ServiceStatusPanel,
    SocialStatsPanel,
    SongEnrichmentPanel,
    VUMeterPanel,
)

# Simple configuration constants
APP_TITLE = "Now Playing Display"
TARGET_FPS = 30

# Colors (simplified color scheme)
DARK_BG = (10, 10, 14)
TEXT_COLOR = (230, 230, 230)
DIM_TEXT = (170, 170, 170)
ACCENT_COLOR = (120, 170, 255)
ERROR_COLOR = (255, 120, 120)
WARN_COLOR = (255, 210, 140)
DEBUG_COLOR = (140, 160, 255)
DIVIDER_COLOR = (28, 28, 36)

# Layout margins
MARGIN = 16

# Log settings
MAX_LOG_LINES = 500  # Reduced for simplicity
VISIBLE_LOG_LINES = 40

# Font sizes
LOG_FONT_SIZE = 14  # Reduced from 20 to show more log data
META_FONT_SIZE = 24
TITLE_FONT_SIZE = 28

# Defaults
DEFAULT_COVER_TEXT = "No cover art"
DEFAULT_STATE_TEXT = "waiting"
DEFAULT_PIPE_PATH = "/tmp/shairport-sync-metadata"


class TailBuffer:
    """Thread-safe ring buffer for log lines."""

    def __init__(self, capacity: int):
        """Initialize buffer with specified capacity for log entries."""
        self.capacity = capacity
        self.buffer: List[Tuple[float, str, str]] = []
        self.lock = threading.Lock()
        self.debug_subsystems = None  # None = show all, set() = show none, {'name'} = show specific

    def append(self, level: str, text: str):
        """Add a new log entry with current timestamp."""
        timestamp = time.time()
        with self.lock:
            self.buffer.append((timestamp, level, text))
            if len(self.buffer) > self.capacity:
                self.buffer = self.buffer[-self.capacity :]

    def get_recent_logs(self, max_items: int, include_debug: bool = True) -> List[Tuple[float, str, str]]:
        """Get the most recent log entries."""
        with self.lock:
            logs = self.buffer[-max_items:] if self.buffer else []

        # Simple debug filtering (for GUI display)
        if not include_debug:
            logs = [log for log in logs if log[1] != "DEBUG"]

        return logs

    def get_logs_with_offset(
        self, max_items: int, offset: int, include_debug: bool = True
    ) -> List[Tuple[float, str, str]]:
        """Get log lines with offset from the end (for scrollback)."""
        with self.lock:
            data = self.buffer[-self.capacity :] if self.buffer else []

        # Simple debug filtering (for GUI display)
        if not include_debug:
            data = [log for log in data if log[1] != "DEBUG"]

        # Calculate slice indices
        total_lines = len(data)
        start_idx = max(0, total_lines - max_items - offset)
        end_idx = max(0, total_lines - offset)

        return data[start_idx:end_idx]

    def get_total_lines(self, include_debug: bool = True) -> int:
        """Get total number of available log lines."""
        with self.lock:
            data = self.buffer[-self.capacity :] if self.buffer else []

        # Simple debug filtering (for GUI display)
        if not include_debug:
            data = [log for log in data if log[1] != "DEBUG"]

        return len(data)


class MillisecondFormatter(logging.Formatter):
    """Custom formatter that includes milliseconds in timestamps."""

    def formatTime(self, record, datefmt=None):
        """Override formatTime to include milliseconds."""
        import datetime

        ct = self.converter(record.created)
        if datefmt:
            # For custom format, use standard formatting
            s = time.strftime(datefmt, ct)
        else:
            # Default format with milliseconds
            dt = datetime.datetime.fromtimestamp(record.created)
            s = dt.strftime("%H:%M:%S.%f")[:-3]  # Include milliseconds
        return s


class DebugLogFilter(logging.Filter):
    """Custom filter for controlling debug message visibility by subsystem."""

    def __init__(self, subsystems: set = None):
        """Initialize filter with allowed subsystems.

        Args:
            subsystems: Set of subsystem names to show debug messages for.
                       If None, show all debug messages.
                       If empty set, show no debug messages.
                       Available: 'playback_metadata', 'playback_state'
        """
        super().__init__()
        self.subsystems = subsystems

    def filter(self, record):
        """Filter log records based on subsystem and level."""
        # Always allow non-debug messages
        if record.levelname != "DEBUG":
            return True

        # If no subsystem filter, show all debug messages
        if self.subsystems is None:
            return True

        # If empty subsystem set, hide all debug messages
        if not self.subsystems:
            return False

        # Show debug messages only for specified subsystems
        return record.name in self.subsystems


class PygameLogHandler(logging.Handler):
    """Custom logging handler that appends log records to a TailBuffer."""

    def __init__(self, tail: TailBuffer):
        """Initialize pygame log handler with tail buffer for log collection."""
        super().__init__()
        self.tail = tail

    def emit(self, record: logging.LogRecord):
        """Emit a log record by appending it to the tail buffer."""
        try:
            msg = record.getMessage()
        except Exception:
            msg = str(record.msg)
        level = record.levelname.upper()
        self.tail.append(level, msg)


# ------------- Metadata + State Model -------------
class UIModel:
    """Holds latest metadata/state for the UI thread."""

    def __init__(self):
        """Initialize UI model with default empty metadata and state."""
        self._lock = threading.Lock()
        self.artist: str = ""
        self.album: str = ""
        self.title: str = ""
        self.genre: str = ""
        self.state: str = DEFAULT_STATE_TEXT
        self.cover_path: Optional[str] = None
        self.cover_mtime: Optional[float] = None
        self._cover_surface: Optional[pygame.Surface] = None

        # Enrichment data
        self.enrichment_data: Optional[dict] = None

        # Content context for panels
        self.content_context = ContentContext()

    # Metadata callback from monitor
    def on_metadata(self, m: dict):
        """Handle metadata updates from the metadata monitor."""
        with self._lock:
            self.artist = m.get("artist", self.artist)
            self.album = m.get("album", self.album)
            self.title = m.get("title", self.title)
            self.genre = m.get("genre", self.genre)
            path = m.get("cover_art_path")
            if path and os.path.isfile(path):
                self.cover_path = path
                try:
                    self.cover_mtime = os.path.getmtime(path)
                except OSError:
                    self.cover_mtime = None
                # Invalidate cached surface; reload in draw cycle
                self._cover_surface = None

            # Update content context
            self.content_context.artist = self.artist
            self.content_context.album = self.album
            self.content_context.title = self.title
            self.content_context.genre = self.genre
            self.content_context.cover_art_path = self.cover_path

            # Trigger enrichment if we have artist/album data
            if self.artist or self.album:
                self._trigger_enrichment()

    # State callback from monitor
    def on_state(self, s: str):
        """Handle playback state changes from the metadata monitor."""
        with self._lock:
            self.state = s
            # Update content context state
            from nowplaying.playback_state import PlaybackState

            # Convert string state to PlaybackState enum
            try:
                self.content_context.playback_state = getattr(PlaybackState, s.upper(), PlaybackState.NO_SESSION)
            except AttributeError:
                self.content_context.playback_state = PlaybackState.NO_SESSION

    def _trigger_enrichment(self):
        """Trigger enrichment for current metadata."""
        # Import here to avoid circular imports
        # Create enrichment request
        from nowplaying.enrichment.base import ContentContext as EnrichmentContext
        from nowplaying.enrichment.base import EnrichmentRequest
        from nowplaying.enrichment.engine import enrichment_engine

        enrichment_context = EnrichmentContext(track_id="", source="display")
        request = EnrichmentRequest(artist=self.artist, album=self.album, title=self.title, context=enrichment_context)

        # Run enrichment asynchronously
        import asyncio

        def run_enrichment():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(enrichment_engine.enrich_async(request))
                loop.close()

                # Update enrichment data
                with self._lock:
                    self.enrichment_data = {
                        "musicbrainz_artist_id": result.musicbrainz_artist_id,
                        "musicbrainz_album_id": result.musicbrainz_album_id,
                        "musicbrainz_track_id": result.musicbrainz_track_id,
                        "discogs_artist_id": result.discogs_artist_id,
                        "discogs_release_id": result.discogs_release_id,
                        "spotify_artist_id": result.spotify_artist_id,
                        "spotify_album_id": result.spotify_album_id,
                        "artist_bio": result.artist_bio,
                        "artist_tags": result.artist_tags,
                        "similar_artists": result.similar_artists,
                        "album_reviews": result.album_reviews,
                        "album_credits": result.album_credits,
                        "tour_dates": result.tour_dates,
                        "recent_releases": result.recent_releases,
                        "artist_discography": result.artist_discography,
                        "scrobble_count": result.scrobble_count,
                        "popularity_score": result.popularity_score,
                        "user_tags": result.user_tags,
                        "cover_art_urls": result.cover_art_urls,
                        "artist_images": result.artist_images,
                        "last_updated": dict(result.last_updated),
                        "service_errors": dict(result.service_errors),
                    }
                    # Update content context with enrichment data
                    self.content_context.enrichment_data = self.enrichment_data

            except Exception as e:
                logging.getLogger("display").warning(f"Enrichment failed: {e}")

        # Run enrichment in background thread
        enrichment_thread = threading.Thread(target=run_enrichment, daemon=True)
        enrichment_thread.start()

    # Accessors for drawing thread
    def snapshot(self):
        """Return a thread-safe snapshot of current metadata and state."""
        with self._lock:
            return {
                "artist": self.artist,
                "album": self.album,
                "title": self.title,
                "genre": self.genre,
                "state": self.state,
                "cover_path": self.cover_path,
                "cover_mtime": self.cover_mtime,
                "enrichment_data": self.enrichment_data,
            }

    def _get_or_load_cover(self, target_size: Tuple[int, int]) -> Optional[pygame.Surface]:
        """Load and cache the cover scaled to target_size while preserving aspect."""
        with self._lock:
            path = self.cover_path
            surf = self._cover_surface
        if not path or not os.path.isfile(path):
            return None

        if surf is None:
            try:
                img = pygame.image.load(path)
            except Exception:
                return None
            tw, th = target_size
            iw, ih = img.get_width(), img.get_height()
            if iw == 0 or ih == 0:
                return None
            scale = min(tw / iw, th / ih)
            new_w = max(1, int(iw * scale))
            new_h = max(1, int(ih * scale))
            img = pygame.transform.smoothscale(img, (new_w, new_h))
            with self._lock:
                self._cover_surface = img
            return img
        return surf


# -------------------- UI App ----------------------
class DisplayApp:
    """Simple pygame-based display application."""

    def __init__(
        self,
        use_fullscreen: bool = True,
        kiosk_mode: bool = False,
        headless: bool = False,
        debug_subsystems: set = None,
    ):
        """Initialize display app with screen mode settings.

        Args:
            use_fullscreen: Whether to use fullscreen mode
            kiosk_mode: Whether to use kiosk mode (hides panels)
            headless: Whether to run without GUI
            debug_subsystems: Set of subsystems to show debug for, or None for all
        """
        self.use_fullscreen = use_fullscreen
        self.kiosk_mode = kiosk_mode
        self.headless = headless
        self.debug_subsystems = debug_subsystems
        self.screen = None
        self.clock = None
        self.fonts = {}

        # Initialize tail buffer with debug filtering
        self.tail = TailBuffer(MAX_LOG_LINES)
        self.tail.debug_subsystems = debug_subsystems
        self.show_debug = debug_subsystems is not None

        self.model = UIModel()
        self.running = True
        self.monitor = None

        # Touch and scrollback state
        self.scrollback_mode = False
        self.scroll_offset = 0
        self.max_scroll_offset = 0

        # Touch gesture state
        self.touch_down = False
        self.touch_start_pos = None
        self.touch_start_time = 0
        self.last_touch_time = 0
        self.is_dragging = False
        self.last_drag_y = 0
        self.drag_threshold = 10  # pixels
        self.double_tap_threshold = 0.5  # seconds
        self.swipe_threshold = 50  # pixels for swipe detection
        self.swipe_velocity_threshold = 0.3  # pixels per ms for swipe detection

        # Panel touch gesture state
        self.panel_touch_active = False
        self.panel_touch_start = None
        self.panel_touch_start_time = 0

        # Enrichment panel state
        self.current_panel = 0
        self.enrichment_panels = [
            NowPlayingPanel(),
            CoverArtPanel(),
            ArtistEnrichmentPanel(),
            AlbumEnrichmentPanel(),
            SongEnrichmentPanel(),
            DiscographyPanel(),
            SocialStatsPanel(),
            ServiceStatusPanel(),
            VUMeterPanel(),
        ]

        # Set up signal handling
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, signum, frame):  # noqa: U100
        """Handle shutdown signals gracefully."""
        logging.getLogger("display").info(f"Received signal {signum}, shutting down...")
        self.running = False

    def setup_pygame(self):
        """Initialize pygame and create the display."""
        # Handle headless mode
        if not os.environ.get("DISPLAY"):
            os.environ["SDL_VIDEODRIVER"] = "dummy"

        pygame.init()

        # Get screen size
        display_info = pygame.display.Info()
        screen_width = display_info.current_w
        screen_height = display_info.current_h

        # Create display
        if self.use_fullscreen:
            self.screen = pygame.display.set_mode((screen_width, screen_height), pygame.FULLSCREEN)
            pygame.mouse.set_visible(False)
            if self.kiosk_mode:
                pygame.event.set_grab(True)
                self._hide_desktop_panels()
        else:
            self.screen = pygame.display.set_mode((1280, 800))
            pygame.mouse.set_visible(True)

        pygame.display.set_caption(APP_TITLE)
        self.clock = pygame.time.Clock()

        # Create fonts with better Unicode support
        font_options = [
            "DejaVu Sans Mono",  # Good Unicode support
            "Liberation Mono",  # Common on Linux
            "Consolas",  # Windows
            "Monaco",  # macOS
            None,  # Fallback to pygame default
        ]

        # Try fonts in order of preference
        selected_font = None
        for font_name in font_options:
            try:
                test_font = pygame.font.SysFont(font_name, LOG_FONT_SIZE)
                if test_font:
                    selected_font = font_name
                    break
            except OSError:
                continue

        self.fonts = {
            "log": pygame.font.SysFont(selected_font, LOG_FONT_SIZE),
            "meta": pygame.font.SysFont(selected_font, META_FONT_SIZE),
            "title": pygame.font.SysFont(selected_font, TITLE_FONT_SIZE, bold=True),
        }

        logging.getLogger("display").info(f"Using font: {selected_font or 'pygame default'}")

    def _hide_desktop_panels(self):
        """Hide desktop panels in kiosk mode."""
        try:
            import subprocess

            # Try to hide common Linux desktop panels
            for panel_class in ["panel", "lxpanel"]:
                subprocess.run(
                    [
                        "xdotool",
                        "search",
                        "--onlyvisible",
                        "--class",
                        panel_class,
                        "windowunmap",
                    ],
                    capture_output=True,
                    timeout=1,
                )
        except (subprocess.TimeoutExpired, Exception):
            pass  # Ignore errors - not critical

    def setup_logging(self):
        """Set up log capture for display."""
        handler = PygameLogHandler(self.tail)
        formatter = MillisecondFormatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        handler.setFormatter(formatter)

        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        root_logger.addHandler(handler)

        # In headless mode, also add console logging
        if self.headless:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            # Apply subsystem filtering for headless mode
            debug_filter = DebugLogFilter(self.debug_subsystems)
            console_handler.addFilter(debug_filter)
            root_logger.addHandler(console_handler)
            logging.getLogger("display").info("Headless mode - logs will appear in terminal")
        else:
            logging.getLogger("display").info("Display started - DEBUG messages visible")

    def start_metadata_monitor(
        self,
        capture_file=None,
        replay_file=None,
        fast_forward=False,
        compress_images=False,
    ):
        """Start the metadata monitoring with optional capture/replay."""
        # Check if capture module is available
        if capture_file or replay_file:
            try:
                # Import capture/replay functionality only when needed
                if capture_file:
                    from nowplaying.capture_replay import MetadataCapture  # noqa: F401
                if replay_file:
                    from nowplaying.capture_replay import MetadataReplay
            except ImportError:
                logging.getLogger("display").error("Capture/replay functionality not available")
                return False

        if replay_file:
            # Replay mode - create a special monitor that feeds from replay instead of pipe
            try:
                logging.getLogger("display").info(f"Starting replay from: {replay_file}")

                # Create a metadata monitor without pipe for replay mode
                self.monitor = MetadataMonitor(
                    pipe_path=None,  # No pipe in replay mode
                    state_callback=self.model.on_state,
                    metadata_callback=self.model.on_metadata,
                    capture_file=None,  # No capture during replay
                )

                # Import replay functionality
                replay_handler = MetadataReplay(replay_file, fast_forward_gaps=fast_forward)

                def replay_line_callback(line):
                    """Process replayed metadata lines through the normal pipeline."""
                    # Feed the line through the metadata reader's normal processing
                    if self.monitor and hasattr(self.monitor, "_metadata_reader"):
                        try:
                            self.monitor._metadata_reader.process_line(line)
                        except Exception as e:
                            logging.getLogger("capture").error(f"Error processing replayed line: {e}")
                    else:
                        logging.getLogger("capture").error("No metadata reader available for replay processing")

                def replay_event_callback(event_type, description, timestamp):
                    """Process replayed events."""
                    logging.getLogger("capture").info(f"Replay event at {timestamp:.2f}s: {event_type} - {description}")

                    # Handle state change events by directly updating the monitor's state
                    if event_type == "state_change" and self.monitor:
                        # Parse state change description (format: "OLD -> NEW: reason")
                        try:
                            if " -> " in description:
                                state_part = description.split(" -> ")[1]
                                new_state_name = state_part.split(":")[0].strip()
                                # Convert state name to PlaybackState enum
                                from nowplaying.playback_state import PlaybackState

                                if hasattr(PlaybackState, new_state_name):
                                    new_state = getattr(PlaybackState, new_state_name)
                                    self.monitor.set_state(new_state)
                        except Exception as e:
                            logging.getLogger("capture").warning(f"Could not parse state change: {e}")

                # Start replay in a separate thread to avoid blocking
                import threading

                def run_replay():
                    try:
                        replay_handler.replay(replay_line_callback, replay_event_callback)
                        logging.getLogger("display").info("Replay completed")
                    except Exception as e:
                        logging.getLogger("display").error(f"Replay error: {e}")
                        import traceback

                        traceback.print_exc()

                replay_thread = threading.Thread(target=run_replay, daemon=True)
                replay_thread.start()

                logging.getLogger("display").info("Replay mode initialized - feeding through metadata pipeline")
                return True

            except Exception as e:
                logging.getLogger("display").error(f"Failed to start replay: {e}")
                import traceback

                traceback.print_exc()
                return False
        else:
            # Live monitoring mode (with optional capture)
            self.monitor = MetadataMonitor(
                pipe_path=DEFAULT_PIPE_PATH,
                state_callback=self.model.on_state,
                metadata_callback=self.model.on_metadata,
                capture_file=capture_file,  # Pass capture file to monitor
                compress_images=compress_images,
            )
            if hasattr(self.monitor, "start"):
                self.monitor.start()

            if capture_file:
                logging.getLogger("display").info(f"Metadata capture started: {capture_file}")
            else:
                logging.getLogger("display").info("Metadata monitor started")

            return True

    def handle_events(self):
        """Process pygame events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    self.running = False
                elif event.key == pygame.K_d:
                    self.toggle_debug()
                elif event.key == pygame.K_f:
                    self.toggle_fullscreen()
                elif event.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_TAB):
                    if event.key == pygame.K_LEFT:
                        self.prev_panel()
                    else:
                        self.next_panel()
                # Handle scrollback navigation keys
                elif self.scrollback_mode and event.key == pygame.K_UP:
                    self.scroll_up()
                elif self.scrollback_mode and event.key == pygame.K_DOWN:
                    self.scroll_down()
                elif self.scrollback_mode and event.key == pygame.K_PAGEUP:
                    self.scroll_page_up()
                elif self.scrollback_mode and event.key == pygame.K_PAGEDOWN:
                    self.scroll_page_down()
                elif self.scrollback_mode and event.key in (
                    pygame.K_ESCAPE,
                    pygame.K_RETURN,
                ):
                    self.exit_scrollback_mode()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left mouse button or touch
                    mouse_x, mouse_y = event.pos
                    screen_width = self.screen.get_width()
                    # Right side is where logs are (right half of screen)
                    if mouse_x > screen_width // 2:
                        self.handle_touch_start(mouse_x, mouse_y)
                    else:
                        # Left side - panel navigation
                        self.handle_panel_touch(mouse_x, mouse_y)
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:  # Left mouse button or touch
                    mouse_x, mouse_y = event.pos
                    screen_width = self.screen.get_width()
                    # Always handle touch end, but prioritize panel swipes
                    self.handle_touch_end(mouse_x, mouse_y)
            elif event.type == pygame.MOUSEMOTION:
                if self.touch_down:
                    mouse_x, mouse_y = event.pos
                    screen_width = self.screen.get_width()
                    # Handle panel touch motion or right-side scrolling
                    if self.panel_touch_active or mouse_x > screen_width // 2:
                        self.handle_touch_drag(mouse_x, mouse_y)
            elif event.type == pygame.MOUSEWHEEL and self.scrollback_mode:
                # Mouse wheel scrolling in scrollback mode
                if event.y > 0:
                    self.scroll_up()
                elif event.y < 0:
                    self.scroll_down()

    def handle_touch_start(self, x, y):
        """Handle touch/mouse down event."""
        self.touch_down = True
        self.touch_start_pos = (x, y)
        self.touch_start_time = time.time()
        self.is_dragging = False
        self.last_drag_y = y

    def handle_touch_drag(self, x, y):
        """Handle touch/mouse drag event."""
        if not self.touch_down or not self.touch_start_pos:
            return

        # If this is a panel touch (started on left side), don't treat as log scrolling
        if self.panel_touch_active:
            return  # Panel swipes are handled in handle_touch_end

        # Calculate distance from start position
        start_x, start_y = self.touch_start_pos
        distance = ((x - start_x) ** 2 + (y - start_y) ** 2) ** 0.5

        # If we've moved enough to be considered a drag
        if distance > self.drag_threshold:
            if not self.is_dragging:
                # First time we recognize this as a drag
                self.is_dragging = True
                # Enter scrollback mode if not already in it
                if not self.scrollback_mode:
                    self.enter_scrollback_mode()

            # Handle vertical scrolling
            if self.scrollback_mode:
                delta_y = y - self.last_drag_y
                # Scale down the scrolling sensitivity
                # Positive delta_y = drag down = show older logs (scroll up in history)
                # Negative delta_y = drag up = show newer logs (scroll down in history)
                scroll_lines = int(delta_y / 10)

                if scroll_lines != 0:
                    for _ in range(abs(scroll_lines)):
                        if scroll_lines > 0:
                            self.scroll_up()  # Drag down = older logs
                        else:
                            self.scroll_down()  # Drag up = newer logs

                self.last_drag_y = y

    def handle_touch_end(self, x, y):
        """Handle touch/mouse up event."""
        if not self.touch_down:
            return

        self.touch_down = False
        current_time = time.time()

        # Check for panel swipe gestures first
        if self.panel_touch_active and self.panel_touch_start:
            start_x, start_y = self.panel_touch_start
            delta_x = x - start_x
            delta_y = y - start_y
            delta_time = current_time - self.panel_touch_start_time

            # Check if this is a horizontal swipe
            if abs(delta_x) > self.swipe_threshold and abs(delta_x) > abs(delta_y):
                velocity = abs(delta_x) / max(delta_time, 0.001)  # pixels per second
                if velocity > self.swipe_velocity_threshold * 1000:  # convert to pixels per second
                    if delta_x > 0:
                        # Swipe right - previous panel
                        self.prev_panel()
                    else:
                        # Swipe left - next panel
                        self.next_panel()
                    # Reset panel touch state
                    self.panel_touch_active = False
                    self.panel_touch_start = None
                    return

        # Reset panel touch state
        self.panel_touch_active = False
        self.panel_touch_start = None

        # If this was a drag, don't process as tap
        if self.is_dragging:
            self.is_dragging = False
            return

        # Handle scrollback mode exits
        if self.scrollback_mode:
            # Single tap in scrollback mode = exit scrollback
            self.exit_scrollback_mode()
            return

        # Check for double tap (debug toggle) - only when not in scrollback mode
        time_since_last = current_time - self.last_touch_time
        if time_since_last < self.double_tap_threshold:
            # Double tap - toggle debug filter
            self.toggle_debug()

        self.last_touch_time = current_time

    def enter_scrollback_mode(self):
        """Enter scrollback mode to browse log history."""
        self.scrollback_mode = True
        self.scroll_offset = 0
        # Calculate max scroll based on available log lines
        total_lines = self.tail.get_total_lines(include_debug=self.show_debug)
        self.max_scroll_offset = max(0, total_lines - VISIBLE_LOG_LINES)

    def exit_scrollback_mode(self):
        """Exit scrollback mode and return to live log display."""
        self.scrollback_mode = False
        self.scroll_offset = 0

    def scroll_up(self):
        """Scroll up in scrollback mode (older logs)."""
        if self.scrollback_mode:
            self.scroll_offset = min(self.scroll_offset + 1, self.max_scroll_offset)

    def scroll_down(self):
        """Scroll down in scrollback mode (newer logs)."""
        if self.scrollback_mode:
            self.scroll_offset = max(self.scroll_offset - 1, 0)

    def scroll_page_up(self):
        """Scroll up by a page in scrollback mode."""
        if self.scrollback_mode:
            page_size = VISIBLE_LOG_LINES // 2
            self.scroll_offset = min(self.scroll_offset + page_size, self.max_scroll_offset)

    def scroll_page_down(self):
        """Scroll down by a page in scrollback mode."""
        if self.scrollback_mode:
            page_size = VISIBLE_LOG_LINES // 2
            self.scroll_offset = max(self.scroll_offset - page_size, 0)

    def toggle_debug(self):
        """Toggle debug message visibility."""
        self.show_debug = not self.show_debug
        status = "visible" if self.show_debug else "hidden"
        logging.getLogger("display").info(f"Debug messages now {status}")

    def next_panel(self):
        """Switch to next enrichment panel."""
        self.current_panel = (self.current_panel + 1) % len(self.enrichment_panels)
        logging.getLogger("display").info(f"Switched to panel: {self.enrichment_panels[self.current_panel].info.name}")

    def prev_panel(self):
        """Switch to previous enrichment panel."""
        self.current_panel = (self.current_panel - 1) % len(self.enrichment_panels)
        logging.getLogger("display").info(f"Switched to panel: {self.enrichment_panels[self.current_panel].info.name}")

    def handle_panel_touch(self, x, y):
        """Handle touch events on the left panel area for swipe navigation."""
        # Store touch start for swipe detection
        self.panel_touch_start = (x, y)
        self.panel_touch_start_time = time.time()
        self.panel_touch_active = True

    def draw(self):
        """Draw the entire display."""
        screen = self.screen
        screen.fill(DARK_BG)

        # Split screen vertically
        width, height = screen.get_size()
        mid_x = width // 2
        left_rect = pygame.Rect(0, 0, mid_x, height)
        right_rect = pygame.Rect(mid_x, 0, width - mid_x, height)

        # Draw divider line
        pygame.draw.line(screen, DIVIDER_COLOR, (mid_x, 0), (mid_x, height), 2)

        # Draw content
        self._draw_left_panel(left_rect)
        self._draw_logs(right_rect)

        pygame.display.flip()

    def _draw_logs(self, rect: pygame.Rect):
        """Draw the log panel."""
        # Build title with current mode indicator
        if self.scrollback_mode:
            title = "Logs (scrollback) [tap to exit]"
            title_color = WARN_COLOR
        else:
            title = "Logs (live)"
            title_color = ACCENT_COLOR

        if self.show_debug:
            title += " – DEBUG shown [D]"
        else:
            title += " – DEBUG hidden [D]"

        self._render_text(self.fonts["title"], title, (rect.x + MARGIN, rect.y + MARGIN), title_color)

        # Calculate available space for logs
        y_start = rect.y + MARGIN + self.fonts["title"].get_height() + 8
        available_height = rect.bottom - y_start - MARGIN
        line_height = self.fonts["log"].get_height() + 2
        max_lines = max(1, min(VISIBLE_LOG_LINES, available_height // line_height))

        # Get log entries based on mode
        if self.scrollback_mode:
            # In scrollback mode, get lines with offset
            logs = self.tail.get_logs_with_offset(max_lines, self.scroll_offset, include_debug=self.show_debug)
            # Update max scroll based on current filter
            total_lines = self.tail.get_total_lines(include_debug=self.show_debug)
            self.max_scroll_offset = max(0, total_lines - max_lines)
        else:
            # Normal mode - get latest lines
            logs = self.tail.get_recent_logs(max_lines, include_debug=self.show_debug)

        # Draw log entries
        y = y_start
        for _timestamp, level, message in logs:
            color = self._get_log_color(level)
            self._render_text(self.fonts["log"], message, (rect.x + MARGIN, y), color)
            y += line_height

    def _get_log_color(self, level: str):
        """Get color for log level."""
        if level == "DEBUG":
            return DEBUG_COLOR
        elif level == "WARNING":
            return WARN_COLOR
        elif level in ("ERROR", "CRITICAL"):
            return ERROR_COLOR
        else:
            return TEXT_COLOR

    def _draw_left_panel(self, rect: pygame.Rect):
        """Draw the left panel - either metadata or enrichment panels."""
        # Get current enrichment panel
        panel = self.enrichment_panels[self.current_panel]

        # Update panel with current context
        panel.update_context(self.model.content_context)

        # Draw panel title
        title_y = rect.y + MARGIN
        self._render_text(self.fonts["title"], panel.info.name, (rect.x + MARGIN, title_y), ACCENT_COLOR)
        title_y += self.fonts["title"].get_height() + 8

        # Draw subtitle
        subtitle_text = panel.info.description
        self._render_text(self.fonts["meta"], subtitle_text, (rect.x + MARGIN, title_y), TEXT_COLOR)

        # Create content area for panel
        content_rect = pygame.Rect(
            rect.x + MARGIN,
            title_y + self.fonts["meta"].get_height() + 10,
            rect.width - (MARGIN * 2),
            rect.bottom - title_y - self.fonts["meta"].get_height() - MARGIN - 20,
        )

        # Draw panel content
        panel.render(self.screen, content_rect)

        # Draw panel navigation hint
        hint_text = "Swipe or ← → to navigate panels"
        hint_y = rect.bottom - MARGIN - self.fonts["meta"].get_height()
        self._render_text(self.fonts["meta"], hint_text, (rect.x + MARGIN, hint_y), DIM_TEXT)

    def _render_text(self, font, text: str, pos: tuple, color: tuple, return_surface: bool = False):
        """Render text and either blit to screen or return surface."""
        # Ensure text is a string to avoid pygame errors
        if text is None:
            text = "-"
        elif not isinstance(text, (str, int, float)):
            text = str(text)
        else:
            text = str(text)  # Convert everything to string for safety

        # Handle empty strings
        if not text:
            text = "-"

        # Clean the text to remove problematic characters that pygame can't handle
        # Remove null characters and other control characters except newlines/tabs
        text_cleaned = "".join(c for c in text if ord(c) >= 32 or c in "\n\t")
        # Also replace null characters specifically if they somehow remain
        text_cleaned = text_cleaned.replace("\x00", "\\0")

        try:
            # Try to encode as UTF-8 and back to catch encoding issues early
            text_encoded = text_cleaned.encode("utf-8", errors="replace").decode("utf-8")
            surface = font.render(text_encoded, True, color)
            if return_surface:
                return surface
            else:
                self.screen.blit(surface, pos)
        except UnicodeEncodeError as e:
            # Handle Unicode encoding issues - write to stderr for visibility
            import sys

            print(f"DISPLAY ERROR: Unicode encoding error for text: {e}", file=sys.stderr)
            logging.getLogger("display").warning(f"Unicode encoding error for text: {e}")
            # Replace problematic characters
            safe_text = text.encode("ascii", errors="replace").decode("ascii")
            surface = font.render(safe_text, True, color)
            if return_surface:
                return surface
            else:
                self.screen.blit(surface, pos)
        except Exception as e:
            # Fallback for any other rendering issues - write to stderr for visibility
            import sys

            print(
                f"DISPLAY ERROR: Text rendering error for '{text[:50]}...': {e}",
                file=sys.stderr,
            )
            logging.getLogger("display").warning(f"Text rendering error for '{text[:50]}...': {e}")
            # Try with a simple safe character set
            safe_text = "".join(c if ord(c) < 128 else "?" for c in text)
            try:
                surface = font.render(safe_text[:100], True, color)  # Limit length too
                if return_surface:
                    return surface
                else:
                    self.screen.blit(surface, pos)
            except (pygame.error, Exception) as e:
                # Ultimate fallback
                import sys

                print(
                    f"DISPLAY ERROR: Critical text rendering failure: {e}",
                    file=sys.stderr,
                )
                fallback_text = "[render error]"
                surface = font.render(fallback_text, True, color)
                if return_surface:
                    return surface
                else:
                    self.screen.blit(surface, pos)

    def run(
        self,
        capture_file=None,
        replay_file=None,
        fast_forward=False,
        compress_images=False,
    ):
        """Run the main application loop."""
        try:
            if not self.headless:
                self.setup_pygame()
            self.setup_logging()

            # Start monitoring with capture/replay options
            monitor_started = self.start_metadata_monitor(capture_file, replay_file, fast_forward, compress_images)
            if not monitor_started:
                logging.getLogger("display").error("Failed to start metadata monitoring")
                return False

            if self.headless:
                # Headless mode: just run the metadata monitor and log to console
                logging.getLogger("display").info("Running in headless mode - press Ctrl+C to exit")
                try:
                    while self.running:
                        time.sleep(0.1)  # Small sleep to prevent busy waiting
                except KeyboardInterrupt:
                    logging.getLogger("display").info("Keyboard interrupt received")
                    self.running = False
            else:
                # GUI mode: run the normal pygame event loop
                while self.running:
                    self.handle_events()
                    self.draw()
                    self.clock.tick(TARGET_FPS)

        except KeyboardInterrupt:
            logging.getLogger("display").info("Keyboard interrupt received")
            self.running = False
        except Exception as e:
            logging.getLogger("display").error(f"Error in main loop: {e}")
            import traceback

            traceback.print_exc()
            self.running = False
        finally:
            self._cleanup()

    def _cleanup(self):
        """Clean up resources."""
        if self.monitor and hasattr(self.monitor, "stop"):
            try:
                logging.getLogger("display").info("Stopping metadata monitor...")
                self.monitor.stop()
                logging.getLogger("display").info("Metadata monitor stopped")
            except Exception as e:
                logging.getLogger("display").warning(f"Error stopping monitor: {e}")

        # Only quit pygame if we initialized it (not in headless mode)
        if not self.headless:
            pygame.quit()
        logging.getLogger("display").info("Display application shutdown complete")


def main():
    """Provide the main entry point."""
    # Simple help
    if "--help" in sys.argv or "-h" in sys.argv:
        print("Now Playing Metadata Display")
        print("Usage: python3 metadata_display.py [options]")
        print()
        print("Display Modes (mutually exclusive):")
        print("  --windowed     Run in windowed mode")
        print("  --fullscreen   Run in regular fullscreen (no kiosk)")
        print("  --kiosk        Run in kiosk mode (fullscreen + hide panels)")
        print("  --cli          Force CLI mode")
        print()
        print("Capture/Replay:")
        print("  --capture FILE Capture metadata to FILE (JSON Lines format)")
        print("  --replay FILE  Replay captured metadata from FILE")
        print("  --fast-forward Fast-forward through gaps during replay")
        print()
        print("Other Options:")
        print("  --test         Test mode selection without starting display")
        print("  --no-debug     Hide debug messages")

        # Dynamic subsystem debug options - only show if modules are registered
        debug_modules = module_registry.get_modules_by_category("core")
        if debug_modules:
            for _subsystem_name, info in debug_modules.items():
                print(f"  {info['debug_flag']:<15} Show only {info['description']}")

        print("  --help, -h     Show this help")
        print("  (default: show this help)")
        print()
        print("CLI Mode Details:")
        print("  - No graphical display - pure command line interface")
        print("  - All logs stream directly to terminal with millisecond timestamps")
        print("  - Still processes shairport-sync metadata and state changes")
        print("  - Perfect for SSH sessions, debugging, or scripting")
        print("  - Press Ctrl+C to exit")
        print()
        print("Capture/Replay Details:")
        print("  - Capture mode: Records all metadata to JSON Lines format for later analysis")
        print("  - Replay mode: Replays previously captured metadata with precise timing")
        print("  - Fast-forward: Automatically skips idle periods during replay")
        print("  - Image storage: Cover art is stored uncompressed for maximum quality")
        print("  - Compatible with all display modes (GUI, CLI, fullscreen, etc.)")
        print("  - Perfect for debugging production issues or testing state transitions")
        print()
        print("GUI Modes:")
        print("  --windowed     Windowed GUI display")
        print("  --fullscreen   Fullscreen GUI display")
        print("  --kiosk        Kiosk mode (fullscreen + hide panels)")
        print()
        print("Controls:")
        print("  Q, Esc         Quit")
        print("  D              Toggle debug messages")
        print("  F              Toggle fullscreen")
        print("  Left/Right arrows     Navigate enrichment panels")
        print("  Tab            Next enrichment panel")
        print()
        print("Touch Interface:")
        print("  Left side:     Swipe left/right to navigate panels")
        print("                 Tap to cycle to next panel")
        print("  Right side:    Touch & drag to scroll logs")
        print("                 Single tap exits scrollback")
        print("                 Double tap toggles debug")
        print()
        print("Enrichment Panels:")
        print("  Now Playing      Main metadata display with track info")
        print("  Cover Art        Large album cover display")
        print("  Artist Enrichment Biography, tags, similar artists, social stats")
        print("  Album Enrichment  Album reviews, credits, and release information")
        print("  Song Enrichment   Track information and song-specific data")
        print("  Discography       Artist discography and release history")
        print("  Social Stats      Scrobble counts, popularity")
        print("  Service Status    Data freshness, completeness")
        print("  Audio Levels      Real-time audio level meters")
        print()
        print("Debug Options:")
        print("  --no-debug:        Hide all debug messages")

        # Import modules to ensure they're registered for help display
        try:
            from nowplaying.metadata_monitor import StateMonitor  # noqa: F401
            from nowplaying.metadata_reader import ShairportSyncPipeReader  # noqa: F401
        except ImportError:
            pass

        # Show all registered debug modules (both input and output)
        all_modules = module_registry.get_all_modules()
        if all_modules:
            for _subsystem_name, info in all_modules.items():
                print(f"  {info['debug_flag']:<18} {info['description']}")
        else:
            print("  (No debug subsystems registered)")

        print("  Default:           Show all messages")
        print("  Combinations:      Use multiple flags together for multiple subsystems")
        print()
        print("Scrollback Mode:")
        print("  Arrow Keys     Scroll up/down")
        print("  Page Up/Down   Scroll by page")
        print("  Mouse Wheel    Scroll up/down")
        print("  Enter/Esc      Exit scrollback mode")
        return 0

    # Parse simple arguments
    windowed = "--windowed" in sys.argv
    fullscreen = "--fullscreen" in sys.argv  # Regular fullscreen (no kiosk)
    kiosk_explicit = "--kiosk" in sys.argv  # Explicit kiosk mode
    cli_explicit = "--cli" in sys.argv  # Explicit CLI flag
    test_mode = "--test" in sys.argv

    # Parse capture/replay arguments
    capture_file = None
    replay_file = None
    fast_forward = "--fast-forward" in sys.argv
    compress_images = False  # Always use uncompressed images

    # Extract capture file path
    if "--capture" in sys.argv:
        capture_idx = sys.argv.index("--capture")
        if capture_idx + 1 < len(sys.argv) and not sys.argv[capture_idx + 1].startswith("--"):
            capture_file = sys.argv[capture_idx + 1]
        else:
            print("Error: --capture requires a filename")
            return 1

    # Extract replay file path
    if "--replay" in sys.argv:
        replay_idx = sys.argv.index("--replay")
        if replay_idx + 1 < len(sys.argv) and not sys.argv[replay_idx + 1].startswith("--"):
            replay_file = sys.argv[replay_idx + 1]
        else:
            print("Error: --replay requires a filename")
            return 1

    # Validate that only one display mode is specified
    display_modes = [
        ("--windowed", windowed),
        ("--fullscreen", fullscreen),
        ("--kiosk", kiosk_explicit),
        ("--cli", cli_explicit),
    ]
    specified_modes = [mode_name for mode_name, is_set in display_modes if is_set]

    if len(specified_modes) > 1:
        print(f"Error: Cannot specify multiple display modes: {', '.join(specified_modes)}")
        print("Please specify only one of: --windowed, --fullscreen, --kiosk, --cli")
        print("Use --help for more information.")
        return 1

    # Validate capture/replay options
    if capture_file and replay_file:
        print("Error: Cannot specify both --capture and --replay")
        print("Use either --capture FILE to record or --replay FILE to playback")
        return 1

    if fast_forward and not replay_file:
        print("Error: --fast-forward can only be used with --replay")
        return 1

    # Dynamic debug subsystem options based on registry
    no_debug = "--no-debug" in sys.argv
    cli_flags = module_registry.get_debug_flags()
    enabled_subsystems = set()

    for cli_flag, subsystem_name in cli_flags.items():
        if cli_flag in sys.argv:
            enabled_subsystems.add(subsystem_name)

    # Check if no meaningful arguments provided - show help by default
    meaningful_args = [
        windowed,
        fullscreen,
        kiosk_explicit,
        cli_explicit,
        test_mode,
        no_debug,
        bool(enabled_subsystems),
        bool(capture_file),
        bool(replay_file),
        fast_forward,
    ]

    if not any(meaningful_args):
        # No arguments provided, show help and exit
        print("Now Playing Metadata Display")
        print("Usage: python3 metadata_display.py [options]")
        print()
        print("Display Modes (mutually exclusive):")
        print("  --windowed     Run in windowed mode")
        print("  --fullscreen   Run in regular fullscreen (no kiosk)")
        print("  --kiosk        Run in kiosk mode (fullscreen + hide panels)")
        print("  --cli          Force CLI mode")
        print()
        print("Capture/Replay:")
        print("  --capture FILE Capture metadata to FILE (JSON Lines format)")
        print("  --replay FILE  Replay captured metadata from FILE")
        print("  --fast-forward Fast-forward through gaps during replay")
        print()
        print("Other Options:")
        print("  --test         Test mode selection without starting display")
        print("  --no-debug     Hide debug messages")

        # Show all registered debug modules
        all_modules = module_registry.get_all_modules()
        if all_modules:
            for _subsystem_name, info in all_modules.items():
                print(f"  {info['debug_flag']:<15} Show only {info['description']}")

        print("  --help, -h     Show this help")
        print("  (default: show this help)")
        return 0

    # Default to CLI mode unless explicitly overridden with GUI modes
    cli_mode = not (windowed or fullscreen or kiosk_explicit)  # CLI is default unless GUI mode specified
    kiosk = kiosk_explicit  # Kiosk only when explicitly requested

    if cli_mode:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        print("Running in CLI mode")
    elif kiosk_explicit:
        print("Running in kiosk mode")
    elif windowed:
        print("Running in windowed mode")
    elif fullscreen:
        print("Running in regular fullscreen mode")
    else:
        print("Running in kiosk mode (default)")

    # Determine debug subsystems
    debug_subsystems = None  # Default: show all debug messages
    if no_debug:
        debug_subsystems = set()  # Show no debug messages
    elif enabled_subsystems:
        # Convert subsystem names to logger names for filtering
        debug_subsystems = set()
        for subsystem_name in enabled_subsystems:
            subsystem_info = module_registry.get_module_info(subsystem_name)
            if subsystem_info:
                debug_subsystems.add(subsystem_info["logger_name"])

    # If test mode, just show the configuration and exit
    if test_mode:
        subsystems_str = (
            "all"
            if debug_subsystems is None
            else ("none" if not debug_subsystems else ", ".join(sorted(debug_subsystems)))
        )
        capture_str = f"capture={capture_file}" if capture_file else "no capture"
        replay_str = f"replay={replay_file}" if replay_file else "no replay"
        fast_forward_str = f", fast_forward={fast_forward}" if fast_forward else ""
        print(
            f"Test mode - would run with: fullscreen={not windowed}, kiosk={kiosk}, cli_mode={cli_mode}, "
            f"debug_subsystems={subsystems_str}, {capture_str}, {replay_str}{fast_forward_str}"
        )
        return 0

    try:
        app = DisplayApp(
            use_fullscreen=not windowed,
            kiosk_mode=kiosk,
            headless=cli_mode,
            debug_subsystems=debug_subsystems,
        )
        result = app.run(
            capture_file=capture_file,
            replay_file=replay_file,
            fast_forward=fast_forward,
            compress_images=compress_images,
        )
        return 0 if result is not False else 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
