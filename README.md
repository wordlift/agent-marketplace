# WordLift Agent Marketplace

Marketplace metadata for WordLift agent plugins.

This repository is intentionally a catalog. Plugin implementation files stay in
their source repositories; marketplace entries point to Git-backed plugin
sources.

## Available Plugins

- `graph-sync-agent-kit`: graph-sync curation, project implementation, repository
  lifecycle, YARRRML review, postprocessor authoring, and GitHub workflow review.

## Codex

Add the marketplace:

```bash
codex plugin marketplace add wordlift/agent-marketplace --ref main
```

Install Graph Sync Agent Kit:

```bash
codex plugin add graph-sync-agent-kit@wordlift
```

## Claude Code

Add the marketplace:

```bash
claude plugin marketplace add wordlift/agent-marketplace
```

Install Graph Sync Agent Kit:

```bash
claude plugin install graph-sync-agent-kit@wordlift
```

## Repository Layout

```text
.agents/plugins/marketplace.json
.claude-plugin/marketplace.json
scripts/validate_marketplace.py
```

## Maintenance

When releasing a new version of a plugin, update the matching marketplace entry
`ref` to the plugin release tag. Keep Codex and Claude entries aligned.
