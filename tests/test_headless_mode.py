"""
Tests for the CLI mode and display functionality improvements.

These tests verify the CLI mode implementation and the
removal of forced exit workarounds.
"""

import os
import signal
import subprocess
import sys
import time

import pytest


class TestCLIMode:
    """Test the CLI mode functionality."""

    def get_metadata_display_path(self):
        """Get the path to the metadata display script."""
        return os.path.join(os.path.dirname(__file__), "..", "devtools", "metadata_display.py")

    def test_cli_mode_help(self):
        """Test that CLI mode shows up in help."""
        result = subprocess.run(
            [sys.executable, self.get_metadata_display_path(), "--help"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
        )

        assert result.returncode == 0
        stdout_text = result.stdout.decode()
        assert "--cli" in stdout_text
        assert "CLI mode" in stdout_text

    def test_cli_mode_starts_without_pygame(self):
        """Test that CLI mode starts without pygame initialization."""
        # Use timeout to prevent hanging
        process = subprocess.Popen(
            [sys.executable, self.get_metadata_display_path(), "--cli"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            # Let it run for a short time
            time.sleep(2)

            # Should still be running (not crashed)
            assert process.poll() is None, "CLI mode crashed unexpectedly"

            # Send SIGTERM to test graceful shutdown
            process.terminate()

            # Should exit within reasonable time
            try:
                stdout, stderr = process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
                pytest.fail("CLI mode did not shut down gracefully within 5 seconds")

            # Should contain CLI mode logs
            log_output = stdout + stderr
            assert "cli mode" in log_output.lower(), "No CLI mode indication in output"

        finally:
            if process.poll() is None:
                process.kill()

    def test_cli_mode_signal_handling(self):
        """Test that CLI mode handles signals correctly."""
        process = subprocess.Popen(
            [sys.executable, self.get_metadata_display_path(), "--cli"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            # Let it start up
            time.sleep(1)

            # Send SIGINT (Ctrl+C)
            start_time = time.time()
            process.send_signal(signal.SIGINT)

            # Should exit gracefully
            try:
                stdout, stderr = process.communicate(timeout=3)
                end_time = time.time()

                # Should exit quickly (< 1 second)
                shutdown_time = end_time - start_time
                assert shutdown_time < 1.0, f"Shutdown took too long: {shutdown_time} seconds"

                # Should exit with code 0 (graceful shutdown)
                assert process.returncode == 0, f"Exit code was {process.returncode}, expected 0"

            except subprocess.TimeoutExpired:
                process.kill()
                pytest.fail("CLI mode did not respond to SIGINT within 3 seconds")

        finally:
            if process.poll() is None:
                process.kill()

    def test_cli_mode_without_pipe(self):
        """Test CLI mode behavior when pipe doesn't exist."""
        # Add --pipe argument with non-existent path
        process = subprocess.Popen(
            [
                sys.executable,
                self.get_metadata_display_path(),
                "--cli",
                "--pipe",
                "/nonexistent/pipe",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            # Let it run briefly
            time.sleep(2)

            # Should still be running (not crash on missing pipe)
            assert process.poll() is None, "Should not crash when pipe doesn't exist"

            process.terminate()
            stdout, stderr = process.communicate(timeout=3)

            # Should contain appropriate error message
            assert "pipe" in stderr.lower() or "error" in stderr.lower()

        except subprocess.TimeoutExpired:
            process.kill()
            pytest.fail("Process did not terminate gracefully")
        finally:
            if process.poll() is None:
                process.kill()


class TestDisplayModeArguments:
    """Test the display mode argument parsing."""

    def get_metadata_display_path(self):
        """Get the path to the metadata display script."""
        return os.path.join(os.path.dirname(__file__), "..", "devtools", "metadata_display.py")

    def test_conflicting_display_modes(self):
        """Test that conflicting display modes are rejected."""
        # Test that the app rejects conflicting display modes with proper error
        result = subprocess.run(
            [sys.executable, self.get_metadata_display_path(), "--cli", "--fullscreen"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5,
        )

        # Should exit with error code
        assert result.returncode == 1, f"Expected exit code 1, got {result.returncode}"

        # Should contain error message about conflicting modes
        output = result.stdout + result.stderr
        assert "multiple display modes" in output.lower(), "Should show error about conflicting modes"

    def test_kiosk_mode_argument(self):
        """Test that kiosk mode is mentioned in help (as explicit option)."""
        result = subprocess.run(
            [sys.executable, self.get_metadata_display_path(), "--help"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
        )

        stdout_text = result.stdout.decode()
        assert "--kiosk" in stdout_text
        assert "kiosk mode" in stdout_text.lower()
        # Help is now the default, not kiosk
        assert "default: show this help" in stdout_text.lower()

    def test_fullscreen_mode_argument(self):
        """Test that fullscreen mode argument is recognized."""
        result = subprocess.run(
            [sys.executable, self.get_metadata_display_path(), "--help"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
        )

        stdout_text = result.stdout.decode()
        assert "--fullscreen" in stdout_text
        assert "fullscreen" in stdout_text.lower()


class TestUnifiedCleanup:
    """Test the unified cleanup functionality across display modes."""

    def test_no_forced_exit_mechanisms(self):
        """Test that forced exit mechanisms have been removed."""
        # Read the metadata_display.py file to verify no forced exits
        display_path = os.path.join(os.path.dirname(__file__), "..", "devtools", "metadata_display.py")

        with open(display_path, "r") as f:
            content = f.read()

        # Should not contain forced exit patterns that we removed
        assert "_force_exit" not in content, "Forced exit mechanism still present"
        assert "os._exit" not in content, "os._exit() still present"

        # sys.exit in main() is fine - we just removed the forced exits


class TestLogStreaming:
    """Test the log streaming functionality in CLI mode."""

    def test_log_output_in_cli_mode(self):
        """Test that logs are streamed to console in CLI mode."""
        process = subprocess.Popen(
            [
                sys.executable,
                os.path.join(os.path.dirname(__file__), "..", "devtools", "metadata_display.py"),
                "--cli",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            # Let it run briefly to generate some log output
            time.sleep(2)

            process.terminate()
            stdout, stderr = process.communicate(timeout=3)

            # Should have some log output (either in stdout or stderr)
            log_output = stdout + stderr
            assert len(log_output) > 0, "No log output captured"

            # Should contain log-like content
            has_log_content = any(
                [
                    "INFO" in log_output,
                    "DEBUG" in log_output,
                    "Metadata" in log_output,
                    "State" in log_output,
                    "cli mode" in log_output.lower(),
                ]
            )
            assert has_log_content, f"No recognizable log content in: {log_output}"

        except subprocess.TimeoutExpired:
            process.kill()
            pytest.fail("Process did not terminate within timeout")
        finally:
            if process.poll() is None:
                process.kill()


class TestPerformanceImprovements:
    """Test the performance improvements in shutdown times."""

    def test_quick_shutdown_cli(self):
        """Test that CLI mode shuts down quickly."""
        process = subprocess.Popen(
            [
                sys.executable,
                os.path.join(os.path.dirname(__file__), "..", "devtools", "metadata_display.py"),
                "--cli",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            # Let it start up
            time.sleep(1)

            # Measure shutdown time
            start_time = time.time()
            process.terminate()

            try:
                process.communicate(timeout=2)  # Should shutdown within 2 seconds
                end_time = time.time()

                shutdown_time = end_time - start_time
                # Should be much faster than the old 10+ second hangs
                assert shutdown_time < 1.0, f"Shutdown took {shutdown_time} seconds, expected < 1.0"

            except subprocess.TimeoutExpired:
                process.kill()
                pytest.fail("Shutdown took longer than 2 seconds")

        finally:
            if process.poll() is None:
                process.kill()

    def test_no_hanging_on_missing_dependencies(self):
        """Test that app doesn't hang when dependencies are missing."""
        # This would test scenarios where pygame or other deps might be missing
        # For now, just ensure the help works without hanging
        result = subprocess.run(
            [
                sys.executable,
                os.path.join(os.path.dirname(__file__), "..", "devtools", "metadata_display.py"),
                "--help",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5,  # Should be very fast
        )

        assert result.returncode == 0
        assert "Now Playing" in result.stdout.decode()

    def test_default_shows_help(self):
        """Test that running without arguments shows help by default."""
        result = subprocess.run(
            [
                sys.executable,
                os.path.join(os.path.dirname(__file__), "..", "devtools", "metadata_display.py"),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5,
        )

        assert result.returncode == 0
        stdout_text = result.stdout.decode()
        assert "Now Playing Metadata Display" in stdout_text
        assert "Usage:" in stdout_text
        assert "default: show this help" in stdout_text

    def test_meaningful_args_dont_show_help(self):
        """Test that meaningful arguments don't trigger help display."""
        # Test with debug flag - should run CLI mode, not show help
        process = subprocess.Popen(
            [
                sys.executable,
                os.path.join(os.path.dirname(__file__), "..", "devtools", "metadata_display.py"),
                "--debug-metadata",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            # Let it start and check that it's running (not just showing help and exiting)
            time.sleep(1)

            # Should still be running (not just shown help and exited)
            assert process.poll() is None, "Should be running CLI mode, not just showing help"

            process.terminate()
            stdout, stderr = process.communicate(timeout=3)

            # Should contain CLI mode output, not help text
            output = stdout + stderr
            assert "Running in CLI mode" in output or "cli mode" in output.lower()
            assert "Usage:" not in output  # Should not contain help text

        except subprocess.TimeoutExpired:
            process.kill()
            pytest.fail("Process did not terminate within timeout")
        finally:
            if process.poll() is None:
                process.kill()


if __name__ == "__main__":
    pytest.main([__file__])
