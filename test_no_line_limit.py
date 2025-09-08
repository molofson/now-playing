def test_very_long_line():
    """This is a very long line that definitely exceeds 120 characters and should NOT be caught by flake8 now that we have unlimited line length configured again."""
    return True
