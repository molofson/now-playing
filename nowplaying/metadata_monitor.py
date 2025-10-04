"""Monitors playback state and metadata by reading directly from shairport-sync pipe."""

import contextlib
import logging
import select
import sys
import threading
import uuid
from typing import Callable, Optional

from .capture_replay import MetadataCapture
from .config import StateMonitorConfig
from .metadata_reader import ShairportSyncPipeReader
from .module_registry import module_registry
from .playback_state import PlaybackState, PlaybackStateMachine

# Register the callback output subsystems
module_registry.register_module(
    name="playback_metadata",
    description="Published metadata callbacks (artist, album, title, genre)",
    logger_name="playback_metadata",
    debug_flag="--debug-metadata",
    enabled=True,
    category="output",
)

module_registry.register_module(
    name="playback_state",
    description="Published state change callbacks (play, pause, stop, waiting)",
    logger_name="playback_state",
    debug_flag="--debug-state",
    enabled=True,
    category="output",
)

log = logging.getLogger("monitor")
log_metadata = module_registry.get_module_info("playback_metadata")["logger"]
log_state = module_registry.get_module_info("playback_state")["logger"]


class StateMonitor:
    """Monitors shairport-sync metadata directly from pipe and emits parsed data."""

    def __init__(
        self,
        pipe_path: Optional[str] = None,
        metadata_callback: Optional[Callable[[dict], None]] = None,
        state_callback: Optional[Callable[[PlaybackState], None]] = None,
        config: Optional[StateMonitorConfig] = None,
        capture_file: Optional[str] = None,
        compress_images: bool = False,
    ):
        """Initialize state monitor with pipe path and callback functions."""
        self._config = config or StateMonitorConfig()

        # Use config for pipe path, with parameter override
        effective_pipe_path = pipe_path or self._config.get_effective_pipe_path()
        self._pipe_path = effective_pipe_path

        self._metadata_callback = metadata_callback or self._default_metadata_callback
        self._state_callback = state_callback or self._default_state_callback

        # Initialize capture if requested
        self._capture = None
        if capture_file:
            self._capture = MetadataCapture(capture_file, compress_images)

        # Initialize state machine
        self._state_machine = PlaybackStateMachine(PlaybackState.NO_SESSION)
        self._pipe_fd = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._waiting_timer: Optional[threading.Timer] = None
        self._first_data_received = False

        # Create the shairport-sync pipe reader
        self._metadata_reader = ShairportSyncPipeReader(
            state_callback=self._handle_state_change,
            metadata_callback=self._metadata_callback,
        )

    def start(self) -> None:
        """Start monitoring the shairport-sync metadata pipe."""
        if self._thread and self._thread.is_alive():
            log.warning("StateMonitor is already running.")
            return

        if not self._pipe_path:
            log.warning("No pipe path provided, running in manual mode.")
            return

        log.info("Starting StateMonitor with pipe: %s", self._pipe_path)

        # Start capture if configured
        if self._capture:
            self._capture.start_capture()
            self._capture.capture_event("monitor_start", f"Started monitoring pipe: {self._pipe_path}")

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._read_loop, daemon=self._config.daemon_threads)
        self._thread.start()

    def stop(self) -> None:
        """Stop monitoring the metadata pipe."""
        self._stop_event.set()

        # Stop capture first
        if self._capture:
            self._capture.capture_event("monitor_stop", "Stopping metadata monitor")
            self._capture.stop_capture()

        # Cancel any pending timer
        self._cancel_waiting_timer()

        # Close pipe first to unblock any reads
        if self._pipe_fd:
            with contextlib.suppress(Exception):
                self._pipe_fd.close()
            self._pipe_fd = None

        # Join thread with timeout
        if self._thread:
            self._thread.join(timeout=self._config.thread_join_timeout)
            if self._thread.is_alive():
                log.warning("Metadata thread did not exit gracefully within timeout")
            self._thread = None

    def set_state(self, new_state: PlaybackState) -> None:
        """Manually set the playback state (bypasses state machine validation)."""
        # For manual state setting, we bypass validation and force the transition
        self._force_transition_state(new_state, "manual")

    def _force_transition_state(self, new_state: PlaybackState, reason: str = "") -> None:
        """Force transition to new state, bypassing state machine validation."""
        # Cancel any existing timer when state changes
        self._cancel_waiting_timer()

        # Check if this is actually a state change
        current_state = self._state_machine.current_state

        # Use the proper public method instead of breaking encapsulation
        state_changed = self._state_machine.force_transition(new_state, reason)

        # Only notify callback if state actually changed
        if state_changed:
            log_state.info("State transition: %s -> %s (%s)", current_state, new_state, reason)
            self._state_callback(new_state)

            # Clear metadata when session ends completely
            if new_state == PlaybackState.NO_SESSION:
                self._clear_metadata_for_session_end()

        # Start waiting timer for certain states
        self._start_waiting_timer_if_needed(new_state)

    def get_state(self) -> PlaybackState:
        """Get the current playback state."""
        return self._state_machine.current_state

    def _cancel_waiting_timer(self) -> None:
        """Cancel any pending waiting timer."""
        if self._waiting_timer:
            self._waiting_timer.cancel()
            self._waiting_timer = None

    def _start_waiting_timer_if_needed(self, new_state: PlaybackState) -> None:
        """Start waiting timer for states that need it."""
        if new_state in (PlaybackState.PAUSED, PlaybackState.STOPPED):
            self._waiting_timer = threading.Timer(
                self._config.wait_timeout_seconds,
                lambda: self._transition_state(PlaybackState.WAITING, "timeout"),
            )
            self._waiting_timer.start()

    def _read_loop(self) -> None:
        """Run main read loop for processing pipe data."""
        log.info("Metadata thread started")

        try:
            # Pipe must stay open for duration of monitoring thread
            self._pipe_fd = open(  # noqa: SIM115 - long-lived handle needs to stay open for thread lifetime
                self._pipe_path, "r"
            )
            self._transition_state(PlaybackState.UNDETERMINED, "pipe opened")

            # Use select for interruptible reading
            while not self._stop_event.is_set():
                # Check if data is available to read (with timeout)
                if sys.platform != "win32":  # select works on Unix-like systems
                    ready, _, _ = select.select([self._pipe_fd], [], [], self._config.select_timeout)
                    if not ready:
                        continue  # No data available, check stop event again
                else:
                    # On Windows, fall back to readline with timeout simulation
                    # (This is less elegant but works)
                    pass

                try:
                    # Check if pipe is still valid before reading
                    if not self._pipe_fd or self._pipe_fd.closed:
                        break

                    line = self._pipe_fd.readline()
                    if not line:  # EOF
                        break

                    if not self._first_data_received:
                        self._first_data_received = True
                        self._transition_state(PlaybackState.PLAYING, "first data received")

                    if self._waiting_timer:
                        self._waiting_timer.cancel()
                        self._waiting_timer = None

                    # Capture the line if capture is enabled
                    if self._capture:
                        self._capture.capture_line(line)

                    self._metadata_reader.process_line(line)

                except (OSError, ValueError, AttributeError) as e:
                    # Pipe was closed or became invalid
                    if self._stop_event.is_set():
                        break
                    log.error("Error reading line from pipe: %s", e)
                    break

        except Exception as e:
            log.error("Error reading from pipe: %s", e)
        finally:
            if self._pipe_fd:
                self._pipe_fd.close()
                self._pipe_fd = None
            log.info("Metadata thread exited")

    def _handle_state_change(self, new_state: PlaybackState) -> None:
        """Handle state changes from line processor."""
        self._transition_state(new_state, "metadata event")

    def _transition_state(self, new_state: PlaybackState, reason: str = "") -> None:
        """Transition to new state using state machine validation."""
        # Cancel any existing timer when state changes
        self._cancel_waiting_timer()

        # Check if this is actually a state change
        current_state = self._state_machine.current_state

        # Capture state transition if capture is enabled
        if self._capture and new_state != current_state:
            self._capture.capture_event("state_change", f"{current_state.name} -> {new_state.name}: {reason}")

        # Attempt state transition
        if self._state_machine.transition_to(new_state, reason):
            # Only notify callback if state actually changed
            if new_state != current_state:
                self._state_callback(new_state)

                # Clear metadata when session ends completely
                if new_state == PlaybackState.NO_SESSION:
                    self._clear_metadata_for_session_end()

            # Start waiting timer for certain states
            self._start_waiting_timer_if_needed(new_state)

    def _clear_metadata_for_session_end(self) -> None:
        """Clear metadata when a session ends."""
        log_metadata.info("Clearing metadata for session end")
        empty_metadata = {
            "metadata_id": str(uuid.uuid4()),
            "sequence_number": "0",
            "artist": "",
            "album": "",
            "title": "",
            "genre": "",
            "cover_art_path": None,
        }
        self._metadata_callback(empty_metadata)

    def _default_metadata_callback(self, metadata: dict) -> None:
        """Log published metadata."""
        log_metadata.info("Published metadata: %s", metadata)

    def _default_state_callback(self, state: PlaybackState) -> None:
        """Log published state changes."""
        log_state.info("Published state: %s", state)

    def __del__(self):
        """Clean up resources on deletion."""
        if hasattr(self, "_stop_event"):
            self.stop()


# Compatibility alias for existing code
MetadataMonitor = StateMonitor
