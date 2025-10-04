# Music Discovery Application

A swipeable music discovery interface built on the ContentPanel architecture. Explore music content with enriched metadata from external services through an intuitive swipe-based interface.

## Features

- **Swipeable Content Panels**: Navigate between different views using arrow keys
- **Context Hold/Release**: Pin exploration context while music continues playing
- **Comprehensive Music Enrichment**: Enrich metadata with information from 8 external services:
  - **MusicBrainz**: Core music metadata, artist/album/track IDs, cross-service linking
  - **Discogs**: Vinyl/record database, release info, production credits
  - **Last.fm**: Social music data, scrobble counts, popularity scores
  - **Setlist.fm**: Concert setlists, tour dates, live performance data
  - **Songfacts**: Song lyrics, annotations, and background stories
  - **AllMusic**: Professional music reviews and detailed credits
  - **Genius**: Song lyrics and cultural annotations
  - **Pitchfork**: Music criticism and reviews
- **Plugin System**: User-extensible panels and enrichment services
- **Clean Interface**: Minimal system noise with professional display

## Quick Start

### 1. Setup Environment

```bash
# Install dependencies and setup virtual environment
make install-dev
```

#### API Key Configuration

**API keys are now required** for enrichment services. Configure via environment variables:

```bash
export DISCOGS_API_TOKEN="your_discogs_token"
export LASTFM_API_KEY="your_lastfm_key"
export SETLISTFM_API_KEY="your_setlistfm_key"
export GENIUS_API_KEY="your_genius_key"  # Optional
```

Copy `.env.example` to `.env` and fill in your keys. Services without keys will be disabled.

- **Discogs**: https://www.discogs.com/settings/developers
- **Last.fm**: https://www.last.fm/api/account/create
- **Setlist.fm**: https://api.setlist.fm/docs/1.0/index.html
- **Genius**: https://genius.com/developers (optional)

### 2. Run the Application

**Simplest way (recommended):**

```bash
# Clean launcher with no system warnings
./run_discovery.sh
```

**Direct execution:**

```bash
# Windowed mode
python3 music_discovery.py --windowed

# Fullscreen mode
python3 music_discovery.py --fullscreen

# With debug logging
python3 music_discovery.py --windowed --debug

# Completely silent (no system warnings)
python3 music_discovery.py --windowed 2>/dev/null
```

## Controls

| Key       | Action                                         |
| --------- | ---------------------------------------------- |
| **←/→**   | Navigate between content panels                |
| **↑/↓**   | Alternative swipe navigation                   |
| **Space** | Hold/Release context (pin current exploration) |
| **ESC/Q** | Exit application                               |

## Built-in Panels

1. **Now Playing Panel** 🎵 - Current song metadata and playback state
2. **Cover Art Panel** 🖼️ - Large cover art display
3. **VU Meter Panel** 📊 - Audio level visualization
4. **Debug Panel** 🐛 - Debug information display

## Architecture Overview

The application is built on a modular ContentPanel architecture:

- **`music_discovery.py`** - Main application with pygame interface
- **`nowplaying/music_views.py`** - Core ContentPanel interfaces and registry
- **`nowplaying/panels/`** - Content panels package with base classes and built-in implementations
- **`nowplaying/enrichment/`** - Metadata enrichment services package
- **`nowplaying/panel_navigator.py`** - Swipe navigation controller
- **`nowplaying/plugin_system.py`** - User plugin loading system

## Metadata Sources

The application monitors `/tmp/shairport-sync-metadata` for AirPlay metadata. If you don't have `shairport-sync` running, you can still explore the interface with demo data.

## Plugin Development

Create custom panels by extending the ContentPanel class:

```python
from nowplaying.music_views import ContentPanel, PanelInfo, ContentContext

class MyPanel(ContentPanel):
    def __init__(self):
        info = PanelInfo(
            id="my_panel",
            name="My Custom Panel",
            description="My custom content panel",
            icon="🎨",
            category="custom"
        )
        super().__init__(info)

    def render(self, surface, rect):
        # Your rendering code here
        pass
```

## Troubleshooting

### Common Issues

**Virtual keyboard overlay**: If you see a virtual keyboard on top of the application:

- Use the launcher script: `./run_discovery.sh` (includes automatic suppression)
- Manually disable: Check your system's accessibility settings
- GNOME: `gsettings set org.gnome.desktop.a11y.applications screen-keyboard-enabled false`
- KDE: Disable virtual keyboard in System Settings > Input Devices

**No display window**: Ensure you have X11 or Wayland display server running
**Import errors**: Run `make install-dev` to install dependencies
**Permission errors**: Ensure the virtual environment is activated

### Clean Output

If you see system warnings (xkbcommon errors, Wayland warnings), use:

```bash
python3 music_discovery.py --windowed 2>/dev/null
```

Or use the provided launcher script:

```bash
./run_discovery.sh
```

## Development

```bash
# Format code
make format

# Run linting
make lint

# Run tests
make test

# Run all checks
make check
```

## License

MIT License - see LICENSE file for details.
