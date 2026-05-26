#!/usr/bin/env python3
"""Validate WordLift agent marketplace metadata."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


PLUGIN_NAME = "graph-sync-agent-kit"
PLUGIN_REPO = "wordlift/graph-sync-agent-kit"
PLUGIN_GIT_URL = "https://github.com/wordlift/graph-sync-agent-kit.git"
MARKETPLACE_NAME = "wordlift"
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

    plugins = require_plugins(catalog, "Codex", errors)
    if not plugins:
        return
    entry = require_plugin_entry(plugins, "Codex", errors)
    if entry is None:
        return

    source = entry.get("source")
    if not isinstance(source, dict):
        errors.append("Codex graph-sync-agent-kit entry must use an object `source`")
        return
    if source.get("source") != "url":
        errors.append("Codex graph-sync-agent-kit entry must use Git-backed `source: url`")
    if source.get("url") != PLUGIN_GIT_URL:
        errors.append(f"Codex graph-sync-agent-kit URL must be `{PLUGIN_GIT_URL}`")
    validate_ref(source.get("ref"), "Codex", errors)

    policy = entry.get("policy")
    if not isinstance(policy, dict):
        errors.append("Codex graph-sync-agent-kit entry must define `policy`")
        return
    if policy.get("installation") != "AVAILABLE":
        errors.append("Codex graph-sync-agent-kit policy.installation must be `AVAILABLE`")
    if policy.get("authentication") != "ON_INSTALL":
        errors.append("Codex graph-sync-agent-kit policy.authentication must be `ON_INSTALL`")
    if not non_empty_string(entry.get("category")):
        errors.append("Codex graph-sync-agent-kit entry must define `category`")


def validate_claude(catalog: dict[str, Any], errors: list[str]) -> None:
    if catalog.get("name") != MARKETPLACE_NAME:
        errors.append("Claude marketplace name must be `wordlift`")
    owner = catalog.get("owner")
    if not isinstance(owner, dict) or not non_empty_string(owner.get("name")):
        errors.append("Claude marketplace must define `owner.name`")
    if not non_empty_string(catalog.get("description")):
        errors.append("Claude marketplace must define `description`")

    plugins = require_plugins(catalog, "Claude", errors)
    if not plugins:
        return
    entry = require_plugin_entry(plugins, "Claude", errors)
    if entry is None:
        return

    source = entry.get("source")
    if not isinstance(source, dict):
        errors.append("Claude graph-sync-agent-kit entry must use an object `source`")
        return
    if source.get("source") != "github":
        errors.append("Claude graph-sync-agent-kit entry must use `source: github`")
    if source.get("repo") != PLUGIN_REPO:
        errors.append(f"Claude graph-sync-agent-kit repo must be `{PLUGIN_REPO}`")
    validate_ref(source.get("ref"), "Claude", errors)

    for key in ("displayName", "description", "version", "homepage", "repository", "category"):
        if not non_empty_string(entry.get(key)):
            errors.append(f"Claude graph-sync-agent-kit entry must define `{key}`")
    author = entry.get("author")
    if not isinstance(author, dict) or not non_empty_string(author.get("name")):
        errors.append("Claude graph-sync-agent-kit entry must define `author.name`")


def validate_cross_catalog(
    codex: dict[str, Any],
    claude: dict[str, Any],
    errors: list[str],
) -> None:
    codex_entry = require_plugin_entry(codex.get("plugins", []), "Codex", errors)
    claude_entry = require_plugin_entry(claude.get("plugins", []), "Claude", errors)
    if codex_entry is None or claude_entry is None:
        return

    codex_ref = codex_entry.get("source", {}).get("ref")
    claude_ref = claude_entry.get("source", {}).get("ref")
    if codex_ref != claude_ref:
        errors.append("Codex and Claude graph-sync-agent-kit refs must match")

    claude_version = claude_entry.get("version")
    if isinstance(codex_ref, str) and isinstance(claude_version, str):
        if codex_ref.removeprefix("v") != claude_version:
            errors.append("Marketplace ref must match Claude plugin entry version")


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


def require_plugin_entry(
    plugins: list[dict[str, Any]],
    label: str,
    errors: list[str],
) -> dict[str, Any] | None:
    matches = [entry for entry in plugins if entry.get("name") == PLUGIN_NAME]
    if not matches:
        errors.append(f"{label} marketplace must include `{PLUGIN_NAME}`")
        return None
    if len(matches) > 1:
        errors.append(f"{label} marketplace must not duplicate `{PLUGIN_NAME}`")
        return None
    return matches[0]


def validate_ref(ref: Any, label: str, errors: list[str]) -> None:
    if not isinstance(ref, str) or SEMVER_TAG_RE.fullmatch(ref) is None:
        errors.append(f"{label} graph-sync-agent-kit source ref must be a semver tag")


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
