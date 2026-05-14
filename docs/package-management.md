# npm Package Management & OpenCode Plugin Installation

Technical reference for npm ecosystem tools (npa, arborist, pacote, Bun resolution) and how OpenCode uses them for plugin installation.

---

## 1. Overview & Tool Relationships

**The npm ecosystem stack:**

```
┌─────────────────────────────────────────────────────────────┐
│                       npm CLI / opencode                     │
│  (parses user input, coordinates install, loads modules)    │
└───────────────────┬────────────────────────┬─────────────────┘
                    │                        │
        ┌───────────▼──────────┐   ┌────────▼──────────┐
        │  npm-package-arg     │   │  @npmcli/config   │
        │  (spec parser)       │   │  (npmrc reader)   │
        └──────────────────────┘   └───────────────────┘
                    │
        ┌───────────▼──────────┐
        │  @npmcli/arborist    │  ← The install engine
        │  (dependency tree    │     (opencode uses this directly)
        │   builder/installer) │
        └───────────┬──────────┘
                    │
        ┌───────────▼──────────┐
        │      pacote          │  ← The fetcher
        │  (tarball/git fetch) │     (arborist's internal dependency)
        └──────────────────────┘
                    │
        ┌───────────▼──────────┐
        │  npm registry / git  │
        │  (package sources)   │
        └──────────────────────┘
```

**Module resolution (runtime):**

```
┌─────────────────────────────────────────────────────────────┐
│  import() or import.meta.resolve()                          │
└───────────────────┬─────────────────────────────────────────┘
                    │
        ┌───────────▼──────────┐
        │  Bun runtime         │  ← Embedded in opencode binary
        │  (module resolver)   │
        └───────────┬──────────┘
                    │
      ┌─────────────┴─────────────┐
      │                           │
┌─────▼─────────┐      ┌─────────▼──────────┐
│ node_modules/ │      │ ~/.bun/install/    │  ← Global cache
│ (walk up tree)│      │      cache/        │     (Bun-specific)
└───────────────┘      └────────────────────┘
```

**Key distinction:** arborist/npm **install** packages into `node_modules/`; Bun **resolves** modules at runtime from `node_modules/` + global cache.

---

## 2. npm-package-arg (npa) — Spec Classification

**Purpose:** Parse package specifier strings into typed objects describing how to fetch them.

**Import:**
```typescript
import npa from "npm-package-arg"
const result = npa("some-package")
```

**Key fields in result:**
- `type`: `"range"` | `"version"` | `"git"` | `"directory"` | `"alias"` | `"tag"` | `"remote"`
- `name`: package name (e.g., `"express"`) — **undefined for git/directory/alias types**
- `raw`: original input string
- `rawSpec`: version/range/path component (e.g., `"^1.0.0"`, `"./path"`, etc.)
- `fetchSpec`: normalized fetchable spec (undefined for git types in many cases)

**Examples:**

```bash
# Test spec classification (Bun)
bun -e "
import npa from 'npm-package-arg';
const specs = [
  'opencode-forge',
  'opencode-forge@1.0.0',
  '@maggu2810/opencode-forge',
  'github:maggu2810/opencode-forge',
  'maggu2810/opencode-forge',
  'npm:opencode-forge',
  '/absolute/path',
  './relative/path',
  'file:///absolute/path',
];
for (const s of specs) {
  const r = npa(s);
  console.log(s, '->', r.type, '| name:', r.name ?? 'undefined', '| fetchSpec:', r.fetchSpec ?? 'null');
}
"
```

**Output:**
```
opencode-forge -> range | name: opencode-forge | fetchSpec: *
opencode-forge@1.0.0 -> version | name: opencode-forge | fetchSpec: 1.0.0
@maggu2810/opencode-forge -> range | name: @maggu2810/opencode-forge | fetchSpec: *
github:maggu2810/opencode-forge -> git | name: undefined | fetchSpec: null
maggu2810/opencode-forge -> git | name: undefined | fetchSpec: null
npm:opencode-forge -> alias | name: undefined | fetchSpec: null
/absolute/path -> directory | name: undefined | fetchSpec: /absolute/path
./relative/path -> directory | name: undefined | fetchSpec: <resolved-absolute-path>
file:///absolute/path -> directory | name: undefined | fetchSpec: /absolute/path
```

**Critical insight:** Git specs (`github:user/repo`, `user/repo`) have **`name: undefined`**. This causes fallback behavior in opencode's `Npm.add()`.

**Node.js equivalent:**
```bash
# Requires installing npm-package-arg separately
npm install npm-package-arg
node -e "const npa = require('npm-package-arg'); console.log(npa('github:user/repo'))"
```

---

## 3. npm Lifecycle Scripts & ignoreScripts

### 3.1 Lifecycle Script Execution Order

**During `npm install <pkg>` (installing a package):**

Scripts run **in the installed package's directory**, in this order:

1. `preinstall` — before package is installed
2. `install` — package being installed
3. `postinstall` — after package is installed

**Also triggered during local `npm install` (no args):**

4. `prepublish` (deprecated) — treated as alias for `prepare`
5. `prepare` — **critical for git dependencies**

**During `npm publish` / `npm pack`:**

1. `prepare` — before tarball is created
2. `prepublishOnly` — only on `npm publish`, not install
3. `prepack` — before tarball is packed
4. `postpack` — after tarball is created

### 3.2 The `prepare` Script — Git Dependency Build Hook

**When installing from a git repository** (e.g., `github:user/repo`), npm/arborist:

1. Clones the repository
2. Installs the package's `dependencies` **and** `devDependencies`
3. **Runs the `prepare` script** (if present)
4. Packs the result into a tarball
5. Installs the tarball into `node_modules/`

**This is the mechanism for git-hosted packages to build themselves from source.**

Example `package.json`:
```json
{
  "name": "my-plugin",
  "scripts": {
    "prepare": "bun run build",
    "build": "tsc && bun build --bundle src/index.ts"
  },
  "devDependencies": {
    "typescript": "^5.0.0"
  }
}
```

When installed via `npm install github:user/my-plugin`, the `prepare` script runs during install, generating `dist/`.

**Scripts with other names are NOT in the lifecycle:**

```json
{
  "scripts": {
    "build": "tsc",           // ❌ NOT auto-executed
    "compile": "tsc",         // ❌ NOT auto-executed
    "xbuild": "tsc",          // ❌ NOT auto-executed
    "custom": "do-something"  // ❌ NOT auto-executed
  }
}
```

Only `preinstall`, `install`, `postinstall`, `prepare`, `prepublish`, `prepublishOnly`, `prepack`, `postpack` are lifecycle hooks. Renaming `prepare` → `xprepare` prevents auto-execution.

### 3.3 ignoreScripts — Suppressing All Lifecycle Scripts

**What it does:** Prevents npm/arborist from executing **any** lifecycle scripts during install.

**When enabled:**
- No `preinstall`, `install`, `postinstall`
- No `prepare` — **git deps will not be built**
- No `prepublish`, `prepack`, etc.

**CLI usage:**

```bash
# One-time flag
npm install --ignore-scripts <package>

# Set persistently (user-level)
npm config set ignore-scripts true

# Check current setting
npm config get ignore-scripts

# Unset
npm config delete ignore-scripts
```

**In code (arborist):**

```typescript
const arborist = new Arborist({
  path: "/install/target/dir",
  ignoreScripts: true,  // ← Suppresses all scripts
})
```

**OpenCode behavior:** OpenCode **always** uses `ignoreScripts: true` (`repos/opencode/packages/core/src/npm.ts:90`). This means:

- Git-hosted plugins with a `prepare` build step will **not** be built during install
- The `dist/` directory must already exist in the git repository (committed), or the plugin will fail to load

**Workaround for git-hosted plugins:**

1. **Commit `dist/` to the repository** (add to git, remove from `.gitignore`)
2. **Rename the script** (e.g., `prepare` → `xprepare`) so it's not in the lifecycle
3. **Publish to npm** instead (use `npm:` or bare package name spec)

---

## 4. @npmcli/arborist — The Install Engine

**Purpose:** Build and manage the `node_modules/` dependency tree. The same engine npm CLI uses.

**Import:**
```typescript
import { Arborist } from "@npmcli/arborist"
```

### 4.1 Basic Usage

```typescript
const arborist = new Arborist({
  path: "/path/to/install/dir",    // Where to install (will create node_modules/ here)
  binLinks: true,                   // Create symlinks in node_modules/.bin
  ignoreScripts: true,              // Suppress lifecycle scripts
  progress: false,                  // Disable progress bars
  registry: "https://registry.npmjs.org",  // Optional: override registry
})

// Install packages
const tree = await arborist.reify({
  add: ["express@4.18.0", "github:user/repo"],  // Packages to install
  save: true,                         // Update package.json
  saveType: "prod",                   // prod | dev | optional | peer
})
```

### 4.2 Return Value — ArboristTree

```typescript
interface ArboristNode {
  name: string   // Package name from package.json
  path: string   // Absolute path to node_modules/<name>
}

interface ArboristTree {
  edgesOut: Map<string, { to?: ArboristNode }>
}
```

**For npm registry packages:**

```typescript
// After: arborist.reify({ add: ["express@4.18.0"] })
tree.edgesOut.get("express")?.to
// → { name: "express", path: "/path/to/node_modules/express" }
```

**For git packages:**

```typescript
// After: arborist.reify({ add: ["github:maggu2810/opencode-forge"] })
tree.edgesOut.get("github:maggu2810/opencode-forge")?.to
// → { name: "opencode-forge", path: "/path/to/node_modules/opencode-forge" }
//   (name comes from the repo's package.json, not the spec)
```

**Key behavior:**
- `edgesOut` maps **spec → installed package metadata**
- For npm specs: spec matches name
- For git specs: spec is `github:user/repo`, but `name` comes from `package.json` in the repo
- The `path` is where the package was installed (under `node_modules/`)

### 4.3 Git Package Install Behavior

When arborist installs `github:user/repo`:

1. **Fetches via pacote** (see Section 5)
2. Clones the git repo to a temp dir
3. Installs `dependencies` + `devDependencies` in the cloned repo
4. If `ignoreScripts: false`: runs `prepare` script
5. If `ignoreScripts: true`: **skips `prepare`** — no build step
6. Packs the repo into a tarball
7. Extracts tarball into `node_modules/<name>`

**Result:** Only files **committed to git** are included. If `dist/` is in `.gitignore` and not committed, it will be absent unless `prepare` runs (which is suppressed by `ignoreScripts: true`).

### 4.4 Manual Arborist Example

```typescript
import { Arborist } from "@npmcli/arborist"
import path from "path"

async function installPlugin(spec: string) {
  const installDir = "/tmp/test-install"
  const arborist = new Arborist({
    path: installDir,
    ignoreScripts: true,
  })

  const tree = await arborist.reify({
    add: [spec],
    save: false,
  })

  const edge = tree.edgesOut.values().next().value
  if (edge?.to) {
    console.log("Installed:", edge.to.name, "at", edge.to.path)
  }
}

await installPlugin("github:maggu2810/opencode-forge")
```

---

## 5. pacote — The Fetcher (Inside Arborist)

**Purpose:** Fetch package contents from npm registry or git repositories. Used internally by arborist; rarely called directly.

**Import:**
```typescript
import pacote from "pacote"
```

### 5.1 What Pacote Fetches

**For npm registry specs** (`express`, `express@4.18.0`, `@scope/pkg`):

- Fetches the **published tarball** from the registry
- URL pattern: `https://registry.npmjs.org/<pkg>/-/<pkg>-<version>.tgz`
- Contains only files specified in `package.json` `files` field (or not in `.npmignore`)
- `dist/` is typically included if in `files` (common for published packages)

**For git specs** (`github:user/repo`, `user/repo`):

- Clones the git repository
- URL pattern: `https://codeload.github.com/<user>/<repo>/tar.gz/<ref>`
- Contains only files **committed to git** (respects `.gitignore`)
- If `dist/` is in `.gitignore` and not committed: **absent**
- If `prepare` script runs: `dist/` is generated in the cloned copy before packing

**Critical difference:**

| Source          | Fetch mechanism       | `dist/` included?                                   |
|-----------------|-----------------------|-----------------------------------------------------|
| npm registry    | Published tarball     | Yes (if in `files` or not in `.npmignore`)          |
| git repository  | Clone + optional build| Only if committed OR `prepare` script generates it  |

### 5.2 Manual Fetch Examples

```bash
# Download published npm tarball
npm view opencode-forge@0.2.5 dist.tarball
# → https://registry.npmjs.org/opencode-forge/-/opencode-forge-0.2.5.tgz

curl -sL https://registry.npmjs.org/opencode-forge/-/opencode-forge-0.2.5.tgz | tar -xz
# Extracts to: package/

# Download git repository tarball (what pacote does for github: specs)
curl -sL https://codeload.github.com/maggu2810/opencode-forge/tar.gz/main | tar -xz
# Extracts to: opencode-forge-main/
```

**TypeScript equivalent:**
```typescript
import pacote from "pacote"

// Fetch and extract
await pacote.extract("github:user/repo", "./dest")

// Get tarball stream
const tarball = await pacote.tarball("opencode-forge@0.2.5")
```

### 5.3 Why Git Specs Differ

When you do `npm install github:user/repo`, pacote:

1. Clones the repo (full git history)
2. Checks out the specified ref (default: `HEAD` / main branch)
3. Runs `npm install` in the cloned dir (to install `devDependencies`)
4. Runs `prepare` script (if not suppressed by `ignoreScripts`)
5. Packs the working tree into a tarball (excludes `.gitignore`d files)

**This is why:**
- `github:` specs have access to `devDependencies` during build
- Published npm tarballs do not include `devDependencies`
- Git specs can build from source; npm specs are pre-built

**Inspection:**
```bash
# Show what would be published (respects .npmignore / files field)
npm pack --dry-run

# Shows list of files that would be in the tarball
```

---

## 6. @npmcli/config — npmrc & Registry Config

**Purpose:** Read and merge npm configuration from `.npmrc` files (project, user, global).

**Import:**
```typescript
import Config from "@npmcli/config"
```

### 6.1 Config File Precedence

npm config is merged from (highest to lowest priority):

1. **Project-level:** `<project-root>/.npmrc`
2. **User-level:** `~/.npmrc`
3. **Global:** `$PREFIX/etc/npmrc`
4. **Built-in defaults**

**Common settings:**

```ini
# ~/.npmrc
registry=https://registry.npmjs.org
ignore-scripts=false
//registry.npmjs.org/:_authToken=npm_xxxxxxxxxxxxx
```

### 6.2 CLI Usage

```bash
# Show all effective config
npm config list

# Get specific value
npm config get registry
npm config get ignore-scripts

# Set value (user-level)
npm config set registry https://custom.registry.com
npm config set ignore-scripts true

# Delete value
npm config delete ignore-scripts
```

### 6.3 How OpenCode Uses Config

OpenCode loads npm config via `@npmcli/config` and passes it to arborist:

```typescript
// repos/opencode/packages/core/src/npm-config.ts
import Config from "@npmcli/config"

export const load = (dir: string) =>
  Effect.tryPromise({
    try: async () => {
      const config = new Config({
        cwd: dir,
        // ... other options
      })
      await config.load()
      return config.flat as Record<string, unknown>
    },
    // ...
  })
```

Then in arborist setup:

```typescript
// repos/opencode/packages/core/src/npm.ts:78-91
const npmOptions = yield* NpmConfig.load(input.dir)
const arborist = new Arborist({
  ...npmOptions,  // ← Includes registry, auth tokens, etc.
  path: input.dir,
  ignoreScripts: true,  // ← But always overrides to true
})
```

**Result:** OpenCode respects user's registry, auth tokens, and proxy settings from `.npmrc`, but always suppresses scripts.

---

## 7. Bun Module Resolution (import.meta.resolve)

**Purpose:** Resolve a module specifier to an absolute file path/URL at runtime.

### 7.1 Node.js vs Bun Differences

**Node.js:**
```javascript
import.meta.resolve("package-name")
// Resolves relative to the current module's directory
// Walks up node_modules/ tree
// No global cache fallback
```

**Bun:**
```javascript
import.meta.resolve("package-name", "/from/directory")
// Resolves from the specified directory
// Walks up node_modules/ tree from that directory
// Falls back to ~/.bun/install/cache/ (global cache)
```

### 7.2 Bun Global Install Cache

Bun maintains a global cache at `~/.bun/install/cache/` for all packages installed via `bun install` anywhere on the system.

**Structure:**
```
~/.bun/install/cache/
├── @opentui/
│   ├── solid@0.2.6@@@1/
│   ├── solid@0.2.8@@@1/
│   ├── core@0.2.6@@@1/
│   └── ...
├── express@4.18.0@@@1/
└── ...
```

**Resolution behavior:**

```javascript
// When Bun does import.meta.resolve("@opentui/solid", someDir):
// 1. Check someDir/node_modules/@opentui/solid
// 2. Check someDir/../node_modules/@opentui/solid
// 3. Walk up to filesystem root
// 4. Fall back to ~/.bun/install/cache/@opentui/solid@<version>@@@1/
```

**This is unique to Bun.** Node.js stops at filesystem root.

### 7.3 Testing Resolution

```bash
# Test if a module resolves from a given directory (Bun)
bun -e "
try {
  const resolved = import.meta.resolve('@opentui/solid', '/some/path');
  console.log('resolved:', resolved);
} catch(e) {
  console.log('failed:', e.message);
}
"
```

**Example:** Why `@opentui/solid` resolution fails for some plugins:

```bash
# From plugin's dist/ directory (where import() happens):
bun -e "
const tuiDir = '/home/user/.cache/opencode/packages/github:user/plugin/node_modules/@user/plugin/dist';
try {
  const r = import.meta.resolve('@opentui/solid', tuiDir);
  console.log('resolved:', r);
} catch(e) {
  console.log('failed:', e.message);
}
"
# Output: failed: Cannot find module '@opentui/solid' from '<path>'
# Because: @opentui/solid is not in node_modules/ tree, and Bun global cache fallback
# only works when the *runtime* has installed it, not when it's a peerDependency
```

**Why opencode's built-in TUI works:**

OpenCode calls `ensureRuntimePluginSupport()` which registers `@opentui/core`, `@opentui/keymap/*` as Bun runtime plugins. However, `@opentui/solid` and `solid-js` are **not** registered — they rely on Bun's global cache resolution.

### 7.4 import.meta.resolve in OpenCode

```typescript
// repos/opencode/packages/core/src/npm.ts:47-57
const resolveEntryPoint = (name: string, dir: string): EntryPoint => {
  let entrypoint: Option.Option<string>
  try {
    // Bun variant: resolve `name` from `dir`
    const resolved = typeof Bun !== "undefined"
      ? import.meta.resolve(name, dir)
      : import.meta.resolve(dir)  // Node variant: resolve dir itself
    entrypoint = Option.some(resolved)
  } catch {
    entrypoint = Option.none()
  }
  return { directory: dir, entrypoint }
}
```

**Called with:**
- `name`: package name (e.g., `"opencode-forge"`)
- `dir`: path to `node_modules/opencode-forge`

**Returns:** `file:///path/to/node_modules/opencode-forge/dist/index.js` (resolved entry point)

---

## 8. Putting It Together: Without OpenCode (CLI Usage)

Manual equivalents of everything OpenCode does, runnable directly.

### 8.1 Classify a Package Spec

```bash
# Bun
bun -e "
import npa from 'npm-package-arg';
const result = npa('github:maggu2810/opencode-forge');
console.log(JSON.stringify(result, null, 2));
"

# Node.js (requires separate install)
npm install npm-package-arg
node -e "const npa = require('npm-package-arg'); console.log(npa('github:user/repo'))"
```

### 8.2 Install a Package with ignoreScripts

```bash
# Using npm CLI
npm install --ignore-scripts github:maggu2810/opencode-forge

# Set globally (affects all installs)
npm config set ignore-scripts true
npm install github:maggu2810/opencode-forge
npm config delete ignore-scripts  # Reset

# Using arborist directly (Node.js/Bun)
bun -e "
import { Arborist } from '@npmcli/arborist';
const arborist = new Arborist({
  path: '/tmp/test-install',
  ignoreScripts: true,
});
const tree = await arborist.reify({
  add: ['github:maggu2810/opencode-forge'],
});
console.log('Installed:', tree.edgesOut.values().next().value?.to);
"
```

### 8.3 Fetch Published Tarball

```bash
# Get tarball URL
npm view opencode-forge@0.2.5 dist.tarball
# → https://registry.npmjs.org/opencode-forge/-/opencode-forge-0.2.5.tgz

# Download and extract
curl -sL $(npm view opencode-forge@0.2.5 dist.tarball) | tar -xz
cd package/
ls -la dist/  # Verify dist/ exists
```

### 8.4 Fetch Git Repository (Simulating github: spec)

```bash
# What pacote does internally for github:maggu2810/opencode-forge
curl -sL https://codeload.github.com/maggu2810/opencode-forge/tar.gz/main | tar -xz
cd opencode-forge-main/
ls -la dist/  # Check if dist/ is committed to git
```

### 8.5 Inspect npm Config

```bash
# Show all config (merged from all .npmrc files)
npm config list

# Get specific settings
npm config get registry
npm config get ignore-scripts
npm config get _authToken  # (won't display for security)

# Check which .npmrc files are loaded
npm config list --json | jq '.["config"]'
```

### 8.6 Test Module Resolution

```bash
# Bun (with global cache fallback)
bun -e "
const path = '/some/install/dir/node_modules/my-package';
try {
  console.log('resolved:', import.meta.resolve('dependency', path));
} catch(e) {
  console.log('failed:', e.message);
}
"

# Check Bun global cache contents
ls ~/.bun/install/cache/
ls ~/.bun/install/cache/@opentui/
```

### 8.7 Show What Would Be Published

```bash
# Dry-run npm pack (shows files from package.json `files` field)
npm pack --dry-run

# Output shows which files would be included in tarball
```

---

## 9. How OpenCode Uses All of This

OpenCode uses arborist directly, not the npm CLI. Here's the complete flow.

### 9.1 Cache Path Derivation

**XDG cache base:**

```typescript
// repos/opencode/packages/core/src/global.ts:10-11
import { xdgCache } from "xdg-basedir"
const cache = path.join(xdgCache!, "opencode")
// → ~/.cache/opencode/ (Linux)
// → ~/Library/Caches/opencode/ (macOS)
```

**Per-package cache directory:**

```typescript
// repos/opencode/packages/core/src/npm.ts:77
const directory = (pkg: string) => path.join(global.cache, "packages", sanitize(pkg))
```

**Sanitization (Windows only):**

```typescript
// repos/opencode/packages/core/src/npm.ts:42-46
export function sanitize(pkg: string) {
  if (!illegal) return pkg  // Non-Windows: no-op
  return Array.from(pkg, (char) =>
    (illegal.has(char) || char.charCodeAt(0) < 32 ? "_" : char)
  ).join("")
}
```

**Examples:**

| Package spec                        | Cache directory (Linux)                                              |
|-------------------------------------|----------------------------------------------------------------------|
| `opencode-forge`                    | `~/.cache/opencode/packages/opencode-forge/`                         |
| `opencode-forge@1.0.0`              | `~/.cache/opencode/packages/opencode-forge@1.0.0/`                   |
| `@maggu2810/opencode-forge`         | `~/.cache/opencode/packages/@maggu2810/opencode-forge/`              |
| `github:maggu2810/opencode-forge`   | `~/.cache/opencode/packages/github:maggu2810/opencode-forge/`        |
| `github:maggu2810/opencode-forge`   | `~/.cache/opencode/packages/github_maggu2810_opencode-forge/` (Windows) |

### 9.2 Npm.add() — Plugin Install Flow

**Entry point:** `repos/opencode/packages/core/src/npm.ts:113`

```typescript
const add = Effect.fn("Npm.add")(function* (pkg: string) {
  // 1. Determine cache directory
  const dir = directory(pkg)  // ~/.cache/opencode/packages/<sanitized-pkg>/
  
  // 2. Parse spec to get package name (falls back to full spec if undefined)
  const name = (() => {
    try {
      return npa(pkg).name ?? pkg
    } catch {
      return pkg
    }
  })()
  
  // 3. Check if already cached
  if (yield* afs.existsSafe(path.join(dir, "node_modules", name))) {
    return resolveEntryPoint(name, path.join(dir, "node_modules", name))
  }
  
  // 4. Install via arborist
  const tree = yield* reify({ dir, add: [pkg] })
  
  // 5. Extract installed package metadata from edgesOut
  const first = tree.edgesOut.values().next().value?.to
  if (!first) {
    // Fallback: try to resolve directly (in case arborist installed but didn't populate edgesOut)
    const result = resolveEntryPoint(name, path.join(dir, "node_modules", name))
    if (Option.isSome(result.entrypoint)) return result
    return yield* new InstallFailedError({ add: [pkg], dir })
  }
  
  // 6. Resolve entry point using actual package name and path from arborist
  return resolveEntryPoint(first.name, first.path)
}, Effect.scoped)
```

**arborist.reify() call:**

```typescript
// repos/opencode/packages/core/src/npm.ts:78-106
const reify = (input: { dir: string; add?: string[] }) =>
  Effect.gen(function* () {
    yield* flock.acquire(`npm-install:${input.dir}`)  // Lock to prevent concurrent installs
    const { Arborist } = yield* Effect.promise(() => import("@npmcli/arborist"))
    const add = input.add ?? []
    const npmOptions = yield* NpmConfig.load(input.dir)  // Load .npmrc config
    const arborist = new Arborist({
      ...npmOptions,        // Include user's registry, auth, etc.
      path: input.dir,      // Where to install
      binLinks: true,       // Create .bin symlinks
      progress: false,      // No progress bars
      savePrefix: "",       // Don't add ^ or ~ to package.json
      ignoreScripts: true,  // ← ALWAYS suppresses lifecycle scripts
    })
    return yield* Effect.tryPromise({
      try: () =>
        arborist.reify({
          ...npmOptions,
          add,              // Packages to install
          save: true,       // Update package.json
          saveType: "prod", // Add as dependency (not devDependency)
        }),
      catch: (cause) => new InstallFailedError({ cause, add, dir: input.dir }),
    }) as Effect.Effect<ArboristTree, InstallFailedError>
  })
```

**Key behaviors:**

1. **Cache reuse:** If `node_modules/<name>` already exists in the cache dir, skip install
2. **Git spec name fallback:** For `github:user/repo`, `npa().name` is `undefined`, so `name` becomes `"github:user/repo"` — then `node_modules/github:user/repo` would never exist (invalid path), forcing install
3. **edgesOut extraction:** After install, `first.name` is the **actual package name** from `package.json` (e.g., `"opencode-forge"`), not the spec
4. **ignoreScripts: true:** `prepare` script never runs — git packages must have `dist/` committed

### 9.3 Npm.install() — Project Dependency Sync

**Purpose:** Install dependencies in a project directory (not a plugin).

**Entry point:** `repos/opencode/packages/core/src/npm.ts:138`

```typescript
const install: Interface["install"] = Effect.fn("Npm.install")(function* (dir, input) {
  // 1. Check if directory is writable
  const canWrite = yield* afs.access(dir, { writable: true }).pipe(
    Effect.as(true),
    Effect.orElseSucceed(() => false),
  )
  if (!canWrite) return  // Skip if read-only
  
  // 2. Map input packages to spec strings
  const add = input?.add.map((pkg) => [pkg.name, pkg.version].filter(Boolean).join("@")) ?? []
  
  // 3. If node_modules/ doesn't exist, install immediately
  if (!(yield* afs.existsSafe(path.join(dir, "node_modules")))) {
    yield* reify({ add, dir })
    return
  }
  
  // 4. Check if package.json and package-lock.json are in sync
  const pkg = yield* afs.readJson(path.join(dir, "package.json")).pipe(Effect.orElseSucceed(() => ({})))
  const lock = yield* afs.readJson(path.join(dir, "package-lock.json")).pipe(Effect.orElseSucceed(() => ({})))
  
  const declared = new Set([
    ...Object.keys(pkg?.dependencies || {}),
    ...Object.keys(pkg?.devDependencies || {}),
    ...Object.keys(pkg?.peerDependencies || {}),
    ...Object.keys(pkg?.optionalDependencies || {}),
    ...(input?.add || []).map((p) => p.name),
  ])
  
  const locked = new Set([
    ...Object.keys(lock?.packages?.[""]?.dependencies || {}),
    ...Object.keys(lock?.packages?.[""]?.devDependencies || {}),
    ...Object.keys(lock?.packages?.[""]?.peerDependencies || {}),
    ...Object.keys(lock?.packages?.[""]?.optionalDependencies || {}),
  ])
  
  // 5. If any declared dep is missing from lock, reify
  for (const name of declared) {
    if (!locked.has(name)) {
      yield* reify({ dir, add })
      return
    }
  }
}, Effect.scoped)
```

**When it runs:** Called by OpenCode when syncing project dependencies (e.g., after adding a server plugin that has npm dependencies).

### 9.4 pluginSource() and resolvePluginTarget()

**Purpose:** Classify a plugin spec as `"file"` or `"npm"` and resolve it to a directory path.

**pluginSource:**

```typescript
// repos/opencode/packages/opencode/src/plugin/shared.ts:56-59
export function pluginSource(spec: string): PluginSource {
  if (isPathPluginSpec(spec)) return "file"
  return "npm"
}

// repos/opencode/packages/opencode/src/plugin/shared.ts:170-172
export function isPathPluginSpec(spec: string) {
  return spec.startsWith("file://") || spec.startsWith(".") || isAbsolutePath(spec)
}
```

**Classification:**

| Spec                                  | pluginSource |
|---------------------------------------|--------------|
| `/absolute/path`                      | `"file"`     |
| `./relative/path`                     | `"file"`     |
| `file:///absolute/path`               | `"file"`     |
| `opencode-forge`                      | `"npm"`      |
| `@maggu2810/opencode-forge`           | `"npm"`      |
| `github:maggu2810/opencode-forge`     | `"npm"`      |

**resolvePluginTarget:**

```typescript
// repos/opencode/packages/opencode/src/plugin/shared.ts:207-213
export async function resolvePluginTarget(spec: string) {
  if (isPathPluginSpec(spec)) return resolvePathPluginTarget(spec)
  
  // For npm specs (including git):
  const hit = parse(spec)
  const pkg = hit?.name && hit.raw === hit.name ? `${hit.name}@latest` : spec
  const result = await Npm.add(pkg)
  return result.directory
}
```

**Pkg transformation:**

| Input spec                          | npa type | `hit.name`      | `hit.raw === hit.name` | `pkg` passed to Npm.add              |
|-------------------------------------|----------|-----------------|------------------------|--------------------------------------|
| `opencode-forge`                    | range    | `"opencode-forge"` | true                   | `"opencode-forge@latest"`            |
| `opencode-forge@1.0.0`              | version  | `"opencode-forge"` | false                  | `"opencode-forge@1.0.0"`             |
| `@maggu2810/opencode-forge`         | range    | `"@maggu2810/..."` | true                   | `"@maggu2810/opencode-forge@latest"` |
| `github:maggu2810/opencode-forge`   | git      | `undefined`     | false                  | `"github:maggu2810/opencode-forge"`  |

**Return value:** `result.directory` is `~/.cache/opencode/packages/<sanitized-spec>/`

### 9.5 resolveEntryPoint() via import.meta.resolve

**Purpose:** Find the actual `.js` file to `import()` for a package.

```typescript
// repos/opencode/packages/core/src/npm.ts:47-61
const resolveEntryPoint = (name: string, dir: string): EntryPoint => {
  let entrypoint: Option.Option<string>
  try {
    const resolved = typeof Bun !== "undefined"
      ? import.meta.resolve(name, dir)   // Bun: resolve `name` starting from `dir`
      : import.meta.resolve(dir)         // Node: resolve `dir` itself
    entrypoint = Option.some(resolved)
  } catch {
    entrypoint = Option.none()
  }
  return {
    directory: dir,
    entrypoint,
  }
}
```

**Called with:**
- `name`: package name (e.g., `"opencode-forge"`)
- `dir`: path to `node_modules/opencode-forge`

**Bun resolution:**
1. Reads `node_modules/opencode-forge/package.json`
2. Checks `exports` field for `"."` entry
3. Falls back to `main` field
4. Returns `file:///path/to/node_modules/opencode-forge/dist/index.js`

**Example:**

```typescript
resolveEntryPoint("opencode-forge", "/home/user/.cache/opencode/packages/github:maggu2810/opencode-forge/node_modules/opencode-forge")
// Returns:
// {
//   directory: "/home/user/.cache/opencode/packages/github:maggu2810/opencode-forge/node_modules/opencode-forge",
//   entrypoint: Some("file:///home/user/.cache/opencode/packages/github:maggu2810/opencode-forge/node_modules/opencode-forge/dist/index.js")
// }
```

### 9.6 TUI Plugin Loading — ensureRuntimePluginSupport & @opentui Resolution

**ensureRuntimePluginSupport:**

```typescript
// repos/opencode/packages/opencode/src/cli/cmd/tui/plugin/runtime.ts:1-2,43
import { ensureRuntimePluginSupport } from "@opentui/solid/runtime-plugin-support/configure"

ensureRuntimePluginSupport({ additional: keymapRuntimeModules })
```

**What it does:**

Registers Bun runtime plugins for:
- `@opentui/core`
- `@opentui/core/testing`
- `@opentui/keymap/*` (via `keymapRuntimeModules`)

**What is NOT registered:**
- `@opentui/solid` — must be resolved via `node_modules/` or Bun global cache
- `solid-js` — must be resolved via `node_modules/` or Bun global cache

**Plugin loading:**

```typescript
// repos/opencode/packages/opencode/src/plugin/loader.ts:119-128
export async function load(row: Resolved): Promise<{ ok: true; value: Loaded } | { ok: false; error: unknown }> {
  let mod
  try {
    mod = await import(row.entry)  // row.entry is file:///path/to/dist/tui.js
  } catch (error) {
    return { ok: false, error }
  }
  if (!mod) return { ok: false, error: new Error(`Plugin ${row.spec} module is empty`) }
  return { ok: true, value: { ...row, mod } }
}
```

**When `import(row.entry)` executes:**

The TUI bundle (`dist/tui.js`) contains:
```typescript
import { createComponent } from "@opentui/solid"
import { createSignal } from "solid-js"
```

Bun resolves these imports by:
1. Starting from `dist/tui.js`'s directory
2. Walking up to find `node_modules/@opentui/solid`
3. If not found in `node_modules/` tree: falling back to `~/.bun/install/cache/@opentui/solid@<version>@@@1/`

**Why some plugins fail:**

If `@opentui/solid` is declared as an **optional peerDependency**, arborist does **not** install it into `node_modules/`. The plugin must then rely on Bun's global cache fallback.

If the Bun global cache doesn't have the exact version, or resolution starts from the wrong directory, `import()` fails with:

```
Cannot find module '@opentui/solid' from '/path/to/dist/tui.js'
```

**Workaround:** Install `@opentui/solid` and `solid-js` in `devDependencies` (pinned to the exact version OpenCode uses), build the plugin with those versions, and rely on Bun's global cache having them available at runtime.

---

## 10. Spec Type Reference Table

| Spec                                | npa type   | `name` field       | `pkg` → Npm.add               | Cache dir (Linux)                                       | arborist behavior                                        | `prepare` runs? | `dist/` available?                          | OpenCode result                          |
|-------------------------------------|------------|--------------------|-------------------------------|---------------------------------------------------------|----------------------------------------------------------|-----------------|---------------------------------------------|------------------------------------------|
| `opencode-forge`                    | `range`    | `"opencode-forge"` | `"opencode-forge@latest"`     | `~/.cache/opencode/packages/opencode-forge@latest/`     | Fetches latest from npm registry                         | No¹             | Yes (from published tarball)                | Installs to cache, resolves entry        |
| `opencode-forge@1.0.0`              | `version`  | `"opencode-forge"` | `"opencode-forge@1.0.0"`      | `~/.cache/opencode/packages/opencode-forge@1.0.0/`      | Fetches v1.0.0 from npm registry                         | No¹             | Yes (from published tarball)                | Installs to cache, resolves entry        |
| `@maggu2810/opencode-forge`         | `range`    | `"@maggu2810/..."` | `"@maggu2810/...@latest"`     | `~/.cache/opencode/packages/@maggu2810/opencode-forge@latest/` | Fetches latest from npm registry (scoped)        | No¹             | Yes (from published tarball)                | Installs to cache, resolves entry        |
| `github:maggu2810/opencode-forge`   | `git`      | `undefined`        | `"github:maggu2810/..."`      | `~/.cache/opencode/packages/github:maggu2810/opencode-forge/` | Clones git repo, installs deps                   | No¹             | Only if committed (`.gitignore` respected)  | Fails if `dist/` missing; succeeds if committed |
| `maggu2810/opencode-forge`          | `git`      | `undefined`        | `"maggu2810/opencode-forge"`  | `~/.cache/opencode/packages/maggu2810/opencode-forge/`  | Same as `github:` (implicit GitHub)                      | No¹             | Only if committed                           | Same as `github:`                        |
| `npm:opencode-forge`                | `alias`    | `undefined`²       | `"npm:opencode-forge"`        | `~/.cache/opencode/packages/npm:opencode-forge/`        | Resolves alias to npm registry, fetches                  | No¹             | Yes (from published tarball)                | Installs to cache, resolves entry        |
| `/absolute/path`                    | `directory`| `undefined`        | N/A³                          | N/A (not cached)                                        | N/A (direct path, no arborist)                           | N/A             | Depends on local filesystem                 | Resolves directly, no install            |
| `./relative/path`                   | `directory`| `undefined`        | N/A³                          | N/A (not cached)                                        | N/A (direct path, no arborist)                           | N/A             | Depends on local filesystem                 | Resolves directly, no install            |
| `file:///absolute/path`             | `directory`| `undefined`        | N/A³                          | N/A (not cached)                                        | N/A (direct path, no arborist)                           | N/A             | Depends on local filesystem                 | Resolves directly, no install            |

**Footnotes:**

¹ OpenCode always uses `ignoreScripts: true`, so `prepare` never runs. For git specs without committed `dist/`, this causes failure.

² For `alias` type, `npa().name` is `undefined`, but `subSpec.name` contains the actual package name. OpenCode doesn't extract `subSpec`, so falls back to full spec string.

³ Path specs bypass `Npm.add()` entirely — they go through `resolvePathPluginTarget()` which directly returns the path as a `file://` URL.

---

## 11. Inspection Commands

### 11.1 Classify a Package Spec (npa)

```bash
# Bun (if npa is installed in current project or globally)
bun -e "
import npa from 'npm-package-arg';
const result = npa('github:maggu2810/opencode-forge');
console.log(JSON.stringify({
  type: result.type,
  name: result.name,
  raw: result.raw,
  rawSpec: result.rawSpec,
  fetchSpec: result.fetchSpec,
}, null, 2));
"

# Node.js (requires separate npm install npm-package-arg)
node -e "
const npa = require('npm-package-arg');
const r = npa('github:maggu2810/opencode-forge');
console.log(JSON.stringify(r, null, 2));
"
```

### 11.2 Get Published Package Metadata

```bash
# Get tarball URL
npm view opencode-forge@0.2.5 dist.tarball

# Get all metadata
npm view opencode-forge@0.2.5

# Get specific field (package.json field)
npm view opencode-forge@0.2.5 version
npm view opencode-forge@0.2.5 main
npm view opencode-forge@0.2.5 exports
npm view opencode-forge@0.2.5 oc-plugin
```

### 11.3 Download and Inspect Published Tarball

```bash
# Download
curl -sL https://registry.npmjs.org/opencode-forge/-/opencode-forge-0.2.5.tgz | tar -xz

# OR: use npm pack
npm pack opencode-forge@0.2.5
tar -xzf opencode-forge-0.2.5.tgz

# Inspect contents
cd package/
ls -la dist/
cat package.json
```

### 11.4 Download and Inspect Git Repository (github: spec)

```bash
# What pacote does for github:maggu2810/opencode-forge
curl -sL https://codeload.github.com/maggu2810/opencode-forge/tar.gz/main | tar -xz

cd opencode-forge-main/
ls -la dist/           # Check if dist/ is committed
cat .gitignore         # Check if dist/ is ignored
git log --oneline -5   # See recent commits
```

### 11.5 Show What Would Be Published (Local Package)

```bash
# From a package.json project directory
npm pack --dry-run

# Shows:
# - Which files would be included in tarball
# - Respects `files` field and .npmignore
# - Does not actually create tarball
```

### 11.6 Inspect npm Config

```bash
# Show all config (merged from all .npmrc files)
npm config list

# Get specific settings
npm config get registry
npm config get ignore-scripts
npm config get loglevel

# Show config as JSON
npm config list --json

# Check which .npmrc files exist
ls -la ~/.npmrc
ls -la ./.npmrc
```

### 11.7 Install with ignoreScripts

```bash
# One-time install
npm install --ignore-scripts github:maggu2810/opencode-forge

# Set config persistently
npm config set ignore-scripts true
npm install <package>
npm config delete ignore-scripts  # Reset

# Verify setting
npm config get ignore-scripts  # Should show: true
```

### 11.8 Inspect OpenCode Plugin Cache

```bash
# List all cached plugins
ls ~/.cache/opencode/packages/

# Inspect specific plugin cache
ls -la ~/.cache/opencode/packages/github:maggu2810/opencode-forge/
ls -la ~/.cache/opencode/packages/github:maggu2810/opencode-forge/node_modules/

# Check package.json in cache
cat ~/.cache/opencode/packages/github:maggu2810/opencode-forge/package.json

# Check installed package
ls ~/.cache/opencode/packages/github:maggu2810/opencode-forge/node_modules/opencode-forge/
cat ~/.cache/opencode/packages/github:maggu2810/opencode-forge/node_modules/opencode-forge/package.json
```

### 11.9 Test Module Resolution (Bun)

```bash
# Test if a module resolves from a given directory
bun -e "
const fromDir = '/home/user/.cache/opencode/packages/github:maggu2810/opencode-forge/node_modules/opencode-forge';
try {
  const resolved = import.meta.resolve('@opentui/solid', fromDir);
  console.log('resolved:', resolved);
} catch(e) {
  console.log('failed:', e.message);
}
"

# Walk up directory tree to find where resolution succeeds
bun -e "
const paths = [
  '/home/user/.cache/opencode/packages/github:user/plugin/node_modules/@user/plugin/dist',
  '/home/user/.cache/opencode/packages/github:user/plugin/node_modules/@user/plugin',
  '/home/user/.cache/opencode/packages/github:user/plugin/node_modules',
  '/home/user/.cache/opencode/packages/github:user/plugin',
  '/home/user/.cache/opencode/packages',
];
for (const p of paths) {
  try {
    const r = import.meta.resolve('@opentui/solid', p);
    console.log('FOUND walking from:', p);
    console.log('  ->', r);
    break;
  } catch {
    console.log('not found walking from:', p);
  }
}
"
```

### 11.10 Check Bun Global Cache

```bash
# List all packages in Bun global cache
ls ~/.bun/install/cache/

# Check specific package versions
ls ~/.bun/install/cache/@opentui/
ls ~/.bun/install/cache/@opentui/solid@*/

# Inspect cached package
ls -la ~/.bun/install/cache/@opentui/solid@0.2.6@@@1/
cat ~/.bun/install/cache/@opentui/solid@0.2.6@@@1/package.json
```

### 11.11 Manual Arborist Install (Testing)

```bash
# Create test install directory
mkdir -p /tmp/test-arborist-install
cd /tmp/test-arborist-install

# Run arborist via Bun
bun -e "
import { Arborist } from '@npmcli/arborist';
const arborist = new Arborist({
  path: process.cwd(),
  ignoreScripts: true,
});
const tree = await arborist.reify({
  add: ['github:maggu2810/opencode-forge'],
  save: false,
});
const first = tree.edgesOut.values().next().value?.to;
console.log('Installed package:');
console.log('  name:', first?.name);
console.log('  path:', first?.path);
"

# Inspect result
ls -la node_modules/
ls -la node_modules/opencode-forge/
```

### 11.12 Compare npm Tarball vs Git Clone

```bash
# Setup
mkdir -p /tmp/compare-sources && cd /tmp/compare-sources

# Fetch npm tarball
mkdir npm-tarball && cd npm-tarball
curl -sL $(npm view opencode-forge@0.2.5 dist.tarball) | tar -xz
mv package/* .
rmdir package

# Fetch git repository
cd /tmp/compare-sources
mkdir git-clone && cd git-clone
curl -sL https://codeload.github.com/maggu2810/opencode-forge/tar.gz/main | tar -xz
mv opencode-forge-main/* .
rmdir opencode-forge-main

# Compare
cd /tmp/compare-sources
diff -qr npm-tarball/ git-clone/ | head -20

# Check dist/ specifically
ls -la npm-tarball/dist/ | head -10
ls -la git-clone/dist/ 2>&1 | head -10
```

---

## 12. Source File References

**OpenCode source files (repos/opencode/):**

- `packages/core/src/global.ts:10-24` — XDG cache path derivation, `Path.cache` definition
- `packages/core/src/npm.ts:42-46` — `sanitize()` function (Windows path sanitization)
- `packages/core/src/npm.ts:47-61` — `resolveEntryPoint()` using `import.meta.resolve`
- `packages/core/src/npm.ts:77` — `directory(pkg)` cache path computation
- `packages/core/src/npm.ts:78-106` — `reify()` arborist wrapper with `ignoreScripts: true`
- `packages/core/src/npm.ts:113-136` — `Npm.add()` plugin install flow
- `packages/core/src/npm.ts:138-189` — `Npm.install()` project dependency sync
- `packages/core/src/npm-config.ts` — `@npmcli/config` loading and registry resolution
- `packages/opencode/src/plugin/shared.ts:56-59` — `pluginSource()` classification
- `packages/opencode/src/plugin/shared.ts:170-172` — `isPathPluginSpec()` check
- `packages/opencode/src/plugin/shared.ts:207-213` — `resolvePluginTarget()` entry point
- `packages/opencode/src/plugin/shared.ts:103-113` — `resolvePackageEntrypoint()` using `exports` field
- `packages/opencode/src/plugin/loader.ts:119-128` — `load()` dynamic import of plugin module
- `packages/opencode/src/cli/cmd/tui/plugin/runtime.ts:1-2,43` — `ensureRuntimePluginSupport()` call

**Documentation links:**

- npm lifecycle scripts: `man npm-scripts` or https://docs.npmjs.com/cli/v10/using-npm/scripts
- arborist API: https://github.com/npm/arborist
- npm-package-arg: https://github.com/npm/npm-package-arg
- pacote: https://github.com/npm/pacote
- Bun module resolution: https://bun.sh/docs/runtime/modules

---

## 13. Quick Reference: Key Takeaways

**npm registry vs git repository installs:**

| Source         | Fetch method         | `prepare` runs? | `dist/` included?                     |
|----------------|----------------------|-----------------|---------------------------------------|
| npm registry   | Published tarball    | No¹             | Yes (from `files` in package.json)    |
| git repository | Clone + optional build | No¹           | Only if committed (not in .gitignore) |

¹ OpenCode uses `ignoreScripts: true`

**Why `github:` installs fail without committed `dist/`:**

1. Arborist clones the git repo (only committed files)
2. `ignoreScripts: true` skips the `prepare` script (no build)
3. If `dist/` is in `.gitignore` and not committed: **absent**
4. Plugin tries `import("./dist/tui.js")` → **file not found**

**Workarounds:**

- **Commit `dist/` to the git repository** (remove from `.gitignore`)
- **Rename the script** (`prepare` → `xprepare`) so it's not a lifecycle hook
- **Publish to npm** (use `npm:opencode-forge` or bare name spec)

**Why `@opentui/solid` resolution fails for some plugins:**

1. `@opentui/solid` declared as **optional peerDependency**
2. Arborist does **not** install optional peers
3. Plugin's `dist/tui.js` does `import { x } from "@opentui/solid"`
4. Bun walks up from `dist/` directory, checks `node_modules/` at each level
5. If not found in tree: falls back to `~/.bun/install/cache/`
6. If not in Bun global cache: **fails**

**Workaround:**

Install `@opentui/solid` and `solid-js` in `devDependencies` (pinned to exact OpenCode version), ensuring Bun's global cache has them.

**Essential commands:**

```bash
# Classify spec
bun -e "import npa from 'npm-package-arg'; console.log(npa('github:user/repo'))"

# Install without scripts
npm install --ignore-scripts <package>

# Inspect cache
ls ~/.cache/opencode/packages/

# Test resolution
bun -e "try { console.log(import.meta.resolve('@opentui/solid', '/path')) } catch(e) { console.log('failed') }"
```

---

**End of document.**
