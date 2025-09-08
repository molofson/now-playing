#!/bin/bash
#
# Virtual Keyboard Killer Script
# Run this if the virtual keyboard appears over the music discovery app
#

echo "Attempting to disable virtual keyboard..."

# GNOME
if command -v gsettings >/dev/null 2>&1; then
    echo "Disabling GNOME virtual keyboard..."
    gsettings set org.gnome.desktop.a11y.applications screen-keyboard-enabled false
    gsettings set org.gnome.shell enabled-extensions "[]"
fi

# KDE
if command -v qdbus >/dev/null 2>&1; then
    echo "Disabling KDE virtual keyboard..."
    qdbus org.kde.keyboard /Keyboard org.kde.keyboard.setEnabled false 2>/dev/null || true
fi

# Kill any running virtual keyboards
echo "Terminating virtual keyboard processes..."
pkill -f "onboard" 2>/dev/null || true
pkill -f "florence" 2>/dev/null || true
pkill -f "caribou" 2>/dev/null || true
pkill -f "maliit" 2>/dev/null || true
pkill -f "squeekboard" 2>/dev/null || true

echo "Virtual keyboard suppression complete."
echo "Now run: ./run_discovery.sh"
