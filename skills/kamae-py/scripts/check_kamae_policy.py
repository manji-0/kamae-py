"""Check a repository against the Kamae Python stance.

This script inspects project configuration and Python source files for common
Kamae policy violations. It uses only the Python standard library so it can run
in skill-package CI without extra dependencies.

Run from the repository root:

    python path/to/kamae-py/scripts/check_kamae_policy.py

Exit codes:
    0  no errors (warnings may be printed)
    1  one or more policy errors found
"""

from __future__ import annotations

import argparse
import ast
import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path.cwd()

FORBIDDEN_PACKAGE_FILES = {
    "requirements.txt",
    "requirements-dev.txt",
    "poetry.lock",
    "Pipfile",
    "Pipfile.lock",
    "setup.py",
    "setup.cfg",
    "MANIFEST.in",
}

BANNED_TRANSITION_CALLS = {
    "datetime.datetime.now",
    "datetime.datetime.today",
    "datetime.datetime.utcnow",
    "uuid.uuid4",
    "random.random",
    "random.randint",
    "random.choice",
    "random.choices",
    "random.sample",
    "random.shuffle",
    "time.time",
    "time.monotonic",
    "print",
}


@dataclass
class Finding:
    path: Path
    line: int
    message: str
    is_error: bool = True


@dataclass
class PolicyResult:
    errors: list[Finding] = field(default_factory=list)
    warnings: list[Finding] = field(default_factory=list)

    def add(self, path: Path, line: int, message: str, *, error: bool = True) -> None:
        finding = Finding(path=path, line=line, message=message, is_error=error)
        if error:
            self.errors.append(finding)
        else:
            self.warnings.append(finding)

    def has_errors(self) -> bool:
        return bool(self.errors)


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _line(node: ast.AST) -> int:
    return getattr(node, "lineno", 0) or 0


def pyproject_path() -> Path:
    return ROOT / "pyproject.toml"


def load_pyproject(errors: list[Finding]) -> dict[str, Any]:
    path = pyproject_path()
    if not path.is_file():
        errors.append(
            Finding(path, 0, "pyproject.toml not found; Kamae requires uv-managed projects")
        )
        return {}
    try:
        with path.open("rb") as fh:
            return tomllib.load(fh)
    except tomllib.TOMLDecodeError as exc:
        errors.append(Finding(path, getattr(exc, "lineno", 0), f"invalid TOML: {exc}"))
        return {}


def check_project_config(result: PolicyResult, config: dict[str, Any]) -> None:
    if not config:
        return

    project = config.get("project", {})
    requires_python = project.get("requires-python", "")
    if not re.fullmatch(r">=3\.12,<3\.14", requires_python):
        result.add(
            pyproject_path(),
            0,
            f"requires-python should be '>=3.12,<3.14', got {requires_python!r}",
        )

    dependencies = project.get("dependencies", [])
    pydantic_re = re.compile(r"^pydantic(?:\[[^\]]+\])?\s*>=\s*2\s*,\s*<\s*3")
    if not any(pydantic_re.search(dep) for dep in dependencies):
        result.add(
            pyproject_path(),
            0,
            "project.dependencies must include 'pydantic>=2,<3'",
        )

    dev_deps = config.get("dependency-groups", {}).get("dev", [])
    pyrefly_re = re.compile(r"^pyrefly(?:\[[^\]]+\])?\s*>=")
    if not any(pyrefly_re.search(dep) for dep in dev_deps):
        result.add(pyproject_path(), 0, "dependency-groups.dev must include 'pyrefly>=...'")

    pyrefly = config.get("tool", {}).get("pyrefly", {})
    if not pyrefly.get("project-includes"):
        result.add(pyproject_path(), 0, "[tool.pyrefly] project-includes must be set")
    if not pyrefly.get("python-version"):
        result.add(pyproject_path(), 0, "[tool.pyrefly] python-version must be set")

    ruff = config.get("tool", {}).get("ruff", {})
    if ruff.get("target-version") != "py312":
        result.add(pyproject_path(), 0, "[tool.ruff] target-version must be 'py312'")


def check_forbidden_package_files(result: PolicyResult) -> None:
    for name in FORBIDDEN_PACKAGE_FILES:
        path = ROOT / name
        if path.is_file():
            result.add(path, 0, f"Forbidden package-manager file: {name}")


def check_python_version_file(result: PolicyResult) -> None:
    path = ROOT / ".python-version"
    if not path.is_file():
        result.add(path, 0, ".python-version is missing")
        return
    content = path.read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"3\.(12|13)\.\d+", content):
        result.add(
            path, 0, f".python-version should be a 3.12.x or 3.13.x version, got {content!r}"
        )


class ModelConfigCollector(ast.NodeVisitor):
    """First pass: collect which classes have valid frozen+forbid model_config."""

    def __init__(self) -> None:
        self.valid_configs: set[str] = set()
        self.class_bases: dict[str, set[str]] = {}
        self._from_imports: dict[str, str] = {}

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        for alias in node.names:
            local = alias.asname or alias.name
            self._from_imports[local] = f"{module}.{alias.name}"
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        base_names = {self._resolve_name(base) for base in node.bases}
        self.class_bases[node.name] = base_names
        if "pydantic.BaseModel" in base_names:
            if self._has_valid_config(node):
                self.valid_configs.add(node.name)
        self.generic_visit(node)

    def _has_valid_config(self, node: ast.ClassDef) -> bool:
        for item in node.body:
            if not isinstance(item, ast.Assign):
                continue
            for target in item.targets:
                if isinstance(target, ast.Name) and target.id == "model_config":
                    frozen, extra = self._extract_config_dict(item.value)
                    return frozen and extra == "forbid"
        return False

    def _extract_config_dict(self, node: ast.AST) -> tuple[bool, str | None]:
        frozen = False
        extra: str | None = None
        if isinstance(node, ast.Call):
            func = self._resolve_name(node.func)
            if func in ("pydantic.ConfigDict", "ConfigDict"):
                for keyword in node.keywords:
                    if keyword.arg == "frozen":
                        frozen = (
                            isinstance(keyword.value, ast.Constant) and keyword.value.value is True
                        )
                    elif keyword.arg == "extra":
                        if isinstance(keyword.value, ast.Constant) and isinstance(
                            keyword.value.value, str
                        ):
                            extra = keyword.value.value
        return frozen, extra

    def _resolve_name(self, node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return self._from_imports.get(node.id, node.id)
        if isinstance(node, ast.Attribute):
            return f"{self._resolve_name(node.value)}.{node.attr}"
        return ""

    def resolve_valid_bases(self) -> set[str]:
        """Propagate validity through the inheritance graph."""
        valid = set(self.valid_configs)
        changed = True
        while changed:
            changed = False
            for name, bases in self.class_bases.items():
                if name in valid:
                    continue
                if bases & valid or (
                    "pydantic.BaseModel" in bases
                    and any(base in {"DomainModel", "FrozenModel"} for base in bases)
                ):
                    # We only add classes whose immediate bases include a known
                    # valid class. This covers DomainModel-style frozen bases.
                    if any(base in valid for base in bases):
                        valid.add(name)
                        changed = True
        return valid


class SourceVisitor(ast.NodeVisitor):
    def __init__(
        self,
        path: Path,
        result: PolicyResult,
        valid_model_bases: set[str],
    ) -> None:
        self.path = path
        self.result = result
        self._valid_model_bases = valid_model_bases
        self._current_function: ast.FunctionDef | ast.AsyncFunctionDef | None = None
        self._imports: dict[str, str] = {}
        self._from_imports: dict[str, str] = {}

    def _add(self, node: ast.AST, message: str, *, error: bool = True) -> None:
        self.result.add(self.path, _line(node), message, error=error)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            name = alias.asname or alias.name
            self._imports[name] = alias.name
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        for alias in node.names:
            local = alias.asname or alias.name
            self._from_imports[local] = f"{module}.{alias.name}"
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        base_names = {self._resolve_name(base) for base in node.bases}
        if "pydantic.BaseModel" in base_names or bool(base_names & self._valid_model_bases):
            self._check_model_config(node, base_names)
        self.generic_visit(node)

    def _check_model_config(self, node: ast.ClassDef, base_names: set[str]) -> None:
        for item in node.body:
            if not isinstance(item, ast.Assign):
                continue
            for target in item.targets:
                if isinstance(target, ast.Name) and target.id == "model_config":
                    frozen, extra = self._extract_config_dict(item.value)
                    if not frozen:
                        self._add(item, "Domain model should set frozen=True")
                    if extra != "forbid":
                        self._add(item, 'Domain model should set extra="forbid"')
                    return
        # Inheriting a frozen base is acceptable.
        if not (base_names & self._valid_model_bases):
            self._add(node, "Domain model is missing model_config")

    def _extract_config_dict(self, node: ast.AST) -> tuple[bool, str | None]:
        frozen = False
        extra: str | None = None
        if isinstance(node, ast.Call):
            func = self._resolve_name(node.func)
            if func in ("pydantic.ConfigDict", "ConfigDict"):
                for keyword in node.keywords:
                    if keyword.arg == "frozen":
                        frozen = (
                            isinstance(keyword.value, ast.Constant) and keyword.value.value is True
                        )
                    elif keyword.arg == "extra":
                        if isinstance(keyword.value, ast.Constant) and isinstance(
                            keyword.value.value, str
                        ):
                            extra = keyword.value.value
        return frozen, extra

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        outer = self._current_function
        self._current_function = node
        self.generic_visit(node)
        self._current_function = outer

    def visit_Call(self, node: ast.Call) -> None:
        call_name = self._resolve_call(node)
        if self._is_transition_function() and call_name in BANNED_TRANSITION_CALLS:
            self._add(
                node,
                f"Transition function calls {call_name}; inject time/IDs/randomness instead",
            )
        if call_name in ("typing.cast", "cast"):
            self._add(node, "Avoid typing.cast near domain boundaries", error=False)
        self.generic_visit(node)

    def _is_test_file(self) -> bool:
        parts = {p.lower() for p in self.path.parts}
        name = self.path.name.lower()
        return "tests" in parts or name.startswith("test_") or name.endswith("_test.py")

    def visit_Assert(self, node: ast.Assert) -> None:
        if self._is_test_file():
            return
        self._add(node, "Avoid assert for runtime business validation", error=False)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.type is None:
            self._add(node, "Avoid bare except clauses")
        elif isinstance(node.type, ast.Name) and node.type.id in ("Exception", "BaseException"):
            self._add(node, f"Avoid broad except {node.type.id}")
        self.generic_visit(node)

    def visit_Match(self, node: ast.Match) -> None:
        if self._is_transition_function():
            has_assert_never = any(
                isinstance(case.body[-1], ast.Expr)
                and isinstance(case.body[-1].value, ast.Call)
                and self._resolve_call(case.body[-1].value)
                in {"assert_never", "typing.assert_never"}
                for case in node.cases
                if case.pattern is None or isinstance(case.pattern, ast.MatchAs)
            )
            if not has_assert_never:
                self._add(
                    node,
                    "Exhaustive match over domain union should end with assert_never",
                )
        self.generic_visit(node)

    def _is_transition_function(self) -> bool:
        func = self._current_function
        if func is None:
            return False
        # Heuristic: a top-level function whose name looks like a state transition.
        # Event factories (names containing "event") are excluded because they
        # commonly generate IDs at construction time.
        if func.name.startswith("_"):
            return False
        if not func.args.args:
            return False
        first_arg = func.args.args[0].arg
        if first_arg in ("self", "cls"):
            return False
        if "event" in func.name:
            return False
        transition_hints = (
            "transition",
            "assign",
            "cancel",
            "complete",
            "start",
            "approve",
            "reject",
            "activate",
            "deactivate",
        )
        if any(part in func.name for part in transition_hints):
            return True
        return False

    def _resolve_name(self, node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return self._from_imports.get(node.id, node.id)
        if isinstance(node, ast.Attribute):
            return f"{self._resolve_name(node.value)}.{node.attr}"
        return ""

    def _resolve_call(self, node: ast.Call) -> str:
        name = self._resolve_name(node.func)
        if name in self._imports:
            return self._imports[name]
        return name


def _iter_source_paths(include_tests: bool, exclude: list[str]) -> list[Path]:
    paths: list[Path] = []
    exclude_paths = {ROOT / part for part in exclude}
    for pattern in ("src/**/*.py", "tests/**/*.py") if include_tests else ("src/**/*.py",):
        for path in ROOT.glob(pattern):
            if any(path == ep or ep in path.parents for ep in exclude_paths):
                continue
            if any(part in {".git", ".venv", "__pycache__"} for part in path.parts):
                continue
            paths.append(path)
    return sorted(paths)


def _parse_paths(paths: list[Path], result: PolicyResult) -> dict[Path, ast.AST]:
    trees: dict[Path, ast.AST] = {}
    for path in paths:
        try:
            trees[path] = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            result.add(path, exc.lineno or 0, f"Python syntax error: {exc.msg}")
    return trees


def _collect_valid_model_bases(trees: dict[Path, ast.AST]) -> set[str]:
    collector = ModelConfigCollector()
    for tree in trees.values():
        collector.visit(tree)
    return collector.resolve_valid_bases()


def check_source_files(result: PolicyResult, include_tests: bool, exclude: list[str]) -> None:
    paths = _iter_source_paths(include_tests, exclude)
    trees = _parse_paths(paths, result)
    valid_model_bases = _collect_valid_model_bases(trees)

    for path, tree in trees.items():
        visitor = SourceVisitor(path, result, valid_model_bases)
        visitor.visit(tree)

    # Global check: does the codebase define at least one discriminated union?
    has_discriminator = False
    for path in paths:
        text = path.read_text(encoding="utf-8")
        if 'discriminator="kind"' in text or "discriminator='kind'" in text:
            has_discriminator = True
            break
    if not has_discriminator:
        result.add(ROOT, 0, "No discriminated union with 'kind' found", error=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check a repository against the Kamae Python stance."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help="Repository root to check. Defaults to the current working directory.",
    )
    parser.add_argument(
        "--include-tests",
        action="store_true",
        help="Also check files under tests/.",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Path segments to exclude from source checks (may be repeated).",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors.",
    )
    return parser.parse_args()


def print_findings(findings: list[Finding], label: str) -> None:
    if not findings:
        return
    print(f"\n{label}:")
    for finding in findings:
        location = f"{rel(finding.path)}:{finding.line}" if finding.line else rel(finding.path)
        print(f"  {location}: {finding.message}")


def main() -> int:
    args = parse_args()
    global ROOT
    ROOT = args.root.resolve()

    result = PolicyResult()
    pyproject = load_pyproject(result.errors)
    check_project_config(result, pyproject)
    check_forbidden_package_files(result)
    check_python_version_file(result)
    check_source_files(result, args.include_tests, args.exclude)

    print_findings(result.errors, "Errors")
    print_findings(result.warnings, "Warnings")

    if args.strict:
        failures = result.errors + result.warnings
    else:
        failures = result.errors

    if failures:
        print(f"\nKamae policy check failed: {len(failures)} issue(s).")
        return 1

    print("\nKamae policy check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
