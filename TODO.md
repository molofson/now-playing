# TODO: Refactor MetadataCapture to be a context manager
# Instead of keeping file handles open for long durations, implement __enter__ and __exit__
# to make MetadataCapture itself a context manager. This would allow:
#   with MetadataCapture(file) as capture:
#       capture.capture_line(...)
# Currently using long-lived file handles with manual close in stop_capture().

# TODO: Install package in editable mode to eliminate sys.path manipulation
# Currently tests/ and devtools/ manipulate sys.path before importing nowplaying,
# which triggers E402 (module import not at top of file) violations.
#
# Solution: Install package in development mode:
#   pip install -e .
#
# This would make the nowplaying package directly importable without sys.path hacks,
# allowing removal of E402 per-file-ignores from .flake8 configuration.
#
# Files affected:
#   - All test files in tests/
#   - devtools/capture_metadata.py
#   - devtools/metadata_display.py
#   - devtools/replay_capture.py
#   - devtools/touchscreen_demo.py
