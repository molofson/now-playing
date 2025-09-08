#!/usr/bin/env python3
"""
Command-line interface entry points for now-playing package.
"""

import os

# Set pygame environment variables before any imports
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
os.environ["PYGAME_DETECT_AVX2"] = "0"
os.environ["SDL_AUDIODRIVER"] = "pulse"


def display_main():
    """Entry point for nowplaying-display command."""
    from .display import main

    return main()


def test_main():
    """Entry point for nowplaying-test command."""
    from .test import main

    return main()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_main()
    else:
        display_main()
