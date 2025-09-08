# Metadata Capture and Replay for Debugging

The now-playing application includes a comprehensive capture and replay system that allows developers to record real-world shairport-sync metadata streams and replay them later for debugging and testing.

## Overview

This feature is invaluable when bugs occur in production environments or with specific audio sources. Instead of trying to reproduce the exact conditions, developers can capture the metadata stream during the problematic session and replay it later in a controlled environment.

## Key Features

- **Real-time Capture**: Records all metadata lines with precise timestamps
- **Event Tracking**: Captures state changes, errors, and other notable events
- **Fast-Forward Replay**: Automatically speeds through idle periods during replay
- **Lossless Reproduction**: Preserves exact timing and sequence of events
- **Easy Integration**: Simple API for adding capture to any monitoring session

## Capture Functionality

### Programmatic Capture

```python
from nowplaying.metadata_monitor import StateMonitor
from nowplaying.capture_replay import create_capture_filename

# Create monitor with capture enabled
capture_file = create_capture_filename("debug_session")
monitor = StateMonitor(
    pipe_path="/tmp/shairport-sync-metadata",
    capture_file=capture_file
)

# Start monitoring with automatic capture
monitor.start()

# ... let it run during problematic conditions ...

# Stop and save capture
monitor.stop()
print(f"Capture saved to: {capture_file}")
```

### Command-Line Capture

Use the `capture_metadata.py` utility for live capture:

```bash
# Capture for 60 seconds
python devtools/capture_metadata.py --duration 60 --output /tmp/bug_reproduction.jsonl

# Capture with custom pipe path
python devtools/capture_metadata.py --pipe /custom/pipe/path --verbose

# Capture until interrupted (Ctrl+C)
python devtools/capture_metadata.py
```

## Replay Functionality

### Programmatic Replay

```python
from nowplaying.capture_replay import MetadataReplay
from nowplaying.metadata_reader import ShairportSyncPipeReader

# Create metadata processor
def metadata_callback(metadata):
    print(f"Received: {metadata}")

def state_callback(state):
    print(f"State: {state}")

processor = ShairportSyncPipeReader(state_callback, metadata_callback)

# Create replay with fast-forward enabled
replay = MetadataReplay("/tmp/captured_session.jsonl", fast_forward_gaps=True)

# Replay the session
replay.replay(
    line_callback=processor.process_line,
    event_callback=lambda event_type, desc, ts: print(f"Event: {event_type} - {desc}")
)
```

### Command-Line Replay

Use the `replay_capture.py` utility:

```bash
# Basic replay with fast-forward
python devtools/replay_capture.py /tmp/captured_session.jsonl

# Replay preserving original timing
python devtools/replay_capture.py /tmp/captured_session.jsonl --no-fast-forward

# Show capture file information
python devtools/replay_capture.py /tmp/captured_session.jsonl --info-only

# Verbose output showing all processing
python devtools/replay_capture.py /tmp/captured_session.jsonl --verbose
```

## Capture File Format

Capture files use JSON Lines (JSONL) format with the following structure:

### Header
```json
{
  "type": "capture_header",
  "version": "1.0",
  "start_time": 1693123456.789,
  "description": "Shairport-sync metadata capture for debugging"
}
```

### Metadata Lines
```json
{
  "type": "metadata_line",
  "timestamp": 1.234,
  "gap_since_last": 0.156,
  "data": "<item><type>636f7265</type><code>6173616c</code>...</item>"
}
```

### Events
```json
{
  "type": "event",
  "timestamp": 2.567,
  "event_type": "state_change",
  "description": "STOPPED -> PLAYING: session begin"
}
```

### Footer
```json
{
  "type": "capture_footer",
  "end_time": 1693123567.890,
  "total_duration": 111.101
}
```

## Fast-Forward Feature

The replay system can automatically detect idle periods (gaps longer than a configurable threshold) and fast-forward through them while preserving the logical sequence of events.

```python
# Fast-forward gaps longer than 1 second
replay = MetadataReplay(
    capture_file,
    fast_forward_gaps=True,
    max_gap_seconds=1.0
)
```

This is particularly useful when debugging issues that occur during long playback sessions where there may be minutes of idle time between interesting events.

## Common Debugging Workflows

### Reproducing a Bug

1. **Capture the problematic session**:
   ```bash
   python devtools/capture_metadata.py --output bug_reproduction.jsonl
   ```

2. **Reproduce the issue** while capture is running

3. **Stop capture** (Ctrl+C) when issue occurs

4. **Replay for debugging**:
   ```bash
   python devtools/replay_capture.py bug_reproduction.jsonl --verbose
   ```

### Testing State Transitions

1. **Capture a session** with known state changes
2. **Replay multiple times** to verify consistent behavior
3. **Use breakpoints** in replay code for step-by-step debugging

### Performance Analysis

1. **Capture high-frequency metadata** streams
2. **Analyze timing patterns** in capture file
3. **Compare performance** between different implementations

## Integration with Testing

Capture files can be used to create deterministic test cases:

```python
def test_specific_metadata_sequence(self):
    """Test handling of a specific real-world metadata sequence."""
    replay = MetadataReplay("tests/fixtures/problematic_session.jsonl")

    processor = ShairportSyncPipeReader(...)
    results = []

    replay.replay(lambda line: results.append(processor.process_line(line)))

    # Assert expected behavior
    self.assertEqual(len(results), expected_count)
```

## Best Practices

1. **Capture Early**: Start capture before issues occur when possible
2. **Descriptive Filenames**: Use meaningful names like `shuffle_mode_bug_2023.jsonl`
3. **Version Control**: Store important capture files in test fixtures
4. **Privacy**: Be mindful of song titles and metadata in captures
5. **Storage**: Capture files are typically small but can accumulate over time

## Troubleshooting

### Large Capture Files
- Use `--info-only` to check file size and duration before replay
- Consider splitting long captures into smaller segments

### Timing Issues
- Disable fast-forward if precise timing is critical
- Adjust `max_gap_seconds` for different fast-forward behavior

### Missing Events
- Ensure capture started before the problematic sequence
- Check that all state transitions are being captured

This capture and replay system provides a powerful foundation for debugging complex metadata processing issues and ensuring robust handling of real-world shairport-sync streams.
