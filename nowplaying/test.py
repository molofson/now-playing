"""Test script for metadata monitoring."""

# nowplaying/test.py
# Test script for metadata monitoring
#
# Usage:
#   nowplaying-test
#   python -m nowplaying.test

import logging
import os
import sys
import time

from .metadata_monitor import MetadataMonitor
from .playback_state import PlaybackState

logging.basicConfig(
    level=logging.DEBUG,  # Change to INFO if you want less verbose output
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


PIPE_PATH = "/tmp/shairport-sync-metadata"


def print_metadata(metadata):
    """Print metadata information."""
    print("Now Playing:")
    for key, value in metadata.items():
        print(f"  {key}: {value}")


def handle_state(state: PlaybackState):
    """Handle playback state changes."""
    print(f"Playback State Changed: {state}")


if __name__ == "__main__":
    if not os.path.exists(PIPE_PATH):
        print(f"Pipe not found: {PIPE_PATH}")
        print("Is shairport-sync running with metadata enabled?")
        sys.exit(1)

    monitor = MetadataMonitor(
        pipe_path=PIPE_PATH,
        metadata_callback=print_metadata,
        state_callback=handle_state,
    )

    monitor.start()

    try:
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("Stopping...")
        monitor.stop()
