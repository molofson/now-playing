import os
import subprocess
import sys

import pytest


@pytest.mark.parametrize("a,b,result", [(1, 2, 3), (2, 3, 5), (-1, 1, 0)])
def test_addition(a, b, result):
    assert a + b == result


@pytest.fixture
def sample_data():
    return {"name": "Airplay", "active": True}


def test_sample_fixture(sample_data):
    assert sample_data["active"] is True


def test_metadata_display_help():
    """Test that the metadata display shows help without crashing."""
    script_path = os.path.join(os.path.dirname(__file__), "..", "devtools", "metadata_display.py")
    result = subprocess.run(
        [sys.executable, script_path, "--help"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=10,  # Prevent hanging
    )

    # Should exit successfully when showing help
    assert (
        result.returncode == 0
    ), f"Help command failed with code {result.returncode}\nSTDERR:\n{result.stderr.decode()}"

    # Should contain help text
    stdout_text = result.stdout.decode()
    assert "Now Playing Metadata Display" in stdout_text, "Help text not found in output"
    assert "--help" in stdout_text, "Help option not found in output"

    # Should not crash with traceback
    stderr_text = result.stderr.decode()
    assert "Traceback" not in stderr_text, f"App crashed with traceback:\n{stderr_text}"
