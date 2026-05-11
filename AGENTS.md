# OpenCode Plugin Playground

A playground for developing and experimenting with opencode plugins. The opencode source
code is available as a git submodule at `repos/opencode/` (branch: dev) for inspecting
internal APIs, plugin systems, and TUI components. Working plugin examples are under
`plugins/`.

## Critical Constants

- opencode repo: `repos/opencode/` (git submodule, branch: dev)
- plugins dir: `plugins/`
- Plugin entry: `plugins/{name}/src/index.ts` or `plugins/{name}/src/index.tsx` (for TUI)
- Installation: `opencode plugin add <path>` (CLI command)

## Plugin Projects

### oclitellmac-server
Server plugin that automatically configures multiple LiteLLM proxy endpoints as OpenCode providers.
- **Purpose**: Auto-discovery and configuration of LiteLLM models
- **Config**: `~/.config/oclitellmac/server.json`
- **State**: `~/.local/state/oclitellmac/providers/` (model cache)
- **Budget tracking**: Polls `/key/info` endpoint, stores to `~/.local/state/oclitellmac/key-info/`
- **Features**: Multiple endpoints, smart caching with fallback, automatic auth injection, category filtering
- **Architecture**: Modular pipeline (fetch → categorize → map → build → filter → transform)
- **Docs**: `plugins/oclitellmac-server/README.md`, `ARCHITECTURE.md`

### oclitellmac-tui
TUI plugin that displays LiteLLM budget information in the OpenCode sidebar.
- **Purpose**: Visual display of budget/usage data
- **Data source**: Reads files from `~/.local/state/oclitellmac/key-info/`
- **Updates**: File watcher (fs.watch) with 5s polling fallback
- **Requires**: `oclitellmac-server` plugin to generate budget data
- **Features**: Real-time updates, color-coded alerts, multi-provider display

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

For AGENTS.md conventions and cost optimization strategy:
Read @docs/agents-file-conventions.md

When exploring opencode internals (SDK types, plugin APIs, provider system, TUI components):
Read @repos/opencode/AGENTS.md

When analyzing server plugin field coverage (provider/model fields, LiteLLM API mapping):
Read @docs/opencode-litellm/plugin-fields.md

When understanding the shared pipeline architecture (Python tool + TypeScript plugin):
Read @docs/opencode-litellm/ARCHITECTURE.md

When implementing new features or fixing bugs (agent-focused implementation guide):
Read @docs/opencode-litellm/IMPLEMENTATION.md
