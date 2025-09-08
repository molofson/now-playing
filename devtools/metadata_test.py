# devtools/metadata_test.py
# Test script for metadata monitoring
#
# Usage (run from project root):
#   python3 devtools/metadata_test.py

import logging
import os
import sys
import time

from nowplaying.metadata_monitor import MetadataMonitor

logging.basicConfig(
    level=logging.DEBUG,  # Change to INFO if you want less verbose output
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


PIPE_PATH = "/tmp/shairport-sync-metadata"


def print_metadata(metadata):
    print("Now Playing:")
    for key, value in metadata.items():
        print(f"  {key}: {value}")


def handle_state(state):
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
