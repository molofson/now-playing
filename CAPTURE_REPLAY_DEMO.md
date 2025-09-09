# Music Discovery App - Capture and Replay Demo

This demonstrates the new capture and replay functionality added to the music discovery app for testing and development.

## Features Added

### 1. Metadata Capture
- **Purpose**: Record live metadata sessions for later replay
- **Usage**: `python music_discovery.py --capture filename.json`
- **Benefits**:
  - Test with real metadata without needing live music
  - Create reproducible test scenarios
  - Debug specific song transitions

### 2. Metadata Replay with Fast-Forward
- **Purpose**: Replay captured sessions with accelerated playback
- **Usage**: `python music_discovery.py --replay filename.json`
- **Benefits**:
  - Skip through long periods of silence
  - Test multiple song transitions quickly
  - Validate UI behavior with different metadata

## Example Usage

### Capture a Session
```bash
# Start capturing while music is playing
python music_discovery.py --capture sample_skipping_songs.json --windowed

# Let it run while skipping through several songs, then stop with Ctrl+C
```

### Replay the Session
```bash
# Replay with fast-forward through gaps
python music_discovery.py --replay sample_skipping_songs.json --windowed

# The app will quickly skip through idle periods and show song transitions
```

## Sample File Included

- `sample_skipping_songs.json` - Contains a captured session with:
  - "Busy" by Oscar Welsh (Indie Pop)
  - "The Most Humblest of All Time, Ever" by Children of Zeus (Contemporary R&B)
  - Cover art for both songs
  - State transitions (no_session → playing → stopped → waiting)

## Technical Details

- **Fast-forward**: Gaps longer than 2 seconds are compressed to 0.1 seconds
- **Cover art**: Previously downloaded cover art is reused from cache
- **Metadata preservation**: Full metadata including sequence numbers and IDs
- **State tracking**: Playback states are captured and replayed

## Integration

The capture/replay system integrates seamlessly with:
- ✅ Content panels and navigation
- ✅ Cover art display (using cached images)
- ✅ Metadata enrichment services
- ✅ State management and transitions
- ✅ UUID-based metadata tracking with sequence numbers

This enables comprehensive testing of the music discovery interface without requiring live music streaming.
