"""Scan Python files for patterns that route Kamae Python review checklists.

This script produces review leads, not findings. Run from the repository root:

    python skills/kamae-py-review/scripts/review_probe.py path/to/changed.py
    python skills/kamae-py-review/scripts/review_probe.py src/ --json

Exit code is always 0 unless a path is missing or unreadable.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

CHECKLISTS = (
    "domain-modeling",
    "state-transitions",
    "error-handling",
    "boundary",
    "pii-protection",
    "logging-metrics",
    "unsafe-boundaries",
    "quality-gates",
    "api-contracts",
    "ci-setup",
    "development-setup",
    "persistence-events",
    "aggregates",
    "application-wiring",
    "concurrency",
    "infrastructure-resilience",
    "orm-adapters",
    "pydantic-performance",
    "migration-strategy",
    "tests",
)

PATTERN_RULES: list[tuple[str, re.Pattern[str], tuple[str, ...]]] = [
    (
        "native-boundary",
        re.compile(r"\b(ctypes|cffi|model_construct|typing\.cast|# type:\s*ignore)\b"),
        ("unsafe-boundaries", "boundary", "pydantic-performance"),
    ),
    (
        "implicit-time-random",
        re.compile(
            r"\b(datetime\.(now|utcnow|today)|uuid\.uuid4|random\.|time\.(time|monotonic))\b"
        ),
        ("state-transitions",),
    ),
    (
        "pii-terms",
        re.compile(
            r"\b(email|phone|password|secret|token|ssn|passport|address|SecretStr)\b",
            re.IGNORECASE,
        ),
        ("pii-protection", "logging-metrics"),
    ),
    (
        "persistence-events",
        re.compile(r"\b(outbox|repository|transaction|idempoten|optimistic|event_version)\b", re.I),
        ("persistence-events", "aggregates", "tests"),
    ),
    (
        "orm-imports",
        re.compile(r"\b(sqlalchemy|django\.db|Session|AsyncSession)\b"),
        ("orm-adapters", "boundary", "persistence-events"),
    ),
    (
        "async-risk",
        re.compile(r"\b(async def|await |asyncio\.|to_thread)\b"),
        ("concurrency", "error-handling", "application-wiring"),
    ),
    (
        "resilience",
        re.compile(r"\b(tenacity|retry|CircuitBreaker|backoff)\b", re.I),
        ("infrastructure-resilience", "persistence-events"),
    ),
    (
        "quality-suppressions",
        re.compile(r"(#\s*noqa\b|#\s*type:\s*ignore\b)"),
        ("quality-gates",),
    ),
    (
        "pydantic-domain",
        re.compile(
            r"\b(BaseModel|TypeAdapter|Field\(discriminator|Literal\[|model_validator|field_validator)\b"
        ),
        ("domain-modeling", "boundary"),
    ),
    (
        "observability",
        re.compile(r"\b(logger\.|logging\.|opentelemetry|metrics\.|trace\.|span\.)\b"),
        ("logging-metrics", "pii-protection"),
    ),
    (
        "property-tests",
        re.compile(r"\b(hypothesis|given\(|@settings)\b"),
        ("tests",),
    ),
    (
        "doc-contract-gap",
        re.compile(r"^def [a-z_].*\):\n(?!\s+\"\"\")", re.MULTILINE),
        ("api-contracts",),
    ),
]


@dataclass
class ProbeHit:
    path: str
    line: int
    rule: str
    snippet: str
    checklists: list[str] = field(default_factory=list)


@dataclass
class ProbeResult:
    hits: list[ProbeHit] = field(default_factory=list)
    checklists: set[str] = field(default_factory=set)

    def add(
        self,
        path: Path,
        line: int,
        rule: str,
        snippet: str,
        checklists: tuple[str, ...],
    ) -> None:
        self.hits.append(
            ProbeHit(
                path=str(path),
                line=line,
                rule=rule,
                snippet=snippet.strip(),
                checklists=list(checklists),
            )
        )
        self.checklists.update(checklists)


def iter_python_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_file() and path.suffix == ".py":
            files.append(path)
        elif path.is_dir():
            files.extend(sorted(path.rglob("*.py")))
    return files


def scan_file(path: Path, result: ProbeResult) -> None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"error: cannot read {path}: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    lines = text.splitlines()
    for rule_name, pattern, checklists in PATTERN_RULES:
        if rule_name == "doc-contract-gap":
            for match in pattern.finditer(text):
                line = text[: match.start()].count("\n") + 1
                snippet = match.group(0).splitlines()[0]
                result.add(path, line, rule_name, snippet, checklists)
            continue

        for index, line in enumerate(lines, start=1):
            if pattern.search(line):
                result.add(path, index, rule_name, line.strip(), checklists)

    if "class " in text and "Protocol" in text:
        result.add(
            path,
            0,
            "protocol-port",
            "Protocol definition",
            ("application-wiring", "api-contracts"),
        )

    if re.search(r"\b(match\b.*:|\bassert_never\b)", text):
        result.add(path, 0, "exhaustive-branching", "match/assert_never", ("state-transitions",))


def render_text(result: ProbeResult) -> str:
    if not result.hits:
        return "No review leads found."

    lines = ["Suggested checklists:"]
    for name in CHECKLISTS:
        if name in result.checklists:
            lines.append(f"- {name}")

    lines.append("")
    lines.append("Leads:")
    for hit in result.hits:
        checklist_text = ", ".join(hit.checklists)
        location = f"{hit.path}:{hit.line}" if hit.line else hit.path
        lines.append(f"- {location} [{hit.rule}] -> {checklist_text}")
        if hit.snippet:
            lines.append(f"  {hit.snippet}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path, help="Python files or directories to scan")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text")
    args = parser.parse_args(argv)

    files = iter_python_files(args.paths)
    if not files:
        print("error: no Python files found", file=sys.stderr)
        return 1

    result = ProbeResult()
    for path in files:
        scan_file(path, result)

    # Always suggest tests when any lead exists
    if result.hits:
        result.checklists.add("tests")

    if args.json:
        payload = {
            "checklists": [name for name in CHECKLISTS if name in result.checklists],
            "hits": [
                {
                    "path": hit.path,
                    "line": hit.line,
                    "rule": hit.rule,
                    "snippet": hit.snippet,
                    "checklists": hit.checklists,
                }
                for hit in result.hits
            ],
        }
        print(json.dumps(payload, indent=2))
    else:
        print(render_text(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
