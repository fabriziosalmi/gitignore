"""Run the conformance suite as a pytest case.

Equivalent to ``python conformance/run_conformance.py`` but integrated
into the standard test pipeline so any drift fails CI.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_conformance_suite_passes() -> None:
    runner = ROOT / "conformance" / "run_conformance.py"
    assert runner.is_file(), f"conformance runner missing at {runner}"
    result = subprocess.run(  # noqa: S603 - fixed argv, no shell
        [sys.executable, str(runner)],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(ROOT),
    )
    assert result.returncode == 0, (
        f"conformance suite failed (exit={result.returncode}):\n"
        f"stderr:\n{result.stderr}\n"
        f"stdout:\n{result.stdout}"
    )
