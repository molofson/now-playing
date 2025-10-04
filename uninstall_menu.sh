#!/bin/bash
# uninstall_menu.sh - Remove now-playing application from Raspberry Pi menu system

set -e

# Configuration
APP_NAME="now-playing"
APP_DISPLAY_NAME="Now Playing"
DESKTOP_FILE_DIR="$HOME/.local/share/applications"
DESKTOP_FILE="$DESKTOP_FILE_DIR/${APP_NAME}.desktop"

echo "Removing $APP_DISPLAY_NAME from menu system..."

# Check if desktop file exists
if [ ! -f "$DESKTOP_FILE" ]; then
    echo "Desktop file not found at: $DESKTOP_FILE"
    echo "Application may not be installed in the menu system."
    exit 0
fi

# Remove the desktop file
rm -f "$DESKTOP_FILE"
echo "Removed desktop file: $DESKTOP_FILE"

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

echo "Uninstallation complete!"
echo "Note: The application files are still installed. Only the menu entry was removed."
