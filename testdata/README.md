# Test Data

This directory contains sample metadata capture files for testing the music discovery application's capture/replay functionality.

## Files

### `sample_test_setlist.json.gz` (3.8MB)
Manually curated test setlist with 4 diverse songs:
1. **"Tek It"** by Cafuné (Alternative) - from "Running"
2. **"Here Comes the Sun"** by The Beatles (Rock) - from "Abbey Road (Remastered)"
3. **"Do You Believe In Love"** by Huey Lewis & The News (Rock) - from "Picture This"
4. **"Nothing Matters"** by The Last Dinner Party (Alternative) - from "Prelude to Ecstasy"

Captured: September 8, 2025
Duration: ~2 minutes
Features: Complete metadata with cover art, good genre variety, gzip compressed

### `sample_skipping_songs.json` (2.0MB)
Original automated capture with 2 songs:
1. **"Busy"** by Oscar Welsh - from "Busy - Single"
2. **"The Most Humblest of All Time, Ever"** by Children of Zeus - from "Balance"

Features: Uncompressed format for easy inspection

## Usage

Test the replay functionality with either file:

```bash
# Test with compressed manual setlist
python music_discovery.py --replay testdata/sample_test_setlist.json.gz --windowed

# Test with uncompressed original sample
python music_discovery.py --replay testdata/sample_skipping_songs.json --windowed
```

Both files support fast-forward replay (gaps > 2 seconds are compressed to 0.1 seconds).

### Compression Support

The replay system automatically detects and supports gzipped (.gz) files:
- Reduces storage space by ~70-90% for large capture files
- No changes needed to commands - works transparently
- Automatic detection by file extension and magic bytes
- Demonstrates both compressed and uncompressed formats
