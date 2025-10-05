"""Placeholder test for the MCP server; moved into tests/ from top-level.

This provides a trivial assertion so the test file is exercised by CI.
"""


def test_mcp_smoke():
    """Smoke test: simple equality assertion."""
    assert "mcp".upper() == "MCP"
