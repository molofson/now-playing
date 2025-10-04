#!/usr/bin/env python3
"""Simple test client for the now-playing MCP server."""

import json
import subprocess
import sys

import pytest


@pytest.mark.integration
def test_mcp_server():
    """Test the MCP server with a sample music enrichment request."""
    # Start the MCP server process using python -m to ensure it works in CI
    proc = subprocess.Popen(
        [sys.executable, "-m", "nowplaying.cli", "mcp"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        # Read the initialization message (if any)
        # MCP servers typically send an initialization response
        # But let's send the initialize request first

        # Send initialize request
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"},
            },
        }

        proc.stdin.write(json.dumps(init_request) + "\n")
        proc.stdin.flush()

        # Read response
        response_line = proc.stdout.readline()
        if response_line:
            response = json.loads(response_line)
            print("Initialize response:", json.dumps(response, indent=2))

        # Send initialized notification
        initialized_notification = {"jsonrpc": "2.0", "method": "notifications/initialized"}

        proc.stdin.write(json.dumps(initialized_notification) + "\n")
        proc.stdin.flush()

        # Send tools/list request
        tools_request = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}

        proc.stdin.write(json.dumps(tools_request) + "\n")
        proc.stdin.flush()

        # Read response
        response_line = proc.stdout.readline()
        if response_line:
            response = json.loads(response_line)
            print("Tools list response:", json.dumps(response, indent=2))

        # Send a tool call for enrich_music
        tool_call_request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "enrich_music", "arguments": {"artist": "The Beatles", "album": "Abbey Road"}},
        }

        proc.stdin.write(json.dumps(tool_call_request) + "\n")
        proc.stdin.flush()

        # Read response
        response_line = proc.stdout.readline()
        if response_line:
            response = json.loads(response_line)
            print("Tool call response:", json.dumps(response, indent=2))

    finally:
        proc.terminate()
        proc.wait()


if __name__ == "__main__":
    test_mcp_server()
