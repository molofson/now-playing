#!/usr/bin/env python3
"""Command-line utility for replaying captured shairport-sync metadata."""

import argparse
import sys
import time

from nowplaying.capture_replay import MetadataReplay
from nowplaying.metadata_reader import ShairportSyncPipeReader
from nowplaying.playback_state import PlaybackState


def main():
    """Run the metadata replay utility."""
    parser = argparse.ArgumentParser(description="Replay captured shairport-sync metadata for debugging")
    parser.add_argument("capture_file", help="Path to captured metadata file (JSONL format)")
    parser.add_argument(
        "--no-fast-forward",
        action="store_true",
        help="Disable fast-forwarding through idle periods",
    )
    parser.add_argument(
        "--max-gap",
        type=float,
        default=2.0,
        help="Maximum gap in seconds to preserve in real-time (default: 2.0)",
    )
    parser.add_argument(
        "--info-only",
        action="store_true",
        help="Show capture file info without replaying",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")

    args = parser.parse_args()

    # Create replay instance
    try:
        replay = MetadataReplay(
            args.capture_file,
            fast_forward_gaps=not args.no_fast_forward,
            max_gap_seconds=args.max_gap,
        )
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # Show info if requested
    if args.info_only:
        info = replay.get_capture_info()
        print("Capture File Information:")
        print(f"  File: {info['file_path']}")
        print(f"  Size: {info['file_size']:,} bytes")
        print(f"  Lines: {info['line_count']:,}")
        print(f"  Events: {info['event_count']:,}")
        print(f"  Duration: {info['duration']:.2f} seconds")

        if info["start_time"]:
            print(f"  Start Time: {time.ctime(info['start_time'])}")
        if info["end_time"]:
            print(f"  End Time: {time.ctime(info['end_time'])}")

        return 0

    # Set up metadata processing
    metadata_count = 0
    state_changes = 0

    def metadata_callback(metadata: dict) -> None:
        nonlocal metadata_count
        metadata_count += 1
        if args.verbose:
            print(f"Metadata #{metadata_count}: {metadata}")
        else:
            # Show key fields
            fields = []
            for key in ["artist", "album", "title"]:
                if key in metadata:
                    fields.append(f"{key}={metadata[key]}")
            if fields:
                print(f"Metadata: {', '.join(fields)}")

    def state_callback(state: PlaybackState) -> None:
        nonlocal state_changes
        state_changes += 1
        print(f"State Change #{state_changes}: {state.name}")

    # Create metadata reader for processing
    metadata_reader = ShairportSyncPipeReader(state_callback=state_callback, metadata_callback=metadata_callback)

    def line_callback(line: str) -> None:
        """Process each replayed line."""
        if args.verbose:
            print(f"Processing: {line[:100]}{'...' if len(line) > 100 else ''}")
        metadata_reader.process_line(line)

    def event_callback(event_type: str, description: str, timestamp: float) -> None:
        """Process replayed events."""
        print(f"[{timestamp:.2f}s] Event: {event_type} - {description}")

    print(f"Starting replay of: {args.capture_file}")
    print(f"Fast-forward gaps: {'disabled' if args.no_fast_forward else f'enabled (>{args.max_gap}s)'}")
    print("-" * 60)

    try:
        start_time = time.time()
        replay.replay(line_callback, event_callback if args.verbose else None)
        end_time = time.time()

        print("-" * 60)
        print(f"Replay completed in {end_time - start_time:.2f} seconds")
        print(f"Processed {metadata_count} metadata updates and {state_changes} state changes")

    except KeyboardInterrupt:
        print("\nReplay interrupted by user")
        return 1
    except Exception as e:
        print(f"Error during replay: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
