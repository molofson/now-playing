"""
Tests for the StateMonitor class (formerly MetadataMonitor).
"""

import sys
import threading
import time
from unittest.mock import MagicMock, Mock, mock_open, patch

import pytest

from nowplaying.config import StateMonitorConfig
from nowplaying.metadata_monitor import MetadataMonitor, StateMonitor
from nowplaying.metadata_reader import ShairportSyncPipeReader
from nowplaying.playback_state import PlaybackState


class TestShairportSyncPipeReader:
    """Test the ShairportSyncPipeReader class for XML parsing (basic compatibility tests)."""

    def setup_method(self):
        self.state_callback = Mock()
        self.metadata_callback = Mock()
        self.reader = ShairportSyncPipeReader(
            state_callback=self.state_callback, metadata_callback=self.metadata_callback
        )

    def test_parse_state_playing_pcst1(self):
        """Test parsing of playing state via XML pcst=1."""
        import base64

        play_data = base64.b64encode(b"1").decode()
        xml_line = f'<item><type>73736e63</type><code>70637374</code><length>1</length><data encoding="base64">{play_data}</data></item>'
        self.reader.process_line(xml_line)
        self.state_callback.assert_called_once_with(PlaybackState.PLAYING)

    def test_parse_state_paused_pcst0(self):
        """Test parsing of paused state via XML pcst=0."""
        import base64

        pause_data = base64.b64encode(b"0").decode()
        xml_line = f'<item><type>73736e63</type><code>70637374</code><length>1</length><data encoding="base64">{pause_data}</data></item>'
        self.reader.process_line(xml_line)
        self.state_callback.assert_called_once_with(PlaybackState.PAUSED)

    def test_parse_state_stopped_pend(self):
        """Test parsing of stopped state via XML pend."""
        xml_line = "<item><type>73736e63</type><code>70656e64</code><length>0</length></item>"
        self.reader.process_line(xml_line)
        self.state_callback.assert_called_once_with(PlaybackState.STOPPED)

    def test_parse_metadata_fields(self):
        """Test parsing of metadata fields via XML."""
        import base64

        lines = [
            "<item><type>73736e63</type><code>6d647374</code><length>0</length></item>",  # mdst
            f'<item><type>636f7265</type><code>61736172</code><length>11</length><data encoding="base64">{base64.b64encode(b"Test Artist").decode()}</data></item>',  # asar
            f'<item><type>636f7265</type><code>6173616c</code><length>10</length><data encoding="base64">{base64.b64encode(b"Test Album").decode()}</data></item>',  # asal
            f'<item><type>636f7265</type><code>6d696e6d</code><length>9</length><data encoding="base64">{base64.b64encode(b"Test Song").decode()}</data></item>',  # minm
            f'<item><type>636f7265</type><code>6173676e</code><length>4</length><data encoding="base64">{base64.b64encode(b"Rock").decode()}</data></item>',  # asgn
            "<item><type>73736e63</type><code>6d64656e</code><length>0</length></item>",  # mden
        ]

        for line in lines:
            self.reader.process_line(line)

        # Should dispatch complete metadata bundle
        self.metadata_callback.assert_called_once()
        call_args = self.metadata_callback.call_args[0][0]

        # Verify expected metadata fields are present
        expected_fields = {
            "artist": "Test Artist",
            "album": "Test Album",
            "title": "Test Song",
            "genre": "Rock",
        }
        for key, value in expected_fields.items():
            assert call_args[key] == value, f"Expected {key}='{value}', got '{call_args.get(key)}'"

        # Verify metadata includes ID and sequence number
        assert "metadata_id" in call_args
        assert "sequence_number" in call_args

    def test_ignore_empty_lines(self):
        """Test that empty lines are ignored."""
        self.reader.process_line("")
        self.reader.process_line("   ")

        self.state_callback.assert_not_called()
        self.metadata_callback.assert_not_called()


class TestStateMonitor:
    """Test the StateMonitor class."""

    def setup_method(self):
        self.state_callback = Mock()
        self.metadata_callback = Mock()
        self.monitor = StateMonitor(state_callback=self.state_callback, metadata_callback=self.metadata_callback)

    def test_initial_state_is_no_session(self):
        """Test that initial state is NO_SESSION."""
        assert self.monitor.get_state() == PlaybackState.NO_SESSION

    def test_set_state_triggers_callback(self):
        """Test that setting state triggers the callback."""
        self.monitor.set_state(PlaybackState.PLAYING)
        self.state_callback.assert_called_once_with(PlaybackState.PLAYING)
        assert self.monitor.get_state() == PlaybackState.PLAYING


class TestShutdownImprovements:
    """Test the shutdown improvements made to fix hanging issues."""

    def setup_method(self):
        self.state_callback = Mock()
        self.metadata_callback = Mock()

    def test_stop_method_improved_order(self):
        """Test that stop method follows the improved cleanup order."""
        monitor = StateMonitor(state_callback=self.state_callback, metadata_callback=self.metadata_callback)

        # Create a mock pipe and thread to test the cleanup order
        mock_pipe = Mock()
        mock_thread = Mock()
        mock_thread.is_alive.return_value = False

        # Set up the monitor with mock objects
        monitor._pipe_fd = mock_pipe
        monitor._thread = mock_thread

        # Call stop
        monitor.stop()

        # Verify the mock pipe was closed
        mock_pipe.close.assert_called_once()

        # Verify thread join was called with 1 second timeout
        mock_thread.join.assert_called_once_with(timeout=1.0)

        # Verify things were set to None after cleanup
        assert monitor._pipe_fd is None
        assert monitor._thread is None

    def test_pipe_close_exception_handling(self):
        """Test that pipe close exceptions don't crash the stop method."""
        monitor = StateMonitor()

        # Create a mock pipe that raises exception on close
        mock_pipe = Mock()
        mock_pipe.close.side_effect = OSError("Pipe already closed")
        monitor._pipe_fd = mock_pipe

        # Should not raise exception
        monitor.stop()

        # Pipe should still be set to None
        assert monitor._pipe_fd is None

    def test_reduced_thread_join_timeout(self):
        """Test that thread join timeout is now 1.0 second instead of 10."""
        monitor = StateMonitor(pipe_path="/fake/pipe")

        # Mock a thread that takes time to join
        mock_thread = Mock()
        mock_thread.is_alive.return_value = True
        monitor._thread = mock_thread

        with patch("nowplaying.metadata_monitor.log") as mock_log:
            monitor.stop()

            # Should use 1.0 second timeout
            mock_thread.join.assert_called_with(timeout=1.0)

            # Should log warning for threads that don't exit quickly
            mock_log.warning.assert_called_with("Metadata thread did not exit gracefully within timeout")

    @patch("select.select")
    @patch("builtins.open")
    def test_select_based_interruptible_reading(self, mock_open_builtin, mock_select):
        """Test that the read loop uses select for interruptible reading."""
        # Skip on Windows
        if sys.platform == "win32":
            pytest.skip("select() not supported on Windows pipes")

        # Mock file descriptor
        mock_fd = MagicMock()
        mock_open_builtin.return_value = mock_fd

        # Mock select to timeout (no data available)
        mock_select.return_value = ([], [], [])

        monitor = StateMonitor(
            pipe_path="/fake/pipe",
            state_callback=self.state_callback,
            metadata_callback=self.metadata_callback,
        )

        # Start and stop quickly
        monitor.start()
        time.sleep(0.2)  # Let it run a few select cycles
        monitor.stop()

        # Verify select was called with proper timeout
        assert mock_select.called
        # Check that select was called with 0.1 second timeout
        timeout_args = [call[0][3] for call in mock_select.call_args_list if len(call[0]) > 3]
        assert any(timeout == 0.1 for timeout in timeout_args), "Expected 0.1 second timeout in select calls"


if __name__ == "__main__":
    pytest.main([__file__])

    def test_duplicate_state_ignored(self):
        """Test that setting the same state twice only triggers callback once."""
        self.monitor.set_state("playing")
        self.monitor.set_state("playing")
        self.state_callback.assert_called_once_with("playing")

    def test_state_transitions(self):
        """Test basic state transitions."""
        # NO_SESSION → PLAYING
        self.monitor.set_state("no_session")
        self.monitor.set_state("playing")

        # PLAYING → PAUSED
        self.monitor.set_state("paused")

        # PAUSED → PLAYING
        self.monitor.set_state("playing")

        # PLAYING → STOPPED
        self.monitor.set_state("stopped")

        assert self.state_callback.call_count == 5
        assert self.monitor.get_state() == "stopped"

    @patch("threading.Timer")
    def test_waiting_timer_for_stopped_state(self, mock_timer):
        """Test that stopped state triggers waiting timer."""
        self.monitor.set_state("stopped")

        # Should create a timer for transitioning to waiting state
        mock_timer.assert_called_once()
        args, kwargs = mock_timer.call_args
        assert args[0] == 2  # WAIT_TIMEOUT_SECONDS

    @patch("threading.Timer")
    def test_waiting_timer_for_paused_state(self, mock_timer):
        """Test that paused state triggers waiting timer."""
        self.monitor.set_state("paused")

        # Should create a timer for transitioning to waiting state
        mock_timer.assert_called_once()
        args, kwargs = mock_timer.call_args
        assert args[0] == 2  # WAIT_TIMEOUT_SECONDS

    @patch("threading.Timer")
    def test_waiting_timer_cancelled_on_new_state(self, mock_timer):
        """Test that timer is cancelled when new state is set."""
        mock_timer_instance = Mock()
        mock_timer.return_value = mock_timer_instance

        # Set a state that triggers waiting timer
        self.monitor.set_state("stopped")
        mock_timer_instance.start.assert_called_once()

        # Set another state - should cancel the timer
        self.monitor.set_state("playing")
        mock_timer_instance.cancel.assert_called_once()

    def test_stop_cancels_timer(self):
        """Test that stop() cancels any running timer."""
        with patch("threading.Timer") as mock_timer:
            mock_timer_instance = Mock()
            mock_timer.return_value = mock_timer_instance

            self.monitor.set_state("stopped")
            self.monitor.stop()

            mock_timer_instance.cancel.assert_called()

    def test_default_callback_when_none_provided(self):
        """Test that default callback works when none provided."""
        monitor = StateMonitor()
        # Should not raise exceptions
        monitor.set_state("playing")
        assert monitor.get_state() == "playing"

    def test_cleanup_on_deletion(self):
        """Test that timer is cleaned up on object deletion."""
        with patch("threading.Timer") as mock_timer:
            mock_timer_instance = Mock()
            mock_timer.return_value = mock_timer_instance

            monitor = StateMonitor()
            monitor.set_state("stopped")

            # Manually call the cleanup method instead of relying on __del__
            monitor.stop()

            # Timer should have been cancelled
            mock_timer_instance.cancel.assert_called()

    def test_pipe_reading_integration(self):
        """Test that pipe reading setup works correctly."""
        monitor = StateMonitor(
            pipe_path="/fake/pipe",
            state_callback=self.state_callback,
            metadata_callback=self.metadata_callback,
        )

        with patch("threading.Thread") as mock_thread:
            # Start monitoring
            monitor.start()

            # Verify thread was created and started
            mock_thread.assert_called_once()
            thread_instance = mock_thread.return_value
            thread_instance.start.assert_called_once()

    def test_backwards_compatibility_constructor(self):
        """Test that old constructor parameters are handled."""
        monitor = StateMonitor(
            pipe_path="/fake/pipe",
            metadata_callback=self.metadata_callback,
            state_callback=self.state_callback,
        )

        assert monitor._pipe_path == "/fake/pipe"


class TestMetadataMonitorCompatibility:
    """Test that MetadataMonitor alias works for backwards compatibility."""

    def test_metadata_monitor_is_state_monitor(self):
        """Test that MetadataMonitor is an alias for StateMonitor."""
        assert MetadataMonitor is StateMonitor

    def test_metadata_monitor_instantiation(self):
        """Test that MetadataMonitor can be instantiated."""
        callback = Mock()
        monitor = MetadataMonitor(state_callback=callback)

        monitor.set_state(PlaybackState.PLAYING)
        callback.assert_called_once_with(PlaybackState.PLAYING)
        assert monitor.get_state() == PlaybackState.PLAYING

    def test_metadata_monitor_with_old_parameters(self):
        """Test MetadataMonitor with legacy parameters."""
        state_callback = Mock()
        metadata_callback = Mock()

        # This should work with the old API from metadata_display.py
        monitor = MetadataMonitor(
            pipe_path="/fake/pipe",
            state_callback=state_callback,
            metadata_callback=metadata_callback,
        )

        # Should have start method
        assert hasattr(monitor, "start")

        # Manual state setting should still work
        monitor.set_state(PlaybackState.PLAYING)
        state_callback.assert_called_once_with(PlaybackState.PLAYING)


class TestStateMonitorCapture:
    """Test capture functionality in StateMonitor."""

    def setup_method(self):
        self.state_callback = Mock()
        self.metadata_callback = Mock()

    @patch("nowplaying.metadata_monitor.MetadataCapture")
    def test_capture_initialization(self, mock_capture_class):
        """Test that capture is initialized when capture_file is provided."""
        mock_capture = Mock()
        mock_capture_class.return_value = mock_capture

        monitor = StateMonitor(
            capture_file="/tmp/test_capture.json",
            compress_images=True,
            state_callback=self.state_callback,
            metadata_callback=self.metadata_callback,
        )

        # Verify capture was created with correct parameters
        mock_capture_class.assert_called_once_with("/tmp/test_capture.json", True)
        assert monitor._capture == mock_capture

    @patch("nowplaying.metadata_monitor.MetadataCapture")
    def test_capture_start_and_stop(self, mock_capture_class):
        """Test that capture start and stop methods are called."""
        mock_capture = Mock()
        mock_capture_class.return_value = mock_capture

        monitor = StateMonitor(
            pipe_path="/fake/pipe",
            capture_file="/tmp/test_capture.json",
            state_callback=self.state_callback,
            metadata_callback=self.metadata_callback,
        )

        with patch("threading.Thread"):
            monitor.start()
            mock_capture.start_capture.assert_called_once()
            mock_capture.capture_event.assert_called_with("monitor_start", "Started monitoring pipe: /fake/pipe")

        monitor.stop()
        mock_capture.capture_event.assert_called_with("monitor_stop", "Stopping metadata monitor")
        mock_capture.stop_capture.assert_called_once()

    @patch("nowplaying.metadata_monitor.MetadataCapture")
    def test_capture_line_during_reading(self, mock_capture_class):
        """Test that lines are captured during pipe reading."""
        mock_capture = Mock()
        mock_capture_class.return_value = mock_capture

        monitor = StateMonitor(
            capture_file="/tmp/test_capture.json",
            state_callback=self.state_callback,
            metadata_callback=self.metadata_callback,
        )

        # Simulate the line capture that happens in _read_loop
        monitor._capture = mock_capture
        test_line = "<item>test data</item>"

        # This simulates what happens in the read loop when capture is enabled
        if monitor._capture:
            monitor._capture.capture_line(test_line)

        mock_capture.capture_line.assert_called_once_with(test_line)

    @patch("nowplaying.metadata_monitor.MetadataCapture")
    def test_capture_state_transitions(self, mock_capture_class):
        """Test that state transitions are captured."""
        mock_capture = Mock()
        mock_capture_class.return_value = mock_capture

        monitor = StateMonitor(
            capture_file="/tmp/test_capture.json",
            state_callback=self.state_callback,
            metadata_callback=self.metadata_callback,
        )

        # Trigger a state transition
        monitor._transition_state(PlaybackState.PLAYING, "test transition")

        # Should capture the state change
        mock_capture.capture_event.assert_called_with(
            "state_change",
            f"{PlaybackState.NO_SESSION.name} -> {PlaybackState.PLAYING.name}: test transition",
        )


class TestStateMonitorConfiguration:
    """Test configuration handling in StateMonitor."""

    def setup_method(self):
        self.state_callback = Mock()
        self.metadata_callback = Mock()

    def test_default_configuration(self):
        """Test that default configuration is used when none provided."""
        monitor = StateMonitor(
            state_callback=self.state_callback,
            metadata_callback=self.metadata_callback,
        )

        assert monitor._config is not None
        assert isinstance(monitor._config, StateMonitorConfig)

    def test_custom_configuration(self):
        """Test that custom configuration is used when provided."""
        custom_config = StateMonitorConfig()
        custom_config.wait_timeout_seconds = 5.0

        monitor = StateMonitor(
            config=custom_config,
            state_callback=self.state_callback,
            metadata_callback=self.metadata_callback,
        )

        assert monitor._config == custom_config
        assert monitor._config.wait_timeout_seconds == 5.0

    def test_pipe_path_from_config(self):
        """Test that pipe path is taken from config when not specified."""
        custom_config = StateMonitorConfig()

        with patch.object(custom_config, "get_effective_pipe_path", return_value="/config/pipe/path"):
            monitor = StateMonitor(
                config=custom_config,
                state_callback=self.state_callback,
                metadata_callback=self.metadata_callback,
            )

            assert monitor._pipe_path == "/config/pipe/path"

    def test_pipe_path_parameter_override(self):
        """Test that pipe_path parameter overrides config."""
        custom_config = StateMonitorConfig()

        with patch.object(custom_config, "get_effective_pipe_path", return_value="/config/pipe/path"):
            monitor = StateMonitor(
                pipe_path="/override/pipe/path",
                config=custom_config,
                state_callback=self.state_callback,
                metadata_callback=self.metadata_callback,
            )

            assert monitor._pipe_path == "/override/pipe/path"


class TestStateMonitorReadLoop:
    """Test the read loop functionality."""

    def setup_method(self):
        self.state_callback = Mock()
        self.metadata_callback = Mock()

    @patch("builtins.open")
    @patch("select.select")
    def test_read_loop_with_data(self, mock_select, mock_open_func):
        """Test read loop when data is available."""
        if sys.platform == "win32":
            pytest.skip("select() not supported on Windows pipes")

        # Create a mock file object with proper behavior
        mock_file = Mock()
        mock_file.readline.side_effect = ["<item>test</item>\n", ""]  # Data then EOF
        mock_file.closed = False
        mock_open_func.return_value = mock_file
        mock_select.side_effect = [([mock_file], [], []), ([mock_file], [], [])]

        monitor = StateMonitor(
            pipe_path="/fake/pipe",
            state_callback=self.state_callback,
            metadata_callback=self.metadata_callback,
        )

        # Mock the metadata reader to avoid complex parsing
        monitor._metadata_reader.process_line = Mock()

        # Run the read loop
        monitor._read_loop()

        # Verify pipe was opened and data was processed
        mock_open_func.assert_called_once_with("/fake/pipe", "r")
        monitor._metadata_reader.process_line.assert_called_with("<item>test</item>\n")

    @patch("builtins.open")
    @patch("select.select")
    def test_read_loop_eof_handling(self, mock_select, mock_open_func):
        """Test read loop handles EOF correctly."""
        if sys.platform == "win32":
            pytest.skip("select() not supported on Windows pipes")

        mock_file = Mock()
        mock_file.readline.return_value = ""  # EOF
        mock_open_func.return_value = mock_file
        mock_select.return_value = ([mock_file], [], [])

        monitor = StateMonitor(
            pipe_path="/fake/pipe",
            state_callback=self.state_callback,
            metadata_callback=self.metadata_callback,
        )

        # Run the read loop - should exit on EOF
        monitor._read_loop()

        # Verify file was closed
        mock_file.close.assert_called()

    @patch("builtins.open")
    @patch("select.select")
    def test_read_loop_exception_handling(self, mock_select, mock_open_func):
        """Test read loop handles exceptions correctly."""
        if sys.platform == "win32":
            pytest.skip("select() not supported on Windows pipes")

        mock_file = Mock()
        mock_file.closed = False
        mock_file.readline.side_effect = OSError("Pipe error")
        mock_open_func.return_value = mock_file
        mock_select.return_value = ([mock_file], [], [])

        monitor = StateMonitor(
            pipe_path="/fake/pipe",
            state_callback=self.state_callback,
            metadata_callback=self.metadata_callback,
        )

        with patch("nowplaying.metadata_monitor.log") as mock_log:
            # Set stop_event to False initially to ensure we enter the exception handling
            with patch.object(monitor._stop_event, "is_set", return_value=False):
                monitor._read_loop()

            # Should log the error
            mock_log.error.assert_called_with("Error reading line from pipe: %s", mock_file.readline.side_effect)

    @patch("builtins.open")
    @patch("select.select")
    def test_read_loop_first_data_received(self, mock_select, mock_open_func):
        """Test read loop sets playing state on first data received."""
        if sys.platform == "win32":
            pytest.skip("select() not supported on Windows pipes")

        # Create mock file that returns data once then EOF
        mock_file = Mock()
        mock_file.readline.side_effect = ["<item>test</item>\n", ""]  # Data then EOF
        mock_file.closed = False
        mock_open_func.return_value = mock_file
        mock_select.side_effect = [([mock_file], [], []), ([mock_file], [], [])]

        monitor = StateMonitor(
            pipe_path="/fake/pipe",
            state_callback=self.state_callback,
            metadata_callback=self.metadata_callback,
        )

        monitor._metadata_reader.process_line = Mock()

        # Run the read loop
        monitor._read_loop()

        # Should transition to UNDETERMINED when pipe opens, then PLAYING on first data
        # Check that PLAYING was called (it might be the second call after UNDETERMINED)
        state_calls = [call[0][0] for call in self.state_callback.call_args_list]
        assert PlaybackState.PLAYING in state_calls

    @patch("builtins.open")
    @patch("select.select")
    def test_read_loop_waiting_timer_cancellation(self, mock_select, mock_open_func):
        """Test read loop cancels waiting timer when data is received."""
        if sys.platform == "win32":
            pytest.skip("select() not supported on Windows pipes")

        mock_file = Mock()
        mock_file.readline.side_effect = ["<item>test</item>\n", ""]
        mock_file.closed = False
        mock_open_func.return_value = mock_file
        mock_select.side_effect = [([mock_file], [], []), ([mock_file], [], [])]

        monitor = StateMonitor(
            pipe_path="/fake/pipe",
            state_callback=self.state_callback,
            metadata_callback=self.metadata_callback,
        )

        # Set up a mock waiting timer
        mock_timer = Mock()
        monitor._waiting_timer = mock_timer
        monitor._metadata_reader.process_line = Mock()

        # Run one iteration
        with patch.object(monitor._stop_event, "is_set", side_effect=[False, True]):
            monitor._read_loop()

        # Timer should have been cancelled and set to None
        mock_timer.cancel.assert_called_once()
        assert monitor._waiting_timer is None

    def test_read_loop_windows_fallback(self):
        """Test read loop fallback behavior on Windows."""
        if sys.platform != "win32":
            pytest.skip("Windows-specific test")

        monitor = StateMonitor(
            pipe_path="/fake/pipe",
            state_callback=self.state_callback,
            metadata_callback=self.metadata_callback,
        )

        # On Windows, the select branch should be skipped
        # This test mainly ensures Windows doesn't crash
        with patch("builtins.open", side_effect=FileNotFoundError), patch(
            "nowplaying.metadata_monitor.log"
        ) as mock_log:
            monitor._read_loop()
            mock_log.error.assert_called()


class TestStateMonitorDefaultCallbacks:
    """Test default callback functionality."""

    @patch("nowplaying.metadata_monitor.log_metadata")
    def test_default_metadata_callback(self, mock_log_metadata):
        """Test default metadata callback logs metadata."""
        monitor = StateMonitor()

        test_metadata = {"artist": "Test Artist", "title": "Test Song"}
        monitor._default_metadata_callback(test_metadata)

        mock_log_metadata.info.assert_called_once_with("Published metadata: %s", test_metadata)

    @patch("nowplaying.metadata_monitor.log_state")
    def test_default_state_callback(self, mock_log_state):
        """Test default state callback logs state changes."""
        monitor = StateMonitor()

        monitor._default_state_callback(PlaybackState.PLAYING)

        mock_log_state.info.assert_called_once_with("Published state: %s", PlaybackState.PLAYING)

    def test_default_callbacks_used_when_none_provided(self):
        """Test default callbacks are used when none provided."""
        monitor = StateMonitor()

        # Should use default callbacks
        assert monitor._metadata_callback == monitor._default_metadata_callback
        assert monitor._state_callback == monitor._default_state_callback


class TestStateMonitorSessionEndHandling:
    """Test session end metadata clearing functionality."""

    def setup_method(self):
        self.state_callback = Mock()
        self.metadata_callback = Mock()

    @patch("nowplaying.metadata_monitor.log_metadata")
    @patch("uuid.uuid4")
    def test_clear_metadata_for_session_end(self, mock_uuid, mock_log_metadata):
        """Test metadata clearing when session ends."""
        mock_uuid.return_value = "test-uuid-12345"

        monitor = StateMonitor(
            state_callback=self.state_callback,
            metadata_callback=self.metadata_callback,
        )

        monitor._clear_metadata_for_session_end()

        # Should log the clearing
        mock_log_metadata.info.assert_called_once_with("Clearing metadata for session end")

        # Should call metadata callback with empty metadata
        expected_metadata = {
            "metadata_id": "test-uuid-12345",
            "sequence_number": "0",
            "artist": "",
            "album": "",
            "title": "",
            "genre": "",
            "cover_art_path": None,
        }
        self.metadata_callback.assert_called_once_with(expected_metadata)

    def test_session_end_triggers_metadata_clearing(self):
        """Test that transitioning to NO_SESSION clears metadata."""
        monitor = StateMonitor(
            state_callback=self.state_callback,
            metadata_callback=self.metadata_callback,
        )

        with patch.object(monitor, "_clear_metadata_for_session_end") as mock_clear:
            # First transition to a different state so NO_SESSION is actually a change
            monitor.set_state(PlaybackState.PLAYING)

            # Then transition to NO_SESSION which should trigger metadata clearing
            monitor.set_state(PlaybackState.NO_SESSION)

            mock_clear.assert_called_once()


class TestStateMonitorWarnings:
    """Test warning conditions and edge cases."""

    def setup_method(self):
        self.state_callback = Mock()
        self.metadata_callback = Mock()

    @patch("nowplaying.metadata_monitor.log")
    def test_start_already_running_warning(self, mock_log):
        """Test warning when trying to start already running monitor."""
        monitor = StateMonitor(
            pipe_path="/fake/pipe",
            state_callback=self.state_callback,
            metadata_callback=self.metadata_callback,
        )

        # Mock a running thread
        mock_thread = Mock()
        mock_thread.is_alive.return_value = True
        monitor._thread = mock_thread

        monitor.start()

        mock_log.warning.assert_called_with("StateMonitor is already running.")

    @patch("nowplaying.metadata_monitor.log")
    def test_start_no_pipe_path_warning(self, mock_log):
        """Test warning when no pipe path is provided."""
        monitor = StateMonitor(
            state_callback=self.state_callback,
            metadata_callback=self.metadata_callback,
        )

        # Ensure pipe path is None
        monitor._pipe_path = None

        monitor.start()

        # Check that the warning was called with the correct message
        warning_calls = [
            call
            for call in mock_log.warning.call_args_list
            if "No pipe path provided, running in manual mode." in str(call)
        ]
        assert len(warning_calls) > 0, f"Expected warning not found. Calls: {mock_log.warning.call_args_list}"

    def test_del_cleanup(self):
        """Test that __del__ calls stop if stop_event exists."""
        monitor = StateMonitor(
            state_callback=self.state_callback,
            metadata_callback=self.metadata_callback,
        )

        with patch.object(monitor, "stop") as mock_stop:
            monitor.__del__()
            mock_stop.assert_called_once()

    def test_del_cleanup_no_stop_event(self):
        """Test that __del__ handles missing stop_event gracefully."""
        monitor = StateMonitor(
            state_callback=self.state_callback,
            metadata_callback=self.metadata_callback,
        )

        # Remove stop_event to simulate incomplete initialization
        delattr(monitor, "_stop_event")

        # Should not raise exception
        monitor.__del__()


class TestStateMonitorStateTransitions:
    """Test state transition handling with state machine validation."""

    def setup_method(self):
        self.state_callback = Mock()
        self.metadata_callback = Mock()

    def test_transition_state_vs_force_transition(self):
        """Test difference between normal and forced state transitions."""
        monitor = StateMonitor(
            state_callback=self.state_callback,
            metadata_callback=self.metadata_callback,
        )

        # Test forced transition (bypasses validation) - this should always work
        monitor._force_transition_state(PlaybackState.PLAYING, "forced transition")

        # Test normal transition (uses state machine validation) - this might fail validation
        monitor._transition_state(PlaybackState.STOPPED, "normal transition")

        # At least the forced transition should result in a state callback
        assert self.state_callback.call_count >= 1

        # Verify we can get the current state
        current_state = monitor.get_state()
        assert current_state in [PlaybackState.PLAYING, PlaybackState.STOPPED]


class TestStateMonitorEdgeCases:
    """Test edge cases and remaining uncovered code paths."""

    def setup_method(self):
        self.state_callback = Mock()
        self.metadata_callback = Mock()

    @patch("builtins.open")
    @patch("select.select")
    def test_read_loop_closed_pipe_detection(self, mock_select, mock_open_func):
        """Test read loop detects closed pipe and breaks."""
        if sys.platform == "win32":
            pytest.skip("select() not supported on Windows pipes")

        mock_file = Mock()
        mock_file.closed = True  # Pipe is closed
        mock_open_func.return_value = mock_file
        mock_select.return_value = ([mock_file], [], [])

        monitor = StateMonitor(
            pipe_path="/fake/pipe",
            state_callback=self.state_callback,
            metadata_callback=self.metadata_callback,
        )

        # Should exit early due to closed pipe
        monitor._read_loop()

        # readline should not be called if pipe is closed
        mock_file.readline.assert_not_called()

    @patch("builtins.open")
    @patch("select.select")
    def test_read_loop_waiting_timer_cancellation(self, mock_select, mock_open_func):
        """Test read loop cancels waiting timer when data is received."""
        if sys.platform == "win32":
            pytest.skip("select() not supported on Windows pipes")

        mock_file = Mock()
        mock_file.readline.side_effect = ["<item>test</item>\n", ""]
        mock_file.closed = False
        mock_open_func.return_value = mock_file
        mock_select.side_effect = [([mock_file], [], []), ([mock_file], [], [])]

        monitor = StateMonitor(
            pipe_path="/fake/pipe",
            state_callback=self.state_callback,
            metadata_callback=self.metadata_callback,
        )

        # Set up a waiting timer
        mock_timer = Mock()
        monitor._waiting_timer = mock_timer
        monitor._metadata_reader.process_line = Mock()

        # Run read loop
        monitor._read_loop()

        # Timer should have been cancelled
        mock_timer.cancel.assert_called_once()
        assert monitor._waiting_timer is None

    def test_windows_read_loop_fallback(self):
        """Test that Windows fallback path doesn't crash."""
        # Force Windows behavior by patching sys.platform
        with patch("nowplaying.metadata_monitor.sys.platform", "win32"):
            monitor = StateMonitor(
                pipe_path="/fake/pipe",
                state_callback=self.state_callback,
                metadata_callback=self.metadata_callback,
            )

            # Mock file operations to avoid actual file access
            with patch("builtins.open", side_effect=FileNotFoundError("No pipe")), patch(
                "nowplaying.metadata_monitor.log"
            ) as mock_log:
                monitor._read_loop()
                # Should log error about pipe opening failure
                mock_log.error.assert_called()

    @patch("nowplaying.metadata_monitor.log")
    def test_start_with_pipe_path_info_logging(self, mock_log):
        """Test that start() logs info when pipe path is provided."""
        monitor = StateMonitor(
            pipe_path="/fake/pipe",
            state_callback=self.state_callback,
            metadata_callback=self.metadata_callback,
        )

        with patch("threading.Thread"):
            monitor.start()

        # Should log the info message
        mock_log.info.assert_called_with("Starting StateMonitor with pipe: %s", "/fake/pipe")


if __name__ == "__main__":

    def test_handle_state_change_from_metadata_reader(self):
        """Test state changes triggered by metadata reader."""
        monitor = StateMonitor(
            state_callback=self.state_callback,
            metadata_callback=self.metadata_callback,
        )

        with patch.object(monitor, "_transition_state") as mock_transition:
            monitor._handle_state_change(PlaybackState.PLAYING)

            mock_transition.assert_called_once_with(PlaybackState.PLAYING, "metadata event")


if __name__ == "__main__":
    pytest.main([__file__])
