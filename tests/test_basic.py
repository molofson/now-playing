import subprocess
import os
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


def test_app_runs_without_crashing():
    """Run the app and ensure it exits without crashing."""
    script_path = os.path.join(os.path.dirname(__file__), "..", "nowplaying.py")
    result = subprocess.run(
        [sys.executable, script_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )

    # Accept 0 (success) or 1 (controlled exit)
    assert result.returncode in (
        0,
        1,
    ), f"Exited with unexpected code {result.returncode}\nSTDERR:\n{result.stderr.decode()}"

    # Fail if a traceback is found in stderr
    assert b"Traceback" not in result.stderr, "App crashed:\n" + result.stderr.decode()
