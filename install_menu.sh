#!/bin/bash
# install_menu.sh - Install now-playing application to Raspberry Pi menu system

set -e

# Configuration
APP_NAME="now-playing"
APP_DISPLAY_NAME="Now Playing"
APP_DESCRIPTION="AirPlay metadata display for shairport-sync"
APP_ICON="multimedia-audio-player"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/devtools/metadata_display.py"
DESKTOP_FILE_DIR="$HOME/.local/share/applications"
DESKTOP_FILE="$DESKTOP_FILE_DIR/${APP_NAME}.desktop"

# Detect desktop environment
detect_desktop() {
    if pgrep -f "lxpanel\|lxqt" >/dev/null 2>&1; then
        echo "lxde"
    elif pgrep -f "xfce4" >/dev/null 2>&1; then
        echo "xfce"
    elif pgrep -f "gnome" >/dev/null 2>&1; then
        echo "gnome"
    elif pgrep -f "plasma\|kde" >/dev/null 2>&1; then
        echo "kde"
    else
        echo "unknown"
    fi
}

DESKTOP_ENV=$(detect_desktop)

echo "Installing $APP_DISPLAY_NAME to menu system..."
echo "Detected desktop environment: $DESKTOP_ENV"

# Create applications directory if it doesn't exist
mkdir -p "$DESKTOP_FILE_DIR"

# Check if Python script exists
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "Error: Python script not found at $PYTHON_SCRIPT"
    exit 1
fi

# Check if we're in a virtual environment and get the Python path
if [ -n "$VIRTUAL_ENV" ]; then
    PYTHON_EXEC="$VIRTUAL_ENV/bin/python3"
    echo "Using virtual environment Python: $PYTHON_EXEC"
else
    PYTHON_EXEC="python3"
    echo "Using system Python: $PYTHON_EXEC"
fi

# Test if the Python script can be run
echo "Testing Python script execution..."
if ! "$PYTHON_EXEC" "$PYTHON_SCRIPT" --help >/dev/null 2>&1; then
    echo "Warning: Could not execute Python script. Make sure dependencies are installed."
    echo "You may need to run: pip install -r requirements.txt"
fi

# Create the .desktop file
cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=$APP_DISPLAY_NAME
Comment=$APP_DESCRIPTION
Exec=$PYTHON_EXEC $PYTHON_SCRIPT --fullscreen
Icon=$APP_ICON
Terminal=false
Categories=AudioVideo;Audio;Player;
Keywords=audio;airplay;shairport;metadata;display;
StartupNotify=true
EOF

# Make the desktop file executable
chmod +x "$DESKTOP_FILE"

echo "Desktop file created at: $DESKTOP_FILE"
echo ""

# Provide desktop-specific refresh instructions
case $DESKTOP_ENV in
    lxde)
        echo "For LXDE/LXQt, refresh the menu by running:"
        echo "  killall -HUP lxpanel"
        echo "  or log out and log back in"
        ;;
    xfce)
        echo "For XFCE, refresh the menu by running:"
        echo "  xfce4-panel -r"
        echo "  or log out and log back in"
        ;;
    gnome)
        echo "For GNOME, the menu should refresh automatically."
        ;;
    kde)
        echo "For KDE Plasma, the menu should refresh automatically."
        ;;
    *)
        echo "Unknown desktop environment. Try logging out and back in to refresh the menu."
        ;;
esac

echo ""
echo "The application should now appear in your Applications menu under Audio/Video."
echo "You can also run it directly with: $PYTHON_EXEC $PYTHON_SCRIPT --fullscreen"

# Try to update desktop database if available
if command -v update-desktop-database >/dev/null 2>&1; then
    echo "Updating desktop database..."
    update-desktop-database "$DESKTOP_FILE_DIR" 2>/dev/null || true
fi

# Try to refresh LXDE panel if running
if pgrep -f lxpanel >/dev/null 2>&1; then
    echo "Refreshing LXDE panel..."
    killall -HUP lxpanel 2>/dev/null || true
fi

echo "Installation complete!"
