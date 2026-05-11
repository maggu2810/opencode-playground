# Notes

## opencode on Termux on Android

https://github.com/Hope2333/opencode-termux/

---

## Plugins

### Distribution options

There are three ways to distribute an OpenCode plugin:

**1. File path (this repo)**
The user clones the repository and registers the plugin by local path. Requires
manual dependency installation (see below). Best for development and internal use.

**2. npm registry**
Publish the plugin as an npm package to [npmjs.com](https://npmjs.com) (public)
or a private registry. OpenCode fetches and installs it automatically — no cloning,
no manual `npm install` needed:
```
opencode plugin my-plugin-name
```

**3. GitHub / git URL**
OpenCode passes the spec directly to `@npmcli/arborist`, which handles git URLs the
same way `npm install` does — no cloning or manual install required. Several forms work:

```sh
# GitHub shorthand (package.json in repo root)
opencode plugin github:your-org/your-repo

# Full git URL
opencode plugin git+https://github.com/your-org/your-repo.git

# Bare GitHub shorthand
opencode plugin your-org/your-repo

# package.json in a subdirectory (e.g. a monorepo)
opencode plugin "github:your-org/your-repo#path:packages/my-plugin"

# Specific branch or commit + subdirectory
opencode plugin "git+https://github.com/your-org/your-repo.git#main::path:packages/my-plugin"

# Semver tag + subdirectory
opencode plugin "git+https://github.com/your-org/your-repo.git#semver:^1.0.0::path:packages/my-plugin"

# Global config
opencode plugin github:your-org/your-repo --global
```

> **Note:** Git URL plugins bypass OpenCode's install cache — arborist re-runs on every
> OpenCode startup, which is slightly slower than an npm-published package.

---

### Plugin User — Getting Started

Clone the repository and enter the plugin directory:

```sh
git clone https://github.com/de23a4/genai
cd genai/repos/opencode-playground/plugins/tui-playground-v1
```

Install dependencies (required — OpenCode does **not** install them automatically
for file-path plugins):

```sh
# using npm
npm install

# or using bun (faster)
bun install
```

Register the plugin with OpenCode. Pass the path to the plugin directory — several
forms are accepted:

```sh
# absolute path, project-local config
opencode plugin /home/alice/repos/opencode-playground/plugins/tui-playground-v1

# absolute path, global config (available in all projects)
opencode plugin /home/alice/repos/opencode-playground/plugins/tui-playground-v1 --global

# relative path (resolved from current directory)
opencode plugin ./plugins/tui-playground-v1

# file:// URI
opencode plugin file:///home/alice/repos/opencode-playground/plugins/tui-playground-v1
```

OpenCode writes the path into `opencode.jsonc` (local) or
`~/.config/opencode/opencode.jsonc` (global) and loads the plugin at startup.
No further steps needed.

---

### Plugin Developer — Setup

Follow the Plugin User steps above first, then:

- Edit `src/index.tsx` — no pre-build step is needed. OpenCode imports TypeScript
  and TSX directly via Bun at load time (`await import(entry)`), no compilation step.
- Restart OpenCode to reload the plugin after changes.
- OpenCode source (plugin APIs, TUI interfaces, SDK types) is in the submodule at
  `repos/opencode/` — use it as the reference for available hooks and types.
- The `plugins/` directory is the working area for all plugin experiments.

---

### Writing a TUI plugin — required `package.json` structure

OpenCode determines the plugin type (server, TUI, or both) by inspecting the
`exports` map in `package.json`, **not** the `main` field alone.

| Target | Detection mechanism | Config file written |
|---|---|---|
| Server plugin | `exports["./server"]` present, **or** `main` / `exports["."]` with a `server()` export | `opencode.jsonc` |
| TUI plugin | `exports["./tui"]` present | `tui.json` |

**A plugin without `exports["./tui"]` will never be registered as a TUI plugin**,
even if its default export contains a `tui` function. The installer detects
"server target" only and adds it to `opencode.jsonc` — the TUI loader never sees it.

Minimum `package.json` for a TUI plugin:

```json
{
  "name": "my-tui-plugin",
  "version": "1.0.0",
  "type": "module",
  "main": "./src/index.tsx",
  "exports": {
    "./tui": {
      "import": "./src/index.tsx"
    }
  },
  "dependencies": {
    "@opencode-ai/plugin": "*",
    "@opencode-ai/sdk": "*"
  },
  "peerDependencies": {
    "@opentui/core": "*",
    "@opentui/keymap": "*",
    "@opentui/solid": "*",
    "solid-js": "*"
  }
}
```

Key points:
- **`exports["./tui"].import`** — points to the plugin entrypoint; required for TUI detection
- **`@opentui/*` and `solid-js` in `peerDependencies`, not `dependencies`** — OpenCode
  provides these at runtime (they are embedded in the OpenCode binary). Installing
  your own copies causes JSX transform failures because the Solid/Babel transform
  registered by OpenCode at startup does not cover a second copy in the plugin's
  own `node_modules/`
- **`@opencode-ai/plugin` and `@opencode-ai/sdk` in `dependencies`** — these are
  type-only imports; they are not provided by OpenCode's runtime and must be installed
  in the plugin's own `node_modules/`
- **Source file must use `.tsx` extension** (not `.ts`) for files containing JSX —
  TypeScript does not parse JSX syntax in `.ts` files regardless of `jsxImportSource`

Additional type correctness notes (confirmed against OpenCode source):
- Import TUI types from `@opencode-ai/plugin/tui`, not `@opencode-ai/plugin`
- `api.slots.register()` returns a `string` ID, not a dispose function — no need
  to pass it to `api.lifecycle.onDispose()`
- `TuiSlotPlugin` has no `id` field — omit it from the `register()` call
- Valid `borderStyle` values include `"rounded"`, not `"round"`
