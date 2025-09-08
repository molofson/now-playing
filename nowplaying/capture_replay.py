"""
Shairport-sync metadata capture and replay system for debugging.
"""

import gzip
import json
import time
from pathlib import Path
from typing import Callable, Optional, TextIO

from .module_registry import module_registry

# Register the capture/replay module
module_registry.register_module(
    name="capture",
    description="Metadata capture and replay for debugging",
    logger_name="capture",
    debug_flag="--debug-capture",
    enabled=True,
    category="debug",
)

# Get logger for this module
log = module_registry.get_module_info("capture")["logger"]


class MetadataCapture:
    """Captures shairport-sync metadata with timestamps for later replay."""

    def __init__(self, capture_file: str, compress_images: bool = False):
        """Initialize capture to specified file.

        Args:
            capture_file: Path to the capture file
            compress_images: Whether to compress cover art images (always False for simplicity)
        """
        self._capture_file = Path(capture_file)
        self._file_handle: Optional[TextIO] = None
        self._start_time = time.time()
        self._last_activity_time = time.time()
        self._compress_images = compress_images
        self._image_quality = 85  # Default quality, not used when compress_images=False

        # Ensure capture directory exists
        self._capture_file.parent.mkdir(parents=True, exist_ok=True)

        log.info(
            "Metadata capture initialized: %s (compress_images=%s)",
            self._capture_file,
            compress_images,
        )

    def start_capture(self) -> None:
        """Start capturing metadata to file."""
        try:
            self._file_handle = open(self._capture_file, "w", encoding="utf-8")
            self._start_time = time.time()
            self._last_activity_time = self._start_time

            # Write capture header with metadata
            header = {
                "type": "capture_header",
                "version": "1.0",
                "start_time": self._start_time,
                "description": "Shairport-sync metadata capture for debugging",
            }
            self._write_entry(header)

            log.info("Started metadata capture to: %s", self._capture_file)
        except Exception as e:
            log.error("Failed to start capture: %s", e)
            raise

    def capture_line(self, line: str) -> None:
        """Capture a metadata line with timestamp."""
        if not self._file_handle:
            return

        try:
            current_time = time.time()
            elapsed = current_time - self._start_time
            gap_since_last = current_time - self._last_activity_time
            self._last_activity_time = current_time

            # Apply image compression if enabled
            processed_line = self._compress_image_in_line(line)

            entry = {
                "type": "metadata_line",
                "timestamp": elapsed,
                "gap_since_last": gap_since_last,
                "data": processed_line.strip(),
            }

            self._write_entry(entry)

        except Exception as e:
            log.error("Failed to capture line: %s", e)

    def capture_event(self, event_type: str, description: str) -> None:
        """Capture a notable event (state change, error, etc.)."""
        if not self._file_handle:
            return

        try:
            current_time = time.time()
            elapsed = current_time - self._start_time

            entry = {"type": "event", "timestamp": elapsed, "event_type": event_type, "description": description}

            self._write_entry(entry)
            log.debug("Captured event: %s - %s", event_type, description)

        except Exception as e:
            log.error("Failed to capture event: %s", e)

    def _write_entry(self, entry: dict) -> None:
        """Write a JSON entry to the capture file."""
        if self._file_handle:
            json.dump(entry, self._file_handle)
            self._file_handle.write("\n")
            self._file_handle.flush()  # Ensure data is written immediately

    def stop_capture(self) -> None:
        """Stop capturing and close file."""
        if self._file_handle:
            try:
                # Write capture footer
                end_time = time.time()
                footer = {"type": "capture_footer", "end_time": end_time, "total_duration": end_time - self._start_time}
                self._write_entry(footer)

                self._file_handle.close()
                self._file_handle = None
                log.info("Stopped metadata capture. Duration: %.2f seconds", end_time - self._start_time)
            except Exception as e:
                log.error("Error stopping capture: %s", e)

    def _compress_image_in_line(self, line: str) -> str:
        """Process image metadata lines (no compression - always returns original line).

        Args:
            line: Raw metadata line that may contain image data

        Returns:
            Original line unchanged (compression disabled for simplicity)
        """
        # Always return the original line since compression is disabled
        return line


class MetadataReplay:
    """Replays captured metadata with optional fast-forward through idle periods."""

    def __init__(self, capture_file: str, fast_forward_gaps: bool = True, max_gap_seconds: float = 2.0):
        """
        Initialize replay from captured file.

        Args:
            capture_file: Path to captured metadata file (supports .gz compression)
            fast_forward_gaps: Whether to fast-forward through idle periods
            max_gap_seconds: Maximum gap to preserve in real-time (larger gaps are fast-forwarded)
        """
        self._capture_file = Path(capture_file)
        self._fast_forward_gaps = fast_forward_gaps
        self._max_gap_seconds = max_gap_seconds
        self._file_handle: Optional[TextIO] = None

        if not self._capture_file.exists():
            raise FileNotFoundError(f"Capture file not found: {capture_file}")

        log.info("Metadata replay initialized: %s", self._capture_file)

    def _is_gzipped(self) -> bool:
        """Check if the capture file is gzipped."""
        # First check by extension
        if self._capture_file.suffix.lower() == ".gz":
            return True

        # Also check by reading the magic bytes
        try:
            with open(self._capture_file, "rb") as f:
                return f.read(2) == b"\x1f\x8b"
        except Exception:
            return False

    def _open_file(self, mode: str = "r"):
        """Open the capture file, handling both regular and gzipped files."""
        if self._is_gzipped():
            return gzip.open(self._capture_file, mode + "t", encoding="utf-8")
        else:
            return open(self._capture_file, mode, encoding="utf-8")

    def replay(
        self, line_callback: Callable[[str], None], event_callback: Optional[Callable[[str, str, float], None]] = None
    ) -> None:
        """
        Replay captured metadata calling callbacks for each line/event.

        Args:
            line_callback: Function to call for each metadata line
            event_callback: Optional function to call for events (type, description, timestamp)
        """
        try:
            with self._open_file() as f:
                self._replay_from_file(f, line_callback, event_callback)
        except Exception as e:
            log.error("Error during replay: %s", e)
            raise

    def _replay_from_file(
        self,
        file_handle: TextIO,
        line_callback: Callable[[str], None],
        event_callback: Optional[Callable[[str, str, float], None]],
    ) -> None:
        """Internal replay implementation."""
        capture_start_time = None
        last_timestamp = 0.0
        lines_processed = 0
        events_processed = 0
        gaps_fast_forwarded = 0

        log.info("Starting metadata replay...")

        for line in file_handle:
            line = line.strip()
            if not line:
                continue

            try:
                entry = json.loads(line)
            except json.JSONDecodeError as e:
                log.warning("Skipping invalid JSON line: %s", e)
                continue

            entry_type = entry.get("type")
            timestamp = entry.get("timestamp", 0.0)

            if entry_type == "capture_header":
                capture_start_time = entry.get("start_time")
                log.info(
                    "Replay started. Original capture: %s",
                    time.ctime(capture_start_time) if capture_start_time else "unknown",
                )
                continue

            elif entry_type == "capture_footer":
                total_duration = entry.get("total_duration", 0.0)
                log.info("Replay completed. Original duration: %.2f seconds", total_duration)
                log.info(
                    "Replay stats: %d lines, %d events, %d gaps fast-forwarded",
                    lines_processed,
                    events_processed,
                    gaps_fast_forwarded,
                )
                break

            elif entry_type == "metadata_line":
                data = entry.get("data", "")
                gap_since_last = entry.get("gap_since_last", 0.0)

                # Handle timing and fast-forward logic
                time_to_wait = timestamp - last_timestamp

                if self._fast_forward_gaps and gap_since_last > self._max_gap_seconds:
                    # Fast-forward through long gaps
                    time_to_wait = min(time_to_wait, 0.1)  # Wait only 100ms instead
                    gaps_fast_forwarded += 1
                    log.debug("Fast-forwarding %.2fs gap (originally %.2fs)", time_to_wait, gap_since_last)

                if time_to_wait > 0:
                    time.sleep(time_to_wait)

                # Call line callback
                line_callback(data)
                lines_processed += 1

            elif entry_type == "event":
                event_type = entry.get("event_type", "")
                description = entry.get("description", "")

                if event_callback:
                    event_callback(event_type, description, timestamp)
                events_processed += 1

                log.debug("Replayed event at %.2fs: %s - %s", timestamp, event_type, description)

            last_timestamp = timestamp

    def get_capture_info(self) -> dict:
        """Get information about the capture file without replaying it."""
        info: dict = {
            "file_path": str(self._capture_file),
            "file_size": int(self._capture_file.stat().st_size) if self._capture_file.exists() else 0,
            "compressed": self._is_gzipped(),
            "line_count": 0,
            "event_count": 0,
            "duration": 0.0,
            "start_time": None,
            "end_time": None,
        }

        try:
            with self._open_file() as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        entry = json.loads(line)
                        entry_type = entry.get("type")

                        if entry_type == "capture_header":
                            info["start_time"] = entry.get("start_time")
                        elif entry_type == "capture_footer":
                            info["end_time"] = entry.get("end_time")
                            info["duration"] = entry.get("total_duration", 0.0)
                        elif entry_type == "metadata_line":
                            info["line_count"] += 1
                        elif entry_type == "event":
                            info["event_count"] += 1

                    except json.JSONDecodeError:
                        continue

        except Exception as e:
            log.error("Error reading capture info: %s", e)

        return info


def create_capture_filename(prefix: str = "metadata_capture") -> str:
    """Create a timestamped filename for captures."""
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    return f"/tmp/{prefix}_{timestamp}.jsonl"
