# Now Playing Display

AirPlay metadata display for shairport-sync with comprehensive music enrichment panels.

## Features

- Real-time AirPlay metadata display
- **Comprehensive Music Enrichment** from 8 external services:
  - **MusicBrainz**: Core music metadata, artist/album/track IDs, cross-service linking
  - **Discogs**: Vinyl/record database, release info, production credits
  - **Last.fm**: Social music data, scrobble counts, popularity scores
  - **Setlist.fm**: Concert setlists, tour dates, live performance data
  - **Songfacts**: Song lyrics, annotations, and background stories
  - **AllMusic**: Professional music reviews and detailed credits
  - **Genius**: Song lyrics and cultural annotations
  - **Pitchfork**: Music criticism and reviews
- Touch-friendly interface with swipe navigation
- Multiple enrichment panels:
  - **Now Playing**: Main metadata display with track info and playback state
  - **Cover Art**: Large album cover display from multiple sources
  - **Artist Info**: Biography, tags, similar artists, tour dates
  - **Album Info**: Reviews, credits, discography, production details
  - **Social Stats**: Scrobble counts, popularity metrics, user tags
  - **Service Status**: Data freshness, enrichment completeness
  - **Audio Levels**: Real-time audio level meters and visualization
- Debug logging with filtering
- Capture/replay functionality for testing

## Installation

### Dependencies

```bash
pip install -r requirements.txt
```

### API Key Configuration

The application uses external music services for metadata enrichment. Some services require API keys, while others work without them:

#### Services Requiring API Keys

```bash
export DISCOGS_API_TOKEN="your_discogs_token"      # Required
export LASTFM_API_KEY="your_lastfm_key"            # Required
export SETLISTFM_API_KEY="your_setlistfm_key"      # Required
export GENIUS_API_KEY="your_genius_key"            # Optional
```

#### Services Available Without Tokens

- **MusicBrainz**: Core music metadata and cross-service linking
- **Songfacts**: Song lyrics and background stories
- **AllMusic**: Professional music reviews and credits
- **Pitchfork**: Music criticism and reviews

#### Getting API Keys

- **Discogs**: https://www.discogs.com/settings/developers
- **Last.fm**: https://www.last.fm/api/account/create
- **Setlist.fm**: https://api.setlist.fm/docs/1.0/index.html
- **Genius**: https://genius.com/developers (optional)

#### Setup Instructions

1. Copy `.env.example` to `.env`
2. Fill in your API keys in the `.env` file
3. Load the environment variables:
   ```bash
   source .env
   # or use a tool like direnv/autoenv
   ```

**Note**: Services without API keys will be automatically disabled. The application will still work with the free services (MusicBrainz, Songfacts, AllMusic, Pitchfork) but with reduced enrichment capabilities.

#### Token Validation

You can validate that your API tokens are properly configured before running the application:

```bash
python3 music_discovery.py --validate-tokens
```

This will load your `.env` file, check that all required tokens are set, report which tokens are present and missing, and test their validity by initializing the enrichment services. Missing required tokens will be reported with signup URLs.

### Menu Integration (Raspberry Pi)

To add the application to your Raspberry Pi's desktop menu:

```bash
./install_menu.sh
```

This will create a desktop entry that appears in your Applications menu under Audio/Video. The app will launch in **fullscreen mode** by default for the best viewing experience.

To remove from the menu:

```bash
./uninstall_menu.sh
```

## Usage

### Quick Start (Recommended)

```bash
# Load API keys and run in kiosk mode
export $(cat .env | grep -v '^#' | xargs)
./run_discovery.sh
```

### Command Line Options

```bash
# Development mode (windowed)
python3 music_discovery.py --windowed

# Fullscreen mode
python3 music_discovery.py --fullscreen

# Kiosk mode (default - fullscreen, no decorations)
python3 music_discovery.py --kiosk

# With debug logging
python3 music_discovery.py --debug

# Validate API tokens before running
python3 music_discovery.py --validate-tokens

# Capture session for testing
python3 music_discovery.py --capture my_session.json

# Replay captured session
python3 music_discovery.py --replay my_session.json.gz
```

### Controls

| Key        | Action                                              |
| ---------- | --------------------------------------------------- |
| **←/→**    | Navigate between content panels                     |
| **Space**  | Hold/Release context (pin current exploration)      |
| **F11**    | Cycle display modes (kiosk → fullscreen → windowed) |
| **D**      | Toggle debug message visibility                     |
| **Q/Esc**  | Exit application                                    |
| **Ctrl+C** | Graceful shutdown                                   |

### Touch Interface

- **Left side**: Swipe left/right to navigate panels, tap to cycle
- **Right side**: Touch & drag to scroll logs, single tap exits scrollback, double tap toggles debug

### Available Panels

1. **Now Playing** 🎵 - Current song metadata and playback state
2. **Cover Art** 🖼️ - Large album cover display from multiple sources
3. **Artist Info** 👤 - Biography, tags, similar artists, tour dates
4. **Album Info** 💿 - Reviews, credits, discography, production details
5. **Social Stats** 📊 - Scrobble counts, popularity metrics, user tags
6. **Service Status** 🔧 - Data freshness, enrichment completeness
7. **VU Meter** 📈 - Real-time audio level meters and visualization
8. **Debug** 🐛 - Debug information display (when --debug enabled)

## Development

### Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_metadata_display.py
```

## Music Discovery (merged notes)

This project contains a Music Discovery application built on the ContentPanel
architecture. The application provides swipeable content panels, context
hold/release, and plugin-capable enrichment services. Developer quick-start and
architecture pointers are below (previously in MUSIC_DISCOVERY.md).

Developer quick start:

```bash
make install-dev
python3 music_discovery.py --windowed
```

Architecture pointers:
- Main app: `music_discovery.py`
- Panels: `nowplaying/panels/`
- Enrichment: `nowplaying/enrichment/`
- Plugin loader: `nowplaying/plugin_system.py`


### Building

```bash
python -m build
```
