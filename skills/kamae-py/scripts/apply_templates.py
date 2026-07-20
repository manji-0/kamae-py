"""Copy Kamae Python project templates into a target repository."""

from __future__ import annotations

import argparse
import shutil
from dataclasses import dataclass
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_ROOT = SKILL_ROOT / "assets" / "templates"


@dataclass(frozen=True)
class TemplateCopy:
    source_name: str
    target: Path
    description: str
    source_dir: Path = TEMPLATE_ROOT


BASE_TEMPLATES = (
    TemplateCopy(
        "pyproject.toml", Path("pyproject.toml"), "uv/Pydantic/Ruff/pyrefly/pytest config"
    ),
    TemplateCopy("gitignore", Path(".gitignore"), "Python tool cache ignores"),
)

SKILL_SCRIPT_TEMPLATES = (
    TemplateCopy(
        "check_kamae_policy.py",
        Path("scripts") / "check_kamae_policy.py",
        "stdlib-only Kamae policy checker",
        source_dir=SKILL_ROOT / "scripts",
    ),
)

CI_TEMPLATES = {
    "backend": TemplateCopy(
        "github-ci.yml",
        Path(".github") / "workflows" / "ci.yml",
        "GitHub Actions workflow for backend projects",
    ),
    "skill-package": TemplateCopy(
        "github-ci-skill-package.yml",
        Path(".github") / "workflows" / "ci.yml",
        "GitHub Actions workflow with skill package validation",
    ),
}

SKILL_PACKAGE_TEMPLATES = (
    TemplateCopy(
        "validate_package.py",
        Path("scripts") / "validate_package.py",
        "stdlib-only skill package validator",
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Copy Kamae Python templates into a repository. Existing files are not "
            "overwritten unless --force is set."
        )
    )
    parser.add_argument(
        "--target",
        type=Path,
        default=Path.cwd(),
        help="Repository root to receive templates. Defaults to the current directory.",
    )
    parser.add_argument(
        "--ci",
        choices=("none", "backend", "skill-package"),
        default="backend",
        help="Which CI template to install.",
    )
    parser.add_argument(
        "--skill-package",
        action="store_true",
        help="Also install scripts/validate_package.py for skill/plugin repositories.",
    )
    parser.add_argument(
        "--no-policy-checker",
        action="store_true",
        help=(
            "Skip installing scripts/check_kamae_policy.py. "
            "If you use this, remove the Check Kamae policy step from the generated CI workflow."
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing target files.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show planned copies without writing files.",
    )
    return parser.parse_args()


def selected_templates(
    ci: str, include_skill_package: bool, include_policy_checker: bool
) -> list[TemplateCopy]:
    templates = list(BASE_TEMPLATES)
    if include_policy_checker:
        templates.extend(SKILL_SCRIPT_TEMPLATES)
    if ci != "none":
        templates.append(CI_TEMPLATES[ci])
    if include_skill_package:
        templates.extend(SKILL_PACKAGE_TEMPLATES)
    return templates


def copy_template(template: TemplateCopy, target_root: Path, *, force: bool, dry_run: bool) -> str:
    source = template.source_dir / template.source_name
    target = target_root / template.target

    if not source.is_file():
        raise FileNotFoundError(f"missing template: {source}")

    if target.exists() and not force:
        return f"skip existing {template.target} ({template.description})"

    if dry_run:
        action = "overwrite" if target.exists() else "create"
        return f"{action} {template.target} from {template.source_name} ({template.description})"

    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    return f"wrote {template.target} ({template.description})"


def main() -> int:
    args = parse_args()
    target_root = args.target.resolve()
    include_policy_checker = not args.no_policy_checker
    templates = selected_templates(
        args.ci,
        args.skill_package or args.ci == "skill-package",
        include_policy_checker,
    )

    for template in templates:
        print(copy_template(template, target_root, force=args.force, dry_run=args.dry_run))

    if not args.dry_run:
        print(
            "Review copied templates before committing; "
            "merge with existing project config as needed."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
