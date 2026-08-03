# OpenCode Plugin Playground

A playground for developing and experimenting with opencode plugins. The opencode source
code is available as a git submodule at `repos/opencode/` (branch: dev) for inspecting
internal APIs, plugin systems, and TUI components. Working plugin examples are under
`plugins/`.

Read [project README](README.md) at the start of every session.
Its instructions are binding — follow them as if they were written in this file.

## Critical Constants

- opencode repo: `repos/opencode/` (git submodule, branch: dev)
- plugins dir: `plugins/`
- Plugin entry: `plugins/{name}/src/index.ts` or `plugins/{name}/src/index.tsx` (for TUI)
- Installation: `opencode plugin <path>` (CLI command)

## Skill Source of Truth

This repository's `skills/` directory is the authoritative, tracked source
for all skills owned by this project (e.g. `agents-md-setup`,
`review-changeset`). When working on any skill, always edit the files under
`skills/` in this repository. Never edit cached or installed copies (e.g.
`~/.cache/opencode/skills/`) — those are ephemeral, untracked, and any
changes made there are lost and do not propagate back to this repo.

## Plugin Projects

### oclitellmac
LiteLLM integration plugin (Git submodule).
- **Location**: `plugins/oclitellmac/` (submodule → github:maggu2810/oclitellmac)
- **Purpose**: Auto-discovery and configuration of LiteLLM models with budget tracking
- **Installation**: `opencode plugin github:maggu2810/oclitellmac`
- **Docs**: See `plugins/oclitellmac/AGENTS.md`

## Tools

### config-generator (Python)
Static config generator for LiteLLM proxy endpoints. Outputs `opencode.jsonc` file.
- **Location**: `tools/config-generator/`
- **Usage**: `python -m src.generate --base-url https://litellm.example.com [--bearer TOKEN] [--output opencode.jsonc]`
- **Purpose**: Generate static OpenCode configs for version control and manual review
- **Architecture**: Same modular pipeline as `oclitellmac-server` (shared design)
- **Modules**: `fetch.py`, `categorize.py`, `map.py`, `build.py`, `filter.py`, `render.py`
- **Features**: Category filtering via CLI flags (`--enable-embedding`, `--enable-all`, etc.)
- **Comparison**: Use Python tool for static configs; use TypeScript plugin for runtime multi-endpoint setup
- **Docs**: `tools/config-generator/README.md`

## File Reading Instructions

For AGENTS.md conventions and cost optimization strategy, [read here](.agents/docs/agents-file-conventions.md)

When creating or editing any markdown file in this project, [read here](.agents/docs/markdown-style-guide.md)

When understanding OpenCode plugin CLI commands and spec formats, [read here](plugins/oclitellmac/docs/opencode-plugin-cli.md)

When exploring opencode internals (SDK types, plugin APIs, provider system, TUI components), [read here](repos/opencode/AGENTS.md)

When working on oclitellmac plugin, [read here](plugins/oclitellmac/AGENTS.md)

When spawning subagents, include the full content of AGENTS.md in the
subagent prompt so the subagent performs the same README.md and doc
reference hops independently.
