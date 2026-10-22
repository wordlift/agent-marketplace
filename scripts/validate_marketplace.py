#!/usr/bin/env python3
"""Validate WordLift agent marketplace metadata."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


MARKETPLACE_NAME = "wordlift"
REPO_OWNER = "wordlift"
SEMVER_TAG_RE = re.compile(r"^v\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".", help="Marketplace repository root")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    errors: list[str] = []

    codex = load_json(root / ".agents" / "plugins" / "marketplace.json", errors)
    claude = load_json(root / ".claude-plugin" / "marketplace.json", errors)

    if codex is not None:
        validate_codex(codex, errors)
    if claude is not None:
        validate_claude(claude, errors)
    if codex is not None and claude is not None:
        validate_cross_catalog(codex, claude, errors)

    if errors:
        print("Marketplace validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"Marketplace validation passed: {root}")
    return 0


def validate_codex(catalog: dict[str, Any], errors: list[str]) -> None:
    if catalog.get("name") != MARKETPLACE_NAME:
        errors.append("Codex marketplace name must be `wordlift`")
    interface = catalog.get("interface")
    if not isinstance(interface, dict) or not non_empty_string(interface.get("displayName")):
        errors.append("Codex marketplace must define `interface.displayName`")

    for name, entry in plugin_entries(catalog, "Codex", errors).items():
        validate_codex_entry(name, entry, errors)


def validate_codex_entry(name: str, entry: dict[str, Any], errors: list[str]) -> None:
    source = entry.get("source")
    if not isinstance(source, dict):
        errors.append(f"Codex {name} entry must use an object `source`")
        return
    if source.get("source") != "url":
        errors.append(f"Codex {name} entry must use Git-backed `source: url`")
    if git_url_repo(source.get("url")) is None:
        errors.append(f"Codex {name} URL must be `https://github.com/{REPO_OWNER}/<repo>.git`")
    validate_ref(source.get("ref"), f"Codex {name}", errors)

    policy = entry.get("policy")
    if not isinstance(policy, dict):
        errors.append(f"Codex {name} entry must define `policy`")
        return
    if policy.get("installation") != "AVAILABLE":
        errors.append(f"Codex {name} policy.installation must be `AVAILABLE`")
    if policy.get("authentication") != "ON_INSTALL":
        errors.append(f"Codex {name} policy.authentication must be `ON_INSTALL`")
    if not non_empty_string(entry.get("category")):
        errors.append(f"Codex {name} entry must define `category`")


def validate_claude(catalog: dict[str, Any], errors: list[str]) -> None:
    if catalog.get("name") != MARKETPLACE_NAME:
        errors.append("Claude marketplace name must be `wordlift`")
    owner = catalog.get("owner")
    if not isinstance(owner, dict) or not non_empty_string(owner.get("name")):
        errors.append("Claude marketplace must define `owner.name`")
    if not non_empty_string(catalog.get("description")):
        errors.append("Claude marketplace must define `description`")

    for name, entry in plugin_entries(catalog, "Claude", errors).items():
        validate_claude_entry(name, entry, errors)


def validate_claude_entry(name: str, entry: dict[str, Any], errors: list[str]) -> None:
    source = entry.get("source")
    if not isinstance(source, dict):
        errors.append(f"Claude {name} entry must use an object `source`")
        return
    if source.get("source") != "github":
        errors.append(f"Claude {name} entry must use `source: github`")
    if github_repo(source.get("repo")) is None:
        errors.append(f"Claude {name} repo must be `{REPO_OWNER}/<repo>`")
    validate_ref(source.get("ref"), f"Claude {name}", errors)

    for key in ("displayName", "description", "version", "homepage", "repository", "category"):
        if not non_empty_string(entry.get(key)):
            errors.append(f"Claude {name} entry must define `{key}`")
    author = entry.get("author")
    if not isinstance(author, dict) or not non_empty_string(author.get("name")):
        errors.append(f"Claude {name} entry must define `author.name`")


def validate_cross_catalog(
    codex: dict[str, Any],
    claude: dict[str, Any],
    errors: list[str],
) -> None:
    # Problems inside each catalog were already reported above.
    codex_entries = plugin_entries(codex, "Codex", [])
    claude_entries = plugin_entries(claude, "Claude", [])

    for name in sorted(codex_entries.keys() - claude_entries.keys()):
        errors.append(f"`{name}` is in the Codex marketplace but not in the Claude one")
    for name in sorted(claude_entries.keys() - codex_entries.keys()):
        errors.append(f"`{name}` is in the Claude marketplace but not in the Codex one")

    for name in sorted(codex_entries.keys() & claude_entries.keys()):
        codex_source = codex_entries[name].get("source")
        claude_source = claude_entries[name].get("source")
        if not isinstance(codex_source, dict) or not isinstance(claude_source, dict):
            continue

        if git_url_repo(codex_source.get("url")) != github_repo(claude_source.get("repo")):
            errors.append(f"Codex and Claude {name} entries must point at the same repository")

        codex_ref = codex_source.get("ref")
        claude_ref = claude_source.get("ref")
        if codex_ref != claude_ref:
            errors.append(f"Codex and Claude {name} refs must match")

        claude_version = claude_entries[name].get("version")
        if isinstance(codex_ref, str) and isinstance(claude_version, str):
            if codex_ref.removeprefix("v") != claude_version:
                errors.append(f"Marketplace {name} ref must match Claude plugin entry version")


def require_plugins(
    catalog: dict[str, Any],
    label: str,
    errors: list[str],
) -> list[dict[str, Any]]:
    plugins = catalog.get("plugins")
    if not isinstance(plugins, list) or not plugins:
        errors.append(f"{label} marketplace must contain at least one plugin")
        return []
    if not all(isinstance(entry, dict) for entry in plugins):
        errors.append(f"{label} marketplace plugins must be objects")
        return []
    return plugins


def plugin_entries(
    catalog: dict[str, Any],
    label: str,
    errors: list[str],
) -> dict[str, dict[str, Any]]:
    entries: dict[str, dict[str, Any]] = {}
    for entry in require_plugins(catalog, label, errors):
        name = entry.get("name")
        if not non_empty_string(name):
            errors.append(f"{label} marketplace plugins must define `name`")
            continue
        if name in entries:
            errors.append(f"{label} marketplace must not duplicate `{name}`")
            continue
        entries[name] = entry
    return entries


def github_repo(repo: Any) -> str | None:
    """Return `wordlift/<repo>` when `repo` names a WordLift repository."""
    if not isinstance(repo, str):
        return None
    owner, _, name = repo.partition("/")
    if owner != REPO_OWNER or not name or "/" in name:
        return None
    return repo


def git_url_repo(url: Any) -> str | None:
    """Return `wordlift/<repo>` for a WordLift GitHub clone URL."""
    prefix = "https://github.com/"
    if not isinstance(url, str) or not url.startswith(prefix) or not url.endswith(".git"):
        return None
    return github_repo(url[len(prefix) : -len(".git")])


def validate_ref(ref: Any, label: str, errors: list[str]) -> None:
    if not isinstance(ref, str) or SEMVER_TAG_RE.fullmatch(ref) is None:
        errors.append(f"{label} source ref must be a semver tag")


def load_json(path: Path, errors: list[str]) -> dict[str, Any] | None:
    if not path.is_file():
        errors.append(f"missing `{path}`")
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"`{path}` must be valid JSON: {exc}")
        return None
    if not isinstance(payload, dict):
        errors.append(f"`{path}` must contain a JSON object")
        return None
    return payload


def non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


if __name__ == "__main__":
    sys.exit(main())
