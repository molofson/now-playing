#!/bin/bash
#
# Music Discovery Application Launcher
# Runs the music discovery app with clean output and virtual keyboard suppression
#

cd "$(dirname "$0")"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Virtual environment not found. Please run: make install-dev"
    exit 1
fi

# Activate virtual environment
source .venv/bin/activate

# Disable virtual keyboard for various desktop environments
export QT_IM_MODULE=none
export GTK_IM_MODULE=none
export XMODIFIERS=""
export SDL_DISABLE_TOUCH=1
export SDL_TEXTINPUT=0

# Kiosk mode settings
export SDL_VIDEO_WINDOW_POS=0,0
export SDL_VIDEO_CENTERED=0

# Try to disable window manager panels/taskbars temporarily
if command -v gsettings >/dev/null 2>&1; then
    # GNOME: Try to hide top bar and dash
    gsettings set org.gnome.shell.extensions.dash-to-dock autohide true 2>/dev/null || true
    gsettings set org.gnome.desktop.interface enable-hot-corners false 2>/dev/null || true
fi

if command -v xfconf-query >/dev/null 2>&1; then
    # XFCE: Try to hide panels
    xfconf-query -c xfce4-panel -p /panels/panel-1/autohide -s true 2>/dev/null || true
fi

# Try to disable virtual keyboard if running on specific systems
if command -v gsettings >/dev/null 2>&1; then
    gsettings set org.gnome.desktop.a11y.applications screen-keyboard-enabled false 2>/dev/null || true
fi

if command -v qdbus >/dev/null 2>&1; then
    qdbus org.kde.keyboard /Keyboard org.kde.keyboard.setEnabled false 2>/dev/null || true
fi

# Run with clean output (kiosk mode is default)
echo "Starting Music Discovery Application in Kiosk Mode..."
echo "Use arrow keys to navigate, spacebar to hold/release context, ESC/Q to quit"
echo "Press F11 to cycle through display modes (kiosk -> fullscreen -> windowed)"
echo ""

python3 music_discovery.py 2>/dev/null
