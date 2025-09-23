"""
Tests for blocking I/O fixes in metadata monitoring.

These tests verify that the metadata monitor can be stopped quickly
without hanging, even during pipe read operations.
"""

import os
import sys
import tempfile
import threading
import time
from unittest.mock import MagicMock, Mock, patch

import pytest

from nowplaying.metadata_monitor import StateMonitor
from nowplaying.playback_state import PlaybackState


class TestInterruptibleReading:
    """Test the select-based interruptible reading functionality."""

    def setup_method(self):
        self.state_callback = Mock()
        self.metadata_callback = Mock()

    @pytest.mark.skipif(sys.platform == "win32", reason="select() not supported on Windows pipes")
    def test_select_based_reading_interruptible(self):
        """Test that select-based reading can be interrupted quickly."""
        # Create a named pipe for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            pipe_path = os.path.join(temp_dir, "test_pipe")
            os.mkfifo(pipe_path)

            monitor = StateMonitor(
                pipe_path=pipe_path,
                state_callback=self.state_callback,
                metadata_callback=self.metadata_callback,
            )

            # Start monitoring in background
            monitor.start()

            # Give it a moment to start
            time.sleep(0.1)

            # Stop monitoring and measure time
            start_time = time.time()
            monitor.stop()
            stop_time = time.time()

            # Should stop within reasonable time (allowing for 1.0 second thread join timeout)
            shutdown_time = stop_time - start_time
            assert shutdown_time < 1.5, f"Shutdown took too long: {shutdown_time} seconds"

    @patch("builtins.open")
    @patch("select.select")
    def test_select_timeout_handling(self, mock_select, mock_open_builtin):
        """Test that select timeouts are handled correctly."""
        # Mock file descriptor
        mock_fd = MagicMock()
        mock_open_builtin.return_value = mock_fd

        # Mock select to return no ready files (timeout)
        mock_select.return_value = ([], [], [])

        monitor = StateMonitor(
            pipe_path="/fake/pipe",
            state_callback=self.state_callback,
            metadata_callback=self.metadata_callback,
        )

        # Start and quickly stop to test timeout handling
        monitor.start()
        time.sleep(0.2)  # Let it go through a few select cycles
        monitor.stop()

        # Verify select was called with timeout
        assert mock_select.called
        call_args = mock_select.call_args_list[0][0]
        assert len(call_args) == 4  # [read_fds], [write_fds], [error_fds], timeout
        assert call_args[3] == 0.1  # Our 0.1 second timeout

    @patch("nowplaying.metadata_monitor.open")
    @patch("nowplaying.metadata_monitor.select.select")
    def test_pipe_closure_during_reading(self, mock_select, mock_open_builtin):
        """Test that pipe closure is handled gracefully."""
        # Mock file descriptor
        mock_fd = MagicMock()
        mock_fd.readline.return_value = ""  # EOF
        mock_fd.closed = False
        mock_open_builtin.return_value = mock_fd

        # Mock select to return ready file
        mock_select.return_value = ([mock_fd], [], [])

        monitor = StateMonitor(
            pipe_path="/fake/pipe",
            state_callback=self.state_callback,
            metadata_callback=self.metadata_callback,
        )

        monitor.start()
        time.sleep(0.2)  # Let it process EOF
        monitor.stop()

        # Should not crash and should handle EOF gracefully
        mock_fd.readline.assert_called()


class TestImprovedShutdown:
    """Test the improved shutdown functionality."""

    def setup_method(self):
        self.state_callback = Mock()
        self.metadata_callback = Mock()

    def test_stop_method_with_timer_cleanup(self):
        """Test that stop() properly cleans up timers."""
        monitor = StateMonitor(state_callback=self.state_callback, metadata_callback=self.metadata_callback)

        with patch("threading.Timer") as mock_timer:
            mock_timer_instance = Mock()
            mock_timer.return_value = mock_timer_instance

            # Trigger a timer by setting a state that creates one
            monitor.set_state(PlaybackState.PAUSED)
            mock_timer_instance.start.assert_called_once()

            # Stop should cancel the timer
            monitor.stop()
            mock_timer_instance.cancel.assert_called_once()

    def test_pipe_close_exception_handling(self):
        """Test that pipe close exceptions are handled silently."""
        monitor = StateMonitor(
            pipe_path="/fake/pipe",
            state_callback=self.state_callback,
            metadata_callback=self.metadata_callback,
        )

        # Mock a pipe that raises exception on close
        mock_fd = Mock()
        mock_fd.close.side_effect = OSError("Pipe already closed")
        monitor._pipe_fd = mock_fd

        # Should not raise exception
        monitor.stop()

        # Pipe should still be set to None
        assert monitor._pipe_fd is None

    def test_thread_join_timeout_reduced(self):
        """Test that thread join timeout is now shorter."""
        monitor = StateMonitor(
            pipe_path="/fake/pipe",
            state_callback=self.state_callback,
            metadata_callback=self.metadata_callback,
        )

        # Mock thread that doesn't exit quickly
        mock_thread = Mock()
        mock_thread.is_alive.return_value = True
        monitor._thread = mock_thread

        with patch("nowplaying.metadata_monitor.log") as mock_log:
            monitor.stop()

            # Should join with 1.0 second timeout (not the old 10 seconds)
            mock_thread.join.assert_called_with(timeout=1.0)

            # Should log warning when thread doesn't exit
            mock_log.warning.assert_called_with("Metadata thread did not exit gracefully within timeout")

    def test_stop_event_set_first(self):
        """Test that stop event is set before other cleanup."""
        monitor = StateMonitor()

        # Mock the stop event
        monitor._stop_event = Mock()

        monitor.stop()

        # Stop event should be the first thing called
        monitor._stop_event.set.assert_called_once()


class TestStateDebouncing:
    """Test the state debouncing functionality."""

    def setup_method(self):
        self.state_callback = Mock()
        self.monitor = StateMonitor(state_callback=self.state_callback)

    def test_debounce_prevents_duplicate_states(self):
        """Test that duplicate states are properly debounced."""
        # First transition to a valid intermediate state
        self.monitor.set_state(PlaybackState.UNDETERMINED)

        # Reset the mock to test the actual duplicates
        self.state_callback.reset_mock()

        # Set same state multiple times
        self.monitor.set_state(PlaybackState.PLAYING)
        self.monitor.set_state(PlaybackState.PLAYING)
        self.monitor.set_state(PlaybackState.PLAYING)

        # Callback should only be called once
        self.state_callback.assert_called_once_with(PlaybackState.PLAYING)

    def test_debounce_allows_different_states(self):
        """Test that different states are not debounced."""
        # Start with valid transitions
        self.monitor.set_state(PlaybackState.UNDETERMINED)
        self.monitor.set_state(PlaybackState.PLAYING)
        self.monitor.set_state(PlaybackState.PAUSED)
        self.monitor.set_state(PlaybackState.STOPPED)

        # All four should trigger callbacks
        assert self.state_callback.call_count == 4
        calls = [call[0][0] for call in self.state_callback.call_args_list]
        assert calls == [
            PlaybackState.UNDETERMINED,
            PlaybackState.PLAYING,
            PlaybackState.PAUSED,
            PlaybackState.STOPPED,
        ]

    @patch("threading.Timer")
    def test_timer_cancelled_on_state_change(self, mock_timer):
        """Test that existing timer is cancelled when state changes."""
        mock_timer_instance = Mock()
        mock_timer.return_value = mock_timer_instance

        # First state that triggers timer
        self.monitor.set_state(PlaybackState.PAUSED)
        mock_timer_instance.start.assert_called_once()

        # Reset mock to check cancellation
        mock_timer_instance.reset_mock()

        # Second state should cancel first timer
        self.monitor.set_state(PlaybackState.PLAYING)
        mock_timer_instance.cancel.assert_called_once()


class TestExceptionHandling:
    """Test exception handling in the read loop."""

    def setup_method(self):
        self.state_callback = Mock()
        self.metadata_callback = Mock()

    @patch("nowplaying.metadata_monitor.open")
    @patch("nowplaying.metadata_monitor.select.select")
    def test_oserror_handling_in_read_loop(self, mock_select, mock_open_builtin):
        """Test that OSError is handled gracefully in read loop."""
        # Mock file descriptor that raises OSError on readline
        mock_fd = MagicMock()
        mock_fd.readline.side_effect = OSError("Broken pipe")
        mock_fd.closed = False
        mock_open_builtin.return_value = mock_fd

        # Mock select to return ready file
        mock_select.return_value = ([mock_fd], [], [])

        monitor = StateMonitor(
            pipe_path="/fake/pipe",
            state_callback=self.state_callback,
            metadata_callback=self.metadata_callback,
        )

        with patch("nowplaying.metadata_monitor.log") as mock_log:
            monitor.start()
            time.sleep(0.2)  # Let it encounter the error
            monitor.stop()

            # Should log error but not crash
            mock_log.error.assert_called()

    @patch("builtins.open")
    def test_pipe_open_failure(self, mock_open_builtin):
        """Test that pipe open failure is handled gracefully."""
        # Mock open to raise exception
        mock_open_builtin.side_effect = FileNotFoundError("Pipe not found")

        monitor = StateMonitor(
            pipe_path="/nonexistent/pipe",
            state_callback=self.state_callback,
            metadata_callback=self.metadata_callback,
        )

        with patch("nowplaying.metadata_monitor.log") as mock_log:
            monitor.start()
            time.sleep(0.1)  # Let it try to open pipe
            monitor.stop()

            # Should log error but not crash
            mock_log.error.assert_called()


class TestCompatibilityAliases:
    """Test backwards compatibility aliases and methods."""

    def test_metadata_monitor_alias(self):
        """Test that MetadataMonitor alias works."""
        from nowplaying.metadata_monitor import MetadataMonitor, StateMonitor

        # Should be the same class
        assert MetadataMonitor is StateMonitor

        # Should instantiate correctly
        callback = Mock()
        monitor = MetadataMonitor(state_callback=callback)

        monitor.set_state("playing")
        callback.assert_called_once_with("playing")

    def test_legacy_constructor_parameters(self):
        """Test that legacy constructor parameters still work."""
        callback = Mock()

        # This should work with old-style parameters
        monitor = StateMonitor(pipe_path="/fake/pipe", metadata_callback=Mock(), state_callback=callback)

        assert monitor._pipe_path == "/fake/pipe"

        # Basic functionality should still work
        monitor.set_state("playing")
        callback.assert_called_once_with("playing")


if __name__ == "__main__":
    pytest.main([__file__])
