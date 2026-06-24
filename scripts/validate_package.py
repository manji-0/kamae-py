"""Validate the kamae-py skill package without non-stdlib dependencies."""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = ROOT / "skills"
CLAUDE_PLUGIN_MANIFEST = ROOT / ".claude-plugin" / "plugin.json"
CLAUDE_MARKETPLACE_MANIFEST = ROOT / ".claude-plugin" / "marketplace.json"
CODEX_PLUGIN_MANIFEST = ROOT / ".codex-plugin" / "plugin.json"
CODEX_MARKETPLACE_MANIFEST = ROOT / ".codex-plugin" / "marketplace.json"

FRONTMATTER_RE = re.compile(r"\A---\n(?P<body>.*?)\n---\n", re.DOTALL)
MD_LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
FENCED_CODE_RE = re.compile(r"```.*?```", re.DOTALL)


def as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def parse_frontmatter(path: Path, errors: list[str]) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if match is None:
        fail(errors, f"{rel(path)}: missing YAML frontmatter")
        return {}

    data: dict[str, str] = {}
    current_key: str | None = None
    for raw in match.group("body").splitlines():
        if not raw.strip():
            continue
        if raw.startswith((" ", "\t")):
            if current_key is None:
                fail(errors, f"{rel(path)}: indented frontmatter line without key")
            continue
        if ":" not in raw:
            fail(errors, f"{rel(path)}: invalid frontmatter line: {raw}")
            continue
        key, value = raw.split(":", 1)
        current_key = key.strip()
        data[current_key] = value.strip().strip("\"'")
    return data


def load_json(path: Path, errors: list[str]) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        fail(errors, f"{rel(path)}: missing JSON file")
    except json.JSONDecodeError as exc:
        fail(errors, f"{rel(path)}: invalid JSON at {exc.lineno}:{exc.colno}: {exc.msg}")
    return None


def has_skill_file(path: Path) -> bool:
    if path.is_file():
        return path.name == "SKILL.md"
    return (path / "SKILL.md").is_file()


def check_skill_frontmatter(errors: list[str]) -> None:
    for skill_file in sorted(SKILLS_ROOT.glob("*/SKILL.md")):
        data = parse_frontmatter(skill_file, errors)
        expected_name = skill_file.parent.name
        if data.get("name") != expected_name:
            fail(errors, f"{rel(skill_file)}: frontmatter name must be {expected_name!r}")
        if not data.get("description"):
            fail(errors, f"{rel(skill_file)}: missing description")


def resolve_repo_path(source: Path, raw_target: str) -> Path | None:
    if raw_target.startswith(("http://", "https://", "mailto:", "#")):
        return None
    target = raw_target.split("#", 1)[0]
    if not target:
        return None
    return (source.parent / target).resolve()


def check_markdown_links(errors: list[str]) -> None:
    for path in sorted(ROOT.rglob("*.md")):
        if any(part in {".git", ".venv"} for part in path.parts):
            continue
        text = FENCED_CODE_RE.sub("", path.read_text(encoding="utf-8"))
        for raw_target in MD_LINK_RE.findall(text):
            target = resolve_repo_path(path, raw_target)
            if target is None:
                continue
            try:
                target.relative_to(ROOT)
            except ValueError:
                fail(errors, f"{rel(path)}: relative Markdown target escapes repo: {raw_target}")
                continue
            if not target.exists():
                fail(errors, f"{rel(path)}: missing relative Markdown target: {raw_target}")


def check_plugin_manifest_skills(manifest: Path, errors: list[str]) -> None:
    plugin = load_json(manifest, errors)
    if not isinstance(plugin, dict):
        return
    for entry in as_list(plugin.get("skills")):
        if isinstance(entry, str):
            skill_path = (ROOT / entry).resolve()
            if not has_skill_file(skill_path):
                fail(errors, f"{rel(manifest)}: skill path has no SKILL.md: {entry}")


def check_marketplace_manifest_skills(manifest: Path, errors: list[str]) -> None:
    marketplace = load_json(manifest, errors)
    if not isinstance(marketplace, dict):
        return
    for plugin_entry in as_list(marketplace.get("plugins")):
        if not isinstance(plugin_entry, dict):
            continue
        for entry in as_list(plugin_entry.get("skills")):
            if isinstance(entry, str):
                skill_path = (ROOT / entry).resolve()
                if not has_skill_file(skill_path):
                    fail(errors, f"{rel(manifest)}: skill path has no SKILL.md: {entry}")


def check_manifest_skill_paths(errors: list[str]) -> None:
    check_plugin_manifest_skills(CLAUDE_PLUGIN_MANIFEST, errors)
    check_plugin_manifest_skills(CODEX_PLUGIN_MANIFEST, errors)
    check_marketplace_manifest_skills(CLAUDE_MARKETPLACE_MANIFEST, errors)
    check_marketplace_manifest_skills(CODEX_MARKETPLACE_MANIFEST, errors)


def check_python_syntax(errors: list[str]) -> None:
    for path in sorted(ROOT.rglob("*.py")):
        if any(part in {".git", ".venv"} for part in path.parts):
            continue
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            fail(errors, f"{rel(path)}: Python syntax error: {exc.msg}")


def main() -> int:
    errors: list[str] = []
    check_manifest_skill_paths(errors)
    check_skill_frontmatter(errors)
    check_markdown_links(errors)
    check_python_syntax(errors)

    if errors:
        print("Package validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Package validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
