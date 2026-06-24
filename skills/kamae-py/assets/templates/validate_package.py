"""Validate an Agent Skill package without non-stdlib dependencies."""

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
AGENTS_MARKETPLACE_MANIFEST = ROOT / ".agents" / "plugins" / "marketplace.json"

JSON_MANIFESTS = [
    CLAUDE_PLUGIN_MANIFEST,
    CLAUDE_MARKETPLACE_MANIFEST,
    CODEX_PLUGIN_MANIFEST,
    CODEX_MARKETPLACE_MANIFEST,
    AGENTS_MARKETPLACE_MANIFEST,
]

FRONTMATTER_RE = re.compile(r"\A---\n(?P<body>.*?)\n---\n", re.DOTALL)
MD_LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
FENCED_CODE_RE = re.compile(r"```.*?```", re.DOTALL)
REFERENCE_GUIDE_RE = re.compile(r"references/[A-Za-z0-9_-]+\.md")

RULES_DEFAULTS = ROOT / "rules" / "defaults"
SKILL_ROOT = SKILLS_ROOT / "kamae-py"
RULE_REQUIRED_FIELDS = ("name", "description", "applies-to", "type", "alwaysApply")
RULE_APPLIES_TO = {"kamae-py", "kamae-py-review", "*"}
RULE_TYPES = {"library-preference", "check-toggle", "convention", "override"}


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


def check_json_manifests(errors: list[str]) -> None:
    for manifest in JSON_MANIFESTS:
        load_json(manifest, errors)


def check_codex_interface(errors: list[str]) -> None:
    plugin = load_json(CODEX_PLUGIN_MANIFEST, errors)
    if not isinstance(plugin, dict):
        return
    interface = plugin.get("interface")
    if not isinstance(interface, dict):
        fail(errors, f"{rel(CODEX_PLUGIN_MANIFEST)}: missing top-level interface object")
        return
    for key in [
        "displayName",
        "shortDescription",
        "longDescription",
        "developerName",
        "category",
        "capabilities",
        "defaultPrompt",
    ]:
        if not interface.get(key):
            fail(errors, f"{rel(CODEX_PLUGIN_MANIFEST)}: missing interface.{key}")


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


def check_rule_frontmatter(errors: list[str]) -> None:
    if not RULES_DEFAULTS.is_dir():
        fail(errors, f"{rel(RULES_DEFAULTS)}: missing rules defaults directory")
        return

    for path in sorted(RULES_DEFAULTS.glob("*.md")):
        data = parse_frontmatter(path, errors)
        for key in RULE_REQUIRED_FIELDS:
            if not data.get(key):
                fail(errors, f"{rel(path)}: missing required rule frontmatter field {key}")
        applies_to = data.get("applies-to", "")
        if applies_to and applies_to not in RULE_APPLIES_TO:
            fail(errors, f"{rel(path)}: invalid applies-to {applies_to!r}")
        rule_type = data.get("type", "")
        if rule_type and rule_type not in RULE_TYPES:
            fail(errors, f"{rel(path)}: invalid type {rule_type!r}")


def check_dependency_detection_references(errors: list[str]) -> None:
    sources = [
        RULES_DEFAULTS / "dependency-detection.md",
        SKILL_ROOT / "SKILL.md",
    ]
    for path in sources:
        if not path.is_file():
            fail(errors, f"{rel(path)}: missing dependency detection source")
            continue
        text = path.read_text(encoding="utf-8")
        for guide in sorted(set(REFERENCE_GUIDE_RE.findall(text))):
            guide_path = SKILL_ROOT / guide
            if not guide_path.is_file():
                fail(errors, f"{rel(path)}: referenced guide does not exist: {guide}")


def main() -> int:
    errors: list[str] = []
    check_json_manifests(errors)
    if not errors:
        check_codex_interface(errors)
        check_manifest_skill_paths(errors)
    check_skill_frontmatter(errors)
    check_rule_frontmatter(errors)
    check_markdown_links(errors)
    check_dependency_detection_references(errors)
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
