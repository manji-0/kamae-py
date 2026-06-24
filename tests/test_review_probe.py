"""Tests for the Kamae Python review probe."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

PROBE = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "kamae-py-review"
    / "scripts"
    / "review_probe.py"
)
TAXI_REQUEST = (
    Path(__file__).resolve().parents[1] / "skills" / "kamae-py" / "references" / "taxi-request.py"
)


def run_probe(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(PROBE), *args],
        check=False,
        capture_output=True,
        text=True,
    )


def test_probe_finds_leads_on_taxi_request() -> None:
    result = run_probe(str(TAXI_REQUEST), "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert "domain-modeling" in payload["checklists"]
    assert payload["hits"]


def test_probe_requires_python_paths() -> None:
    result = run_probe("README.md")
    assert result.returncode == 1
    assert "no Python files found" in result.stderr
