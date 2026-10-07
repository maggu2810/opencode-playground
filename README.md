# Notes

## Documentation

- [Package Management](docs/package-management.md) — npm, arborist, pacote, and
  Bun module resolution, and OpenCode plugin installation notes
- [LiteLLM Integration Field Coverage Comparison](docs/litellm-integration/field-coverage-comparison.md) —
  field coverage across the 4 LiteLLM integration implementations
- [LiteLLM Integration Shared Pipeline Architecture](docs/litellm-integration/shared-pipeline-architecture.md) —
  the shared pipeline architecture used by the Python tool and TypeScript plugin
- [LiteLLM Integration Implementation Guide](docs/litellm-integration/implementation-guide.md) —
  implementation guide for config-generator and oclitellmac
- [LiteLLM Integration Source Map](docs/litellm-integration/source-map.md) —
  single source of truth for the exact commit/tag of every third-party repo
  referenced by the LiteLLM integration docs
- [Open Issues](docs/open-issues.md) — known problems and decisions still
  to make (config-generator under OpenCode v2, submodule pins)

## opencode on Termux on Android

https://github.com/Hope2333/opencode-termux/

---

## Plugins

### Distribution options

There are two ways to distribute an OpenCode v2 plugin:

**1. npm registry or Git specifier**
Publish the plugin as an npm package (public or private registry) or host it in a
Git repository. Users add it with `opencode plugin add <package>`. Entries are
resolved from the package's `package.json` `exports`.

**2. Local directory (development and internal use)**
Register an absolute directory path in the global server config. The directory
must contain entry files (`server.*` or `index.*`, and/or `tui.*`); V2 does not
consult `exports` for local directories, so `oclitellmac` registers its built
`dist/` directory. `opencode plugin add` rejects local paths, so this is done by
editing the config.

When using `opencode plugin` commands, registration, config files, or spec formats, [read the plugin CLI guide](plugins/oclitellmac/docs/opencode-plugin-cli.md)

When looking for Git-URL specifier forms or install-cache behavior, [read the package management notes](docs/package-management.md)

---

### Plugin User — Getting Started

For `oclitellmac`, [read here](plugins/oclitellmac/AGENTS.md) and follow the install
instructions in its docs.

`plugins/tui-playground-v1` is a V1 teaching example. Its source-only layout cannot
be added by path in V2; see the V1 notes below.

---

### Plugin Developer — Setup

- Edit sources under `plugins/<name>/src/` and rebuild if the plugin has a build step.
- Restart OpenCode to reload the plugin after changes.
- OpenCode source (plugin APIs, TUI interfaces, SDK types) is in the submodule at
  `repos/opencode/` — it is the reference for V2 behavior.
- The `plugins/` directory is the working area for all plugin experiments.

---

### Writing a V2 TUI plugin — `package.json` structure

A V2 plugin module default-exports `{ id, setup(ctx) }`. For a TUI plugin the type is
`Plugin.Definition` from `@opencode/plugin/tui`; `setup` may return a cleanup
function. V1 shapes (`{ id, tui }`, `async function(input)`) are rejected.

For npm/Git packages, entries are resolved from `exports`: `./server` (falling back
to `.`), `./tui`, `./rpc`. A TUI plugin package therefore still needs `exports["./tui"]`.
A server plugin that has a TUI entry is loaded in the TUI automatically; only
TUI-only plugins need a `plugins` entry in `~/.config/opencode/cli.json`
(`tui.json`/`tui.jsonc` are not read in V2).

Minimum `exports` for a TUI plugin package:

```json
{
  "name": "my-tui-plugin",
  "version": "1.0.0",
  "type": "module",
  "exports": {
    "./tui": {
      "import": "./src/index.tsx"
    }
  },
  "peerDependencies": {
    "@opentui/core": "*",
    "@opentui/solid": "*",
    "solid-js": "*"
  }
}
```

Key points:
- **`@opentui/*` and `solid-js` in `peerDependencies`, not `dependencies`** — OpenCode
  provides these at runtime (embedded in the binary). Installing your own copies
  causes JSX transform failures because the Solid transform registered by OpenCode
  does not cover a second copy in the plugin's own `node_modules/`
- **Source file must use `.tsx` extension** (not `.ts`) for files containing JSX
- **Local directory plugins** are resolved by entry files (`<dir>/tui`, `<dir>/server`,
  `<dir>/index`), not `exports`

Additional type notes (V2):
- Import types from `@opencode/plugin/tui` (namespace `Plugin`)
- Register UI with `ctx.ui.slot({ <prepend|append|before|after|replace>: "<slot path>", render })`
  (e.g. `sidebar.content`, `sidebar.footer`); there is no numeric `order`
- Theme comes from `ctx.theme` (tokens like `text.base`, `text.muted`, `border.base`)
- Cleanup is the function returned from `setup`

---

### Notes on the V1 example `tui-playground-v1`

`plugins/tui-playground-v1` is an intentionally V1 plugin kept as a teaching
artifact (V1 API: `api.slots.register`, `api.lifecycle.onDispose`, `tui.json`,
`opencode plugin <path>`). None of its install or API guidance applies to V2; use the
V2 sections above for new work. Do not edit its code.
