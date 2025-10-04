#!/usr/bin/env python3
"""Command-line interface entry points for now-playing package.."""

import os

# Set pygame environment variables before any imports
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
os.environ["PYGAME_DETECT_AVX2"] = "0"
os.environ["SDL_AUDIODRIVER"] = "pulse"


def display_main():
    """Entry point for nowplaying-display command."""
    from .display import main

    return main()


def mcp_main():
    """Entry point for nowplaying-mcp command."""
    import asyncio

    from .mcp_server import serve_mcp

    return asyncio.run(serve_mcp())


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "mcp":
        mcp_main()
    else:
        display_main()
