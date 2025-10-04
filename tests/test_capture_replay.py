"""Tests for the metadata capture and replay functionality."""

import json
import tempfile
import time
import unittest
from pathlib import Path

from nowplaying.capture_replay import MetadataCapture, MetadataReplay, create_capture_filename


class TestMetadataCapture(unittest.TestCase):
    """Test metadata capture functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.capture_file = Path(self.temp_dir) / "test_capture.jsonl"

    def test_capture_creation(self):
        """Test creating a capture instance."""
        capture = MetadataCapture(str(self.capture_file))
        self.assertIsNotNone(capture)
        self.assertFalse(self.capture_file.exists())

    def test_capture_start_stop(self):
        """Test starting and stopping capture."""
        capture = MetadataCapture(str(self.capture_file))

        capture.start_capture()
        self.assertTrue(self.capture_file.exists())

        capture.stop_capture()

        # Verify file contains header and footer
        with open(self.capture_file, "r") as f:
            lines = f.readlines()

        self.assertGreaterEqual(len(lines), 2)

        # Check header
        header = json.loads(lines[0])
        self.assertEqual(header["type"], "capture_header")
        self.assertIn("start_time", header)

        # Check footer
        footer = json.loads(lines[-1])
        self.assertEqual(footer["type"], "capture_footer")
        self.assertIn("end_time", footer)

    def test_capture_lines(self):
        """Test capturing metadata lines."""
        capture = MetadataCapture(str(self.capture_file))
        capture.start_capture()

        # Capture some test lines
        test_lines = [
            '<item><type>636f7265</type><code>6173616c</code><length>10</length><data encoding="base64">VGVzdCBBbGJ1bQ==</data></item>',
            '<item><type>636f7265</type><code>61736172</code><length>11</length><data encoding="base64">VGVzdCBBcnRpc3Q=</data></item>',
        ]

        for line in test_lines:
            capture.capture_line(line)
            time.sleep(0.1)  # Small delay between captures

        capture.stop_capture()

        # Verify captured data
        with open(self.capture_file, "r") as f:
            lines = f.readlines()

        # Should have header + test lines + footer
        self.assertEqual(len(lines), len(test_lines) + 2)

        # Check captured lines
        for i, original_line in enumerate(test_lines):
            captured = json.loads(lines[i + 1])  # Skip header
            self.assertEqual(captured["type"], "metadata_line")
            self.assertEqual(captured["data"], original_line)
            self.assertIn("timestamp", captured)
            self.assertIn("gap_since_last", captured)

    def test_capture_events(self):
        """Test capturing events."""
        capture = MetadataCapture(str(self.capture_file))
        capture.start_capture()

        # Capture some events
        capture.capture_event("state_change", "STOPPED -> PLAYING")
        capture.capture_event("error", "Test error message")

        capture.stop_capture()

        # Verify events were captured
        with open(self.capture_file, "r") as f:
            lines = f.readlines()

        # Find event lines
        events = []
        for line in lines:
            data = json.loads(line)
            if data["type"] == "event":
                events.append(data)

        self.assertEqual(len(events), 2)

        # Check first event
        self.assertEqual(events[0]["event_type"], "state_change")
        self.assertEqual(events[0]["description"], "STOPPED -> PLAYING")

        # Check second event
        self.assertEqual(events[1]["event_type"], "error")
        self.assertEqual(events[1]["description"], "Test error message")


class TestMetadataReplay(unittest.TestCase):
    """Test metadata replay functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.capture_file = Path(self.temp_dir) / "test_replay.jsonl"
        self._create_test_capture()

    def _create_test_capture(self):
        """Create a test capture file for replay testing."""
        capture = MetadataCapture(str(self.capture_file))
        capture.start_capture()

        # Add some test data with delays
        capture.capture_line(
            '<item><type>636f7265</type><code>6173616c</code><length>10</length><data encoding="base64">VGVzdCBBbGJ1bQ==</data></item>'
        )
        time.sleep(0.2)

        capture.capture_event("state_change", "STOPPED -> PLAYING")
        time.sleep(0.1)

        capture.capture_line(
            '<item><type>636f7265</type><code>61736172</code><length>11</length><data encoding="base64">VGVzdCBBcnRpc3Q=</data></item>'
        )
        time.sleep(0.5)  # Longer gap for fast-forward testing

        capture.capture_line(
            '<item><type>636f7265</type><code>6d696e6d</code><length>10</length><data encoding="base64">VGVzdCBUaXRsZQ==</data></item>'
        )

        capture.stop_capture()

    def test_replay_creation(self):
        """Test creating a replay instance."""
        replay = MetadataReplay(str(self.capture_file))
        self.assertIsNotNone(replay)

    def test_replay_nonexistent_file(self):
        """Test replay with nonexistent file."""
        with self.assertRaises(FileNotFoundError):
            MetadataReplay("/nonexistent/file.jsonl")

    def test_get_capture_info(self):
        """Test getting capture file information."""
        replay = MetadataReplay(str(self.capture_file))
        info = replay.get_capture_info()

        self.assertIn("file_path", info)
        self.assertIn("file_size", info)
        self.assertIn("line_count", info)
        self.assertIn("event_count", info)
        self.assertIn("duration", info)

        # Should have captured 3 metadata lines and 1 event
        self.assertEqual(info["line_count"], 3)
        self.assertEqual(info["event_count"], 1)
        self.assertGreater(info["duration"], 0)

    def test_replay_with_callbacks(self):
        """Test replaying with line and event callbacks."""
        replay = MetadataReplay(str(self.capture_file), fast_forward_gaps=False)

        captured_lines = []
        captured_events = []

        def line_callback(line: str):
            captured_lines.append(line)

        def event_callback(event_type: str, description: str, timestamp: float):
            captured_events.append((event_type, description, timestamp))

        start_time = time.time()
        replay.replay(line_callback, event_callback)
        end_time = time.time()

        # Should have captured the expected lines and events
        self.assertEqual(len(captured_lines), 3)
        self.assertEqual(len(captured_events), 1)

        # Check that actual timing was preserved (approximately)
        replay_duration = end_time - start_time
        self.assertGreater(replay_duration, 0.6)  # Should be close to original 0.8s

        # Check event details
        event_type, description, timestamp = captured_events[0]
        self.assertEqual(event_type, "state_change")
        self.assertEqual(description, "STOPPED -> PLAYING")

    def test_replay_with_fast_forward(self):
        """Test replaying with fast-forward enabled."""
        replay = MetadataReplay(str(self.capture_file), fast_forward_gaps=True, max_gap_seconds=0.3)

        captured_lines = []

        def line_callback(line: str):
            captured_lines.append(line)

        start_time = time.time()
        replay.replay(line_callback)
        end_time = time.time()

        # Should still capture all lines
        self.assertEqual(len(captured_lines), 3)

        # But should be faster due to fast-forward
        replay_duration = end_time - start_time
        self.assertLess(replay_duration, 0.5)  # Should be much faster than original


class TestCreateCaptureFilename(unittest.TestCase):
    """Test capture filename generation."""

    def test_default_filename(self):
        """Test default filename generation."""
        filename = create_capture_filename()
        self.assertTrue(filename.startswith("/tmp/metadata_capture_"))
        self.assertTrue(filename.endswith(".jsonl"))

    def test_custom_prefix(self):
        """Test filename generation with custom prefix."""
        filename = create_capture_filename("debug_session")
        self.assertTrue(filename.startswith("/tmp/debug_session_"))
        self.assertTrue(filename.endswith(".jsonl"))

    def test_filename_uniqueness(self):
        """Test that filenames are unique across calls."""
        filename1 = create_capture_filename()
        time.sleep(1.1)  # Ensure different timestamp
        filename2 = create_capture_filename()
        self.assertNotEqual(filename1, filename2)


if __name__ == "__main__":
    unittest.main()
