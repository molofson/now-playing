#!/usr/bin/env python3
"""
Command-line utility for capturing shairport-sync metadata to file.
"""

import argparse
import signal
import sys
import time
from pathlib import Path

# Add the nowplaying package to the path
sys.path.insert(0, str(Path(__file__).parent))

from nowplaying.capture_replay import create_capture_filename  # noqa: E402
from nowplaying.metadata_monitor import StateMonitor  # noqa: E402
from nowplaying.playback_state import PlaybackState  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Capture shairport-sync metadata for debugging")
    parser.add_argument(
        "--pipe",
        default="/tmp/shairport-sync-metadata",
        help="Path to shairport-sync metadata pipe (default: /tmp/shairport-sync-metadata)",
    )
    parser.add_argument("--output", help="Output capture file (default: auto-generated with timestamp)")
    parser.add_argument("--duration", type=int, help="Capture duration in seconds (default: unlimited)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")

    args = parser.parse_args()

    # Create output filename if not specified
    output_file = args.output or create_capture_filename()

    print("Starting metadata capture...")
    print(f"  Pipe: {args.pipe}")
    print(f"  Output: {output_file}")
    if args.duration:
        print(f"  Duration: {args.duration} seconds")
    else:
        print("  Duration: unlimited (Ctrl+C to stop)")
    print("-" * 60)

    # Set up callbacks
    def metadata_callback(metadata: dict) -> None:
        if args.verbose:
            print(f"Metadata: {metadata}")
        else:
            # Show key fields
            fields = []
            for key in ["artist", "album", "title"]:
                if key in metadata:
                    fields.append(f"{key}={metadata[key]}")
            if fields:
                print(f"♪ {', '.join(fields)}")

    def state_callback(state: PlaybackState) -> None:
        print(f"🎵 State: {state.name}")

    # Create monitor with capture
    monitor = StateMonitor(
        pipe_path=args.pipe,
        metadata_callback=metadata_callback,
        state_callback=state_callback,
        capture_file=output_file,
    )

    # Set up signal handling for graceful shutdown
    def signal_handler(signum, frame):
        """Handle signals for graceful shutdown."""
        del frame  # Signal API requires this parameter
        print(f"\nReceived signal {signum}, stopping capture...")
        monitor.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Start monitoring
        monitor.start()

        if args.duration:
            # Run for specified duration
            time.sleep(args.duration)
            print(f"\nCapture duration ({args.duration}s) completed, stopping...")
        else:
            # Run until interrupted
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nCapture interrupted by user, stopping...")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    finally:
        monitor.stop()
        print(f"\nCapture saved to: {output_file}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
