# WordLift Agent Marketplace

<p align="center">
  <img src="assets/image.png" alt="WordLift Agent Marketplace" />
</p>

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

`graph-sync-agent-kit` release tags update this marketplace automatically. The
release workflow updates the matching Codex and Claude Code `ref` values, then
pushes the marketplace commit.

For manual maintenance, keep Codex and Claude entries aligned and point each
plugin `ref` to a release tag from the source repository.
