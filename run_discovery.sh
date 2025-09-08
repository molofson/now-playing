#!/bin/bash
#
# Music Discovery Application Launcher
# Runs the music discovery app with clean output (no system warnings)
#

cd "$(dirname "$0")"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Virtual environment not found. Please run: make install-dev"
    exit 1
fi

# Activate virtual environment
source .venv/bin/activate

# Run with clean output
echo "Starting Music Discovery Application..."
echo "Use arrow keys to navigate, spacebar to hold/release context, ESC/Q to quit"
echo ""

python3 music_discovery.py --windowed 2>/dev/null
