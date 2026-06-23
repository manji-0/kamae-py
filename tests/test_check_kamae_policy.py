"""Tests for the Kamae policy checker script."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

CHECKER = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "kamae-py"
    / "scripts"
    / "check_kamae_policy.py"
)

GOOD_PYPROJECT = """\
[project]
name = "good"
version = "0.1.0"
description = "Good"
readme = "README.md"
requires-python = ">=3.13.14,<3.14"
dependencies = [
    "pydantic>=2,<3",
]

[tool.ruff]
target-version = "py313"

[tool.mypy]
python_version = "3.13"
strict = true
plugins = ["pydantic.mypy"]

[tool.pydantic-mypy]
init_forbid_extra = true
init_typed = true
warn_required_dynamic_aliases = true
"""

GOOD_SOURCE = """\
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field


class DomainModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Waiting(DomainModel):
    kind: Literal["waiting"] = "waiting"
    value: int


class Completed(DomainModel):
    kind: Literal["completed"] = "completed"
    value: int


type Request = Annotated[Waiting | Completed, Field(discriminator="kind")]


def complete(waiting: Waiting) -> Completed:
    match waiting:
        case Waiting():
            return Completed(value=waiting.value)
        case _:
            from typing import assert_never
            assert_never(waiting)
"""


def run_checker(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CHECKER), "--root", str(root), *args],
        capture_output=True,
        text=True,
    )


def write_good_project(root: Path) -> None:
    (root / "pyproject.toml").write_text(GOOD_PYPROJECT, encoding="utf-8")
    (root / ".python-version").write_text("3.13.14", encoding="utf-8")
    src = root / "src"
    src.mkdir()
    (src / "domain.py").write_text(GOOD_SOURCE, encoding="utf-8")


def test_good_project_passes(tmp_path: Path) -> None:
    write_good_project(tmp_path)
    result = run_checker(tmp_path)
    assert result.returncode == 0, result.stdout
    assert "Kamae policy check passed" in result.stdout


def test_missing_pydantic_dependency(tmp_path: Path) -> None:
    write_good_project(tmp_path)
    text = (tmp_path / "pyproject.toml").read_text(encoding="utf-8")
    text = text.replace(
        'dependencies = [\n    "pydantic>=2,<3",\n]',
        "dependencies = []",
    )
    (tmp_path / "pyproject.toml").write_text(text, encoding="utf-8")
    result = run_checker(tmp_path)
    assert result.returncode == 1
    assert "project.dependencies must include 'pydantic>=2,<3'" in result.stdout


def test_model_not_frozen(tmp_path: Path) -> None:
    write_good_project(tmp_path)
    source = GOOD_SOURCE.replace('extra="forbid"', 'extra="ignore"')
    (tmp_path / "src" / "domain.py").write_text(source, encoding="utf-8")
    result = run_checker(tmp_path)
    assert result.returncode == 1
    assert 'Domain model should set extra="forbid"' in result.stdout


def test_transition_calls_now(tmp_path: Path) -> None:
    write_good_project(tmp_path)
    source = GOOD_SOURCE.replace(
        "def complete(waiting: Waiting) -> Completed:",
        "def complete(waiting: Waiting) -> Completed:\n    from datetime import datetime",
    ).replace(
        "return Completed(value=waiting.value)",
        "return Completed(value=waiting.value, completed_at=datetime.now())",
    )
    (tmp_path / "src" / "domain.py").write_text(source, encoding="utf-8")
    result = run_checker(tmp_path)
    assert result.returncode == 1
    assert "Transition function calls datetime.datetime.now" in result.stdout


def test_broad_except(tmp_path: Path) -> None:
    write_good_project(tmp_path)
    replacement = (
        "            try:\n"
        "                return Completed(value=waiting.value)\n"
        "            except Exception:\n"
        "                raise"
    )
    source = GOOD_SOURCE.replace(
        "            return Completed(value=waiting.value)",
        replacement,
    )
    (tmp_path / "src" / "domain.py").write_text(source, encoding="utf-8")
    result = run_checker(tmp_path)
    assert result.returncode == 1
    assert "Avoid broad except Exception" in result.stdout


def test_strict_treats_warnings_as_errors(tmp_path: Path) -> None:
    write_good_project(tmp_path)
    extra = """\


def parse(x: object) -> Waiting:
    from typing import cast
    return cast(Waiting, x)
"""
    source = GOOD_SOURCE + extra
    (tmp_path / "src" / "domain.py").write_text(source, encoding="utf-8")
    result = run_checker(tmp_path, "--strict")
    assert result.returncode == 1
    assert "Avoid typing.cast near domain boundaries" in result.stdout


def test_missing_python_version_file(tmp_path: Path) -> None:
    write_good_project(tmp_path)
    (tmp_path / ".python-version").unlink()
    result = run_checker(tmp_path)
    assert result.returncode == 1
    assert ".python-version is missing" in result.stdout


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
