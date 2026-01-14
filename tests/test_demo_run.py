import subprocess
import sys


def test_demo_run_exec():
    r = subprocess.run([sys.executable, "-m", "examples.demo_run"], capture_output=True, text=True)
    assert r.returncode == 0
