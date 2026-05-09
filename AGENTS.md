# OpenCode Plugin Playground

A playground for developing and experimenting with opencode plugins. The opencode source
code is available as a git submodule at `repos/opencode/` (branch: dev) for inspecting
internal APIs, plugin systems, and TUI components. Working plugin examples are under
`plugins/`.

## Critical Constants

- opencode repo: `repos/opencode/` (git submodule, branch: dev)
- plugins dir: `plugins/`
- Plugin entry: `plugins/{name}/src/index.ts`
- Installation: `opencode plugin add <path>` (CLI command)

## File Reading Instructions

For AGENTS.md conventions and cost optimization strategy:
Read @docs/agents-file-conventions.md

When exploring opencode internals (SDK types, plugin APIs, provider system, TUI components):
Read @repos/opencode/AGENTS.md

When analyzing server plugin field coverage (provider/model fields, LiteLLM API mapping):
Read @docs/opencode-litellm/plugin-fields.md
