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

For AGENTS.md conventions and cost optimization strategy:
Read @docs/agents-file-conventions.md

When exploring opencode internals (SDK types, plugin APIs, provider system, TUI components):
Read @repos/opencode/AGENTS.md

When working on oclitellmac plugin:
Read @plugins/oclitellmac/AGENTS.md

When comparing LiteLLM integration approaches (field coverage across 4 implementations):
Read @docs/litellm-integration/field-coverage-comparison.md

When understanding the shared pipeline architecture (Python tool + TypeScript plugin):
Read @docs/litellm-integration/shared-pipeline-architecture.md

When implementing features in config-generator or oclitellmac (implementation guide):
Read @docs/litellm-integration/implementation-guide.md
