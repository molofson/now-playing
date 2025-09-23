#!/bin/bash
#
# Enhanced Music Discovery App Demo Script
# Shows off the new features added in the continuation phase
#

cd "$(dirname "$0")"

echo "🎵 Enhanced Music Discovery App - Demo Mode"
echo "============================================="
echo ""
echo "This demo showcases the new features added to continue the music discovery app:"
echo ""
echo "✨ NEW FEATURES:"
echo "  • Recommendations/Discovery panel with smart suggestions"
echo "  • Demo mode with rotating sample tracks and enrichment data"
echo "  • Enhanced Now Playing panel with modern design"
echo "  • Contextual demo data generation"
echo ""
echo "🎮 CONTROLS:"
echo "  • ← → Arrow keys: Navigate between panels"
echo "  • Space: Hold/Release context for exploration"
echo "  • ESC/Q: Exit application"
echo "  • F11: Toggle display modes"
echo ""
echo "📱 AVAILABLE PANELS:"
echo "  1. Now Playing - Enhanced with modern design and status indicators"
echo "  2. Cover Art - Large album artwork display"
echo "  3. Audio Levels - VU meters for audio visualization"
echo "  4. Discover - NEW: Smart recommendations and similar artists"
echo "  5. Debug - Technical information"
echo "  6. MusicBrainz, Discogs, Last.fm - Enrichment data displays"
echo ""

# Check if pygame is available
if ! python3 -c "import pygame" 2>/dev/null; then
    echo "❌ pygame not available. Installing..."
    sudo apt-get update && sudo apt-get install -y python3-pygame
fi

echo "🚀 Starting enhanced music discovery app in demo mode..."
echo ""
echo "The demo will rotate through different sample tracks every 30 seconds:"
echo "  • Classical: Beethoven - Moonlight Sonata"
echo "  • Rock: Queen - Bohemian Rhapsody"  
echo "  • Jazz: Dave Brubeck - Take Five"
echo "  • Pop: Michael Jackson - Billie Jean"
echo "  • Rock: Eagles - Hotel California"
echo ""
echo "Each track includes contextual recommendations and enrichment data."
echo "Use arrow keys to explore the different panels!"
echo ""

# Run the enhanced app in demo mode
python3 music_discovery.py --demo --windowed