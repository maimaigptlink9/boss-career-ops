import os
import subprocess
import sys


def _run_subprocess(env):
    result = subprocess.run(
        [sys.executable, "-c", (
            "import logging; "
            "logging.basicConfig(level=logging.DEBUG, format='%(levelname)s %(name)s %(message)s'); "
            "from boss_career_ops.cli.main import cli; "
        )],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        cwd=os.path.dirname(os.path.dirname(__file__)),
    )
    return result


def test_debug_log_when_pythonioencoding_not_set():
    env = os.environ.copy()
    env.pop("PYTHONIOENCODING", None)
    result = _run_subprocess(env)
    combined = (result.stdout or "") + (result.stderr or "")
    assert "PYTHONIOENCODING" in combined


def test_no_warning_when_pythonioencoding_set():
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    result = _run_subprocess(env)
    combined = (result.stdout or "") + (result.stderr or "")
    assert "PYTHONIOENCODING" not in combined
