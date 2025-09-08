"""
Tests for the StateMonitor class (formerly MetadataMonitor).
"""

import sys
import time
from unittest.mock import MagicMock, Mock, patch

import pytest

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
        self.metadata_callback.assert_called_once_with(
            {
                "artist": "Test Artist",
                "album": "Test Album",
                "title": "Test Song",
                "genre": "Rock",
            }
        )

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
            pipe_path="/fake/pipe", state_callback=self.state_callback, metadata_callback=self.metadata_callback
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


if __name__ == "__main__":
    pytest.main([__file__])
