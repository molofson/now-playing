"""Tests for StateMonitor integration with capture functionality."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from nowplaying.metadata_monitor import StateMonitor
from nowplaying.playback_state import PlaybackState


class TestStateMonitorCapture(unittest.TestCase):
    """Test StateMonitor with capture functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.capture_file = Path(self.temp_dir) / "test_monitor_capture.jsonl"

    def test_monitor_with_capture_initialization(self):
        """Test StateMonitor with capture file parameter."""
        metadata_callback = Mock()
        state_callback = Mock()

        monitor = StateMonitor(
            pipe_path="/tmp/test_pipe",
            metadata_callback=metadata_callback,
            state_callback=state_callback,
            capture_file=str(self.capture_file),
        )

        # Should have capture instance
        self.assertIsNotNone(monitor._capture)

    def test_monitor_without_capture(self):
        """Test StateMonitor without capture (normal operation)."""
        metadata_callback = Mock()
        state_callback = Mock()

        monitor = StateMonitor(
            pipe_path="/tmp/test_pipe",
            metadata_callback=metadata_callback,
            state_callback=state_callback,
        )

        # Should not have capture instance
        self.assertIsNone(monitor._capture)

    @patch("nowplaying.metadata_monitor.open")
    @patch("nowplaying.metadata_monitor.select.select")
    @patch("os.path.exists")
    def test_capture_during_monitoring(self, mock_exists, mock_select, mock_open):
        """Test that metadata lines are captured during monitoring."""
        # Mock file operations
        mock_exists.return_value = True
        mock_file = Mock()
        mock_file.readline.side_effect = [
            '<item><type>636f7265</type><code>6173616c</code><length>10</length><data encoding="base64">VGVzdCBBbGJ1bQ==</data></item>\n',
            '<item><type>636f7265</type><code>61736172</code><length>11</length><data encoding="base64">VGVzdCBBcnRpc3Q=</data></item>\n',
            "",  # EOF
        ]
        mock_open.return_value.__enter__.return_value = mock_file
        mock_select.return_value = ([mock_file], [], [])

        metadata_callback = Mock()
        state_callback = Mock()

        # Create monitor with capture
        monitor = StateMonitor(
            pipe_path="/tmp/test_pipe",
            metadata_callback=metadata_callback,
            state_callback=state_callback,
            capture_file=str(self.capture_file),
        )

        # Mock the capture to track calls
        monitor._capture = Mock()

        # Start monitoring (this will run the read loop in a thread)
        monitor.start()

        # Give it a moment to process
        import time

        time.sleep(0.1)

        # Stop monitoring
        monitor.stop()

        # Verify capture methods were called
        monitor._capture.start_capture.assert_called_once()
        monitor._capture.stop_capture.assert_called_once()

        # Should have captured start/stop events
        self.assertTrue(monitor._capture.capture_event.called)

        # Should have captured lines (at least the start event call)
        event_calls = monitor._capture.capture_event.call_args_list
        self.assertTrue(any("monitor_start" in str(call) for call in event_calls))

    def test_state_transition_capture(self):
        """Test that state transitions are captured."""
        metadata_callback = Mock()
        state_callback = Mock()

        monitor = StateMonitor(
            pipe_path="/tmp/test_pipe",
            metadata_callback=metadata_callback,
            state_callback=state_callback,
            capture_file=str(self.capture_file),
        )

        # Mock the capture
        monitor._capture = Mock()

        # Trigger a state transition
        monitor._transition_state(PlaybackState.PLAYING, "test transition")

        # Should have captured the state transition
        monitor._capture.capture_event.assert_called_with("state_change", "NO_SESSION -> PLAYING: test transition")

    def test_capture_file_format(self):
        """Test that capture file is created with correct format."""
        # This is an integration test that actually creates a capture file
        metadata_callback = Mock()
        state_callback = Mock()

        monitor = StateMonitor(
            pipe_path="/tmp/test_pipe",  # Provide a pipe path
            metadata_callback=metadata_callback,
            state_callback=state_callback,
            capture_file=str(self.capture_file),
        )

        # Mock the capture to avoid actual file operations during start/stop
        with patch.object(monitor, "_capture") as mock_capture:
            # Start and immediately stop to test the flow
            monitor.start()
            monitor.stop()

            # Verify capture methods would be called
            mock_capture.start_capture.assert_called_once()
            mock_capture.stop_capture.assert_called_once()

        # Test actual capture file creation separately
        capture = monitor._capture
        if capture:
            capture.start_capture()
            capture.capture_event("test", "Test capture file format")
            capture.stop_capture()

            # Verify capture file was created and has correct format
            self.assertTrue(self.capture_file.exists())

            with open(self.capture_file, "r") as f:
                lines = f.readlines()

            # Should have at least header, event, and footer
            self.assertGreaterEqual(len(lines), 3)

            # Check header
            header = json.loads(lines[0])
            self.assertEqual(header["type"], "capture_header")
            self.assertEqual(header["version"], "1.0")

            # Check footer
            footer = json.loads(lines[-1])
            self.assertEqual(footer["type"], "capture_footer")


if __name__ == "__main__":
    unittest.main()
