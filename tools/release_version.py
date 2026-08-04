#!/usr/bin/env python3
"""Plan automatic semantic releases from API, WoW-version, and node changes."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
API_PATHS = ("API.lua",)
VERSION_CATALOG = "tools/versions.json"
SEMVER_PATTERN = re.compile(
    r"^v(?P<major>0|[1-9][0-9]*)\."
    r"(?P<minor>0|[1-9][0-9]*)\."
    r"(?P<patch>0|[1-9][0-9]*)$"
)
BUILD_PATTERN = re.compile(
    r'^\s*build = "(?P<build>[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)"',
    flags=re.MULTILINE,
)
TAXI_NODES_PATTERN = re.compile(r"^Data/([^/]+)/TaxiNodes\.lua$")


@dataclass(frozen=True)
class SemanticVersion:
    major: int
    minor: int
    patch: int

    @classmethod
    def from_tag(cls, tag: str) -> SemanticVersion:
        match = SEMVER_PATTERN.fullmatch(tag)
        if not match:
            raise ValueError(f"Invalid semantic release tag: {tag!r}")
        return cls(*(int(match.group(name)) for name in ("major", "minor", "patch")))

    def tag(self) -> str:
        return f"v{self.major}.{self.minor}.{self.patch}"


@dataclass(frozen=True)
class ReleasePlan:
    level: str | None
    version: SemanticVersion | None
    reasons: tuple[str, ...]

    @property
    def changed(self) -> bool:
        return self.version is not None


def plan_release(
    previous_tag: str | None,
    *,
    api_changed: bool = False,
    added_versions: tuple[str, ...] = (),
    node_updates: tuple[str, ...] = (),
) -> ReleasePlan:
    """Apply the project's automatic major/minor policy.

    Patch releases are deliberately absent: developers create those tags by hand.
    """
    if not previous_tag:
        return ReleasePlan(
            "major",
            SemanticVersion(1, 0, 0),
            ("initial semantic release",),
        )

    previous = SemanticVersion.from_tag(previous_tag)
    major_reasons: list[str] = []
    if api_changed:
        major_reasons.append("public API changed")
    if added_versions:
        major_reasons.append("new WoW versions: " + ", ".join(added_versions))
    if major_reasons:
        return ReleasePlan(
            "major",
            SemanticVersion(previous.major + 1, 0, 0),
            tuple(major_reasons),
        )

    if node_updates:
        return ReleasePlan(
            "minor",
            SemanticVersion(previous.major, previous.minor + 1, 0),
            ("build and taxi-node changes: " + ", ".join(node_updates),),
        )

    return ReleasePlan(None, None, ("no automatic release condition matched",))


def version_ids(document: str | None) -> set[str]:
    if document is None:
        return set()
    catalog = json.loads(document)
    if not isinstance(catalog, list):
        raise ValueError("tools/versions.json must contain a list")
    result: set[str] = set()
    for entry in catalog:
        if not isinstance(entry, dict) or not isinstance(entry.get("id"), str):
            raise ValueError("Every WoW version must contain a string id")
        result.add(entry["id"])
    return result


def semantic_nodes(document: str) -> str:
    lines = []
    for line in document.splitlines():
        if line.startswith("-- Source:") and "(build " in line:
            continue
        if line.lstrip().startswith("build = "):
            continue
        lines.append(line)
    return "\n".join(lines) + "\n"


def is_build_with_node_update(previous: str | None, current: str | None) -> bool:
    """Return true only when an existing data set changed build and node content."""
    if previous is None or current is None:
        return False
    previous_build = BUILD_PATTERN.search(previous)
    current_build = BUILD_PATTERN.search(current)
    if not previous_build or not current_build:
        return False
    return (
        previous_build.group("build") != current_build.group("build")
        and semantic_nodes(previous) != semantic_nodes(current)
    )


class GitRepository:
    def __init__(self, root: Path = ROOT, head: str = "HEAD") -> None:
        self.root = root
        self.head = head

    def run(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            ["git", *args],
            cwd=self.root,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if check and result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip()
            raise RuntimeError(f"git {' '.join(args)} failed: {detail}")
        return result

    def verify_ref(self, ref: str) -> None:
        self.run("rev-parse", "--verify", f"{ref}^{{commit}}")

    def file_at(self, ref: str, path: str, *, missing_ok: bool = False) -> str | None:
        result = self.run("show", f"{ref}:{path}", check=False)
        if result.returncode == 0:
            return result.stdout
        if missing_ok:
            return None
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"Unable to read {path} at {ref}: {detail}")

    def api_changed_since(self, ref: str) -> bool:
        result = self.run(
            "diff", "--quiet", ref, self.head, "--", *API_PATHS, check=False
        )
        if result.returncode not in (0, 1):
            detail = result.stderr.strip() or result.stdout.strip()
            raise RuntimeError(f"Unable to compare public API files: {detail}")
        return result.returncode == 1

    def taxi_node_paths(self, ref: str) -> set[str]:
        result = self.run("ls-tree", "-r", "--name-only", ref, "--", "Data")
        return {
            path
            for path in result.stdout.splitlines()
            if TAXI_NODES_PATTERN.fullmatch(path)
        }


def inspect_release(
    repository: GitRepository,
    previous_version_tag: str | None,
    previous_data_tag: str | None,
) -> ReleasePlan:
    if not previous_version_tag:
        return plan_release(None)

    SemanticVersion.from_tag(previous_version_tag)
    repository.verify_ref(previous_version_tag)
    api_changed = repository.api_changed_since(previous_version_tag)

    current_catalog = repository.file_at(repository.head, VERSION_CATALOG)
    previous_catalog = repository.file_at(
        previous_version_tag, VERSION_CATALOG, missing_ok=True
    )
    added_versions = tuple(
        sorted(version_ids(current_catalog).difference(version_ids(previous_catalog)))
    )

    node_updates: list[str] = []
    if previous_data_tag:
        repository.verify_ref(previous_data_tag)
        paths = repository.taxi_node_paths(previous_data_tag).intersection(
            repository.taxi_node_paths(repository.head)
        )
        for path in sorted(paths):
            if is_build_with_node_update(
                repository.file_at(previous_data_tag, path),
                repository.file_at(repository.head, path),
            ):
                match = TAXI_NODES_PATTERN.fullmatch(path)
                if match:
                    node_updates.append(match.group(1))

    return plan_release(
        previous_version_tag,
        api_changed=api_changed,
        added_versions=added_versions,
        node_updates=tuple(node_updates),
    )


def write_github_output(path: Path, plan: ReleasePlan) -> None:
    values = {
        "changed": str(plan.changed).lower(),
        "level": plan.level or "none",
        "tag": plan.version.tag() if plan.version else "",
        "reason": "; ".join(plan.reasons),
    }
    with path.open("a", encoding="utf-8", newline="\n") as output:
        for key, value in values.items():
            output.write(f"{key}={value}\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--previous-version-tag")
    parser.add_argument("--previous-data-tag")
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--github-output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repository = GitRepository(args.root.resolve(), args.head)
    plan = inspect_release(
        repository,
        args.previous_version_tag,
        args.previous_data_tag,
    )
    if args.github_output:
        write_github_output(args.github_output, plan)
    if plan.changed:
        print(
            f"Automatic {plan.level} release {plan.version.tag()}: "
            + "; ".join(plan.reasons)
        )
    else:
        print("No automatic release: " + "; ".join(plan.reasons))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
