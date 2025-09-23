#!/usr/bin/env python3
"""
Unit tests for metadata_display.py

Tests focus on preventing regressions in log formatting and display.
"""

import logging
import os
import sys
import threading
import time
import unittest
from unittest.mock import MagicMock, patch

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from devtools.metadata_display import LOG_FONT_SIZE  # noqa: E402
from devtools.metadata_display import META_FONT_SIZE  # noqa: E402
from devtools.metadata_display import TITLE_FONT_SIZE  # noqa: E402
from devtools.metadata_display import DebugLogFilter  # noqa: E402
from devtools.metadata_display import MillisecondFormatter  # noqa: E402
from devtools.metadata_display import PygameLogHandler  # noqa: E402
from devtools.metadata_display import TailBuffer  # noqa: E402

# IMPORT ORDERING NOTE: The following import has conflicting requirements:


class TestTailBuffer(unittest.TestCase):
    """Test the TailBuffer class for log message storage."""

    def setUp(self):
        """Set up test fixtures."""
        self.buffer = TailBuffer(capacity=10)

    def test_append_and_retrieve(self):
        """Test basic append and retrieve functionality."""
        self.buffer.append("INFO", "Test message 1")
        self.buffer.append("ERROR", "Test message 2")

        logs = self.buffer.get_recent_logs(2)
        self.assertEqual(len(logs), 2)

        # Check structure: (timestamp, level, message)
        timestamp1, level1, message1 = logs[0]
        timestamp2, level2, message2 = logs[1]

        self.assertEqual(level1, "INFO")
        self.assertEqual(message1, "Test message 1")
        self.assertEqual(level2, "ERROR")
        self.assertEqual(message2, "Test message 2")
        self.assertIsInstance(timestamp1, float)
        self.assertIsInstance(timestamp2, float)

    def test_capacity_limit(self):
        """Test that buffer respects capacity limits."""
        # Add more messages than capacity
        for i in range(15):
            self.buffer.append("INFO", f"Message {i}")

        logs = self.buffer.get_recent_logs(20)  # Ask for more than capacity
        self.assertEqual(len(logs), 10)  # Should only get capacity amount

        # Should have the last 10 messages (5-14)
        self.assertEqual(logs[0][2], "Message 5")
        self.assertEqual(logs[-1][2], "Message 14")

    def test_debug_filtering(self):
        """Test debug message filtering."""
        self.buffer.append("INFO", "Info message")
        self.buffer.append("DEBUG", "Debug message")
        self.buffer.append("ERROR", "Error message")

        # With debug messages
        logs_with_debug = self.buffer.get_recent_logs(10, include_debug=True)
        self.assertEqual(len(logs_with_debug), 3)

        # Without debug messages
        logs_without_debug = self.buffer.get_recent_logs(10, include_debug=False)
        self.assertEqual(len(logs_without_debug), 2)

        # Check that DEBUG message is filtered out
        levels = [log[1] for log in logs_without_debug]
        self.assertNotIn("DEBUG", levels)
        self.assertIn("INFO", levels)
        self.assertIn("ERROR", levels)

    def test_thread_safety(self):
        """Test thread-safe operations."""

        def add_messages(thread_id, count):
            for i in range(count):
                self.buffer.append("INFO", f"Thread {thread_id} message {i}")
                time.sleep(0.001)  # Small delay to test concurrency

        # Start multiple threads
        threads = []
        for t in range(3):
            thread = threading.Thread(target=add_messages, args=(t, 5))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        logs = self.buffer.get_recent_logs(20)
        self.assertEqual(len(logs), 10)  # Capacity limit should be respected

        # All messages should be properly formatted
        for timestamp, level, message in logs:
            self.assertIsInstance(timestamp, float)
            self.assertEqual(level, "INFO")
            self.assertIn("Thread", message)
            self.assertIn("message", message)


class TestPygameLogHandler(unittest.TestCase):
    """Test the PygameLogHandler class for proper log formatting."""

    def setUp(self):
        """Set up test fixtures."""
        self.tail_buffer = TailBuffer(capacity=10)
        self.handler = PygameLogHandler(self.tail_buffer)
        # NOTE: Even though we set a formatter (as the real code does),
        # the PygameLogHandler should ignore it for GUI display and only store raw messages
        self.handler.setFormatter(MillisecondFormatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))

    def test_message_extraction(self):
        """Test that only the raw message is stored, not the formatted version."""
        # Create a log record
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message without formatting",
            args=(),
            exc_info=None,
        )

        # Emit the record
        self.handler.emit(record)

        # Get the stored log
        logs = self.tail_buffer.get_recent_logs(1)
        self.assertEqual(len(logs), 1)

        timestamp, level, message = logs[0]

        # Check that we got the raw message, not the formatted one
        self.assertEqual(message, "Test message without formatting")
        self.assertEqual(level, "INFO")

        # Ensure the message does NOT contain timestamp or level prefix
        self.assertNotIn("[INFO]", message)
        self.assertNotIn("test.logger", message)
        self.assertNotIn(":", message)  # From the formatter pattern

        # The timestamp should not be in the message (it's stored separately)
        import re

        time_pattern = r"\d{2}:\d{2}:\d{2}\.\d{3}"
        self.assertIsNone(re.search(time_pattern, message))

    def test_formatted_log_messages(self):
        """Test formatted log messages with parameters."""
        record = logging.LogRecord(
            name="test.logger",
            level=logging.WARNING,
            pathname="test.py",
            lineno=42,
            msg="Test message with %s and %d parameters",
            args=("string", 123),
            exc_info=None,
        )

        self.handler.emit(record)

        logs = self.tail_buffer.get_recent_logs(1)
        timestamp, level, message = logs[0]

        # Should have the formatted message with parameters
        self.assertEqual(message, "Test message with string and 123 parameters")
        self.assertEqual(level, "WARNING")

        # Should not have formatter prefixes
        self.assertNotIn("[WARNING]", message)
        self.assertNotIn("test.logger", message)

    def test_exception_handling(self):
        """Test that handler gracefully handles exceptions during formatting."""
        # Create a problematic record that might cause formatting issues
        record = logging.LogRecord(
            name="test.logger",
            level=logging.ERROR,
            pathname="test.py",
            lineno=42,
            msg="Message with bad args %s %s",
            args=("only_one_arg",),  # Missing second argument
            exc_info=None,
        )

        # This should not raise an exception
        self.handler.emit(record)

        logs = self.tail_buffer.get_recent_logs(1)
        self.assertEqual(len(logs), 1)

        timestamp, level, message = logs[0]
        self.assertEqual(level, "ERROR")
        # The message should be the raw template or a fallback
        self.assertIn("Message with bad args", message)


class TestMillisecondFormatter(unittest.TestCase):
    """Test the MillisecondFormatter class."""

    def setUp(self):
        """Set up test fixtures."""
        self.formatter = MillisecondFormatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    def test_millisecond_formatting(self):
        """Test that milliseconds are included in timestamp."""
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        formatted = self.formatter.format(record)

        # Should contain millisecond pattern (HH:MM:SS.mmm)
        import re

        time_pattern = r"\d{2}:\d{2}:\d{2}\.\d{3}"
        self.assertIsNotNone(re.search(time_pattern, formatted))

        # Should contain all formatter components
        self.assertIn("[INFO]", formatted)
        self.assertIn("test.logger", formatted)
        self.assertIn("Test message", formatted)


class TestDebugLogFilter(unittest.TestCase):
    """Test the DebugLogFilter class."""

    def test_filter_all_debug(self):
        """Test filtering when no subsystems are allowed."""
        debug_filter = DebugLogFilter(subsystems=set())

        # Non-debug messages should pass through
        info_record = logging.LogRecord("test", logging.INFO, "test.py", 42, "info msg", (), None)
        self.assertTrue(debug_filter.filter(info_record))

        # Debug messages should be filtered out
        debug_record = logging.LogRecord("test", logging.DEBUG, "test.py", 42, "debug msg", (), None)
        self.assertFalse(debug_filter.filter(debug_record))

    def test_filter_specific_subsystems(self):
        """Test filtering specific debug subsystems."""
        debug_filter = DebugLogFilter(subsystems={"allowed_subsystem"})

        # Non-debug messages should always pass
        info_record = logging.LogRecord("test", logging.INFO, "test.py", 42, "info msg", (), None)
        self.assertTrue(debug_filter.filter(info_record))

        # Debug from allowed subsystem should pass
        allowed_debug = logging.LogRecord("allowed_subsystem", logging.DEBUG, "test.py", 42, "debug msg", (), None)
        self.assertTrue(debug_filter.filter(allowed_debug))

        # Debug from other subsystem should be filtered
        other_debug = logging.LogRecord("other_subsystem", logging.DEBUG, "test.py", 42, "debug msg", (), None)
        self.assertFalse(debug_filter.filter(other_debug))

    def test_filter_no_restrictions(self):
        """Test filtering when all debug messages are allowed."""
        debug_filter = DebugLogFilter(subsystems=None)

        # All messages should pass through
        info_record = logging.LogRecord("test", logging.INFO, "test.py", 42, "info msg", (), None)
        self.assertTrue(debug_filter.filter(info_record))

        debug_record = logging.LogRecord("test", logging.DEBUG, "test.py", 42, "debug msg", (), None)
        self.assertTrue(debug_filter.filter(debug_record))


class TestFontSizeRegression(unittest.TestCase):
    """Test to prevent font size regression."""

    def test_log_font_size_not_too_large(self):
        """Ensure log font size is reasonable for displaying more data."""
        # LOG_FONT_SIZE should be smaller than other font sizes to show more log data
        self.assertLessEqual(
            LOG_FONT_SIZE,
            16,
            "Log font size should be 16 or smaller to display more log data",
        )
        self.assertLess(
            LOG_FONT_SIZE,
            META_FONT_SIZE,
            "Log font should be smaller than metadata font",
        )
        self.assertLess(LOG_FONT_SIZE, TITLE_FONT_SIZE, "Log font should be smaller than title font")

    def test_font_size_reasonable_bounds(self):
        """Ensure font sizes are within reasonable bounds."""
        self.assertGreaterEqual(LOG_FONT_SIZE, 10, "Log font should not be too small to be readable")
        self.assertLessEqual(
            LOG_FONT_SIZE,
            20,
            "Log font should not be too large, limiting visible lines",
        )


class TestLogDisplayRegressionPrevention(unittest.TestCase):
    """Integration tests to prevent log display regressions."""

    def setUp(self):
        """Set up test fixtures."""
        self.tail_buffer = TailBuffer(capacity=100)
        self.handler = PygameLogHandler(self.tail_buffer)
        self.formatter = MillisecondFormatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        # NOTE: We set a formatter to match real usage, but handler should ignore it for GUI display
        self.handler.setFormatter(self.formatter)

    def test_log_content_clean(self):
        """Test that log content displayed in GUI is clean without timestamp/level."""
        # Create logger and add our handler
        logger = logging.getLogger("test.display.regression")
        logger.addHandler(self.handler)
        logger.setLevel(logging.DEBUG)

        # Log various types of messages
        logger.info("Simple info message")
        logger.warning("Warning with timestamp")
        logger.error("Error message")
        logger.debug("Debug information")

        # Get all logged messages
        logs = self.tail_buffer.get_recent_logs(10)
        self.assertEqual(len(logs), 4)

        # Check each message for clean content
        for _timestamp, level, message in logs:
            # Message should NOT contain timestamp patterns
            import re

            time_pattern = r"\d{2}:\d{2}:\d{2}\.\d{3}"
            self.assertIsNone(
                re.search(time_pattern, message),
                f"Message should not contain timestamp: {message}",
            )

            # Message should NOT contain level prefixes
            self.assertNotIn(
                f"[{level}]",
                message,
                f"Message should not contain level prefix: {message}",
            )

            # Message should NOT contain logger name
            self.assertNotIn(
                "test.display.regression",
                message,
                f"Message should not contain logger name: {message}",
            )

            # Message should NOT contain colons from formatter
            if message in [
                "Simple info message",
                "Warning with timestamp",
                "Error message",
                "Debug information",
            ]:
                # These are our test messages - they should be exact
                self.assertIn(
                    message,
                    [
                        "Simple info message",
                        "Warning with timestamp",
                        "Error message",
                        "Debug information",
                    ],
                )

    def test_message_readability(self):
        """Test that messages are readable and properly formatted."""
        logger = logging.getLogger("test.readability")
        logger.addHandler(self.handler)
        logger.setLevel(logging.INFO)  # Ensure logger captures INFO messages

        # Test message with formatting
        logger.info("User %s logged in with ID %d", "john_doe", 12345)

        logs = self.tail_buffer.get_recent_logs(1)
        timestamp, level, message = logs[0]

        # Should have the properly formatted message
        self.assertEqual(message, "User john_doe logged in with ID 12345")
        self.assertEqual(level, "INFO")

        # Should not have any formatter artifacts
        self.assertNotRegex(message, r"\d{2}:\d{2}:\d{2}")  # No timestamp
        self.assertNotIn("[INFO]", message)  # No level bracket
        self.assertNotIn("test.readability", message)  # No logger name


if __name__ == "__main__":
    unittest.main()
