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

**3. GitHub / git URL** _(not yet verified for OpenCode — to be documented)_

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

- Edit `src/index.ts` — no pre-build step is needed. OpenCode bundles TypeScript
  directly via Bun at load time.
- Restart OpenCode to reload the plugin after changes.
- OpenCode source (plugin APIs, TUI interfaces, SDK types) is in the submodule at
  `repos/opencode/` — use it as the reference for available hooks and types.
- The `plugins/` directory is the working area for all plugin experiments.
