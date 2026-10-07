# npm Package Management & OpenCode Plugin Installation

Technical reference for npm ecosystem tools (npa, arborist, pacote, Bun resolution) and how OpenCode uses them for plugin installation.

## Documentation Guidelines

**Source verification requirement:**

All factual claims in this document must be verified from actual source files with file path + line/function references. If a statement has not been verified by reading the source in the current session:

- Mark it as an **open question** or **unconfirmed**
- Do NOT state it as a conclusion
- Include suspected factors but label them clearly as unverified

**Examples:**

✅ **Correct (source-verified):**
> `@opentui/solid` is registered via `defaultRuntimeModules` *(verified: `@opentui/solid@0.2.6` `scripts/runtime-plugin-support-configure.ts:34-37`)*

❌ **Incorrect (inference without source):**
> `@opentui/solid` is not registered — it relies on Bun's global cache

✅ **Correct (unverified but labeled):**
> The exact cause is not yet confirmed from source. Suspected factors: path containing `:` character, missing `bun.lock`.

**Reason:** Previous versions of this document contained incorrect statements that were presented as source-verified but were actually inferences. This rule ensures documentation accuracy.

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

**Critical insight:** Git specs (`github:user/repo`, `user/repo`) have **`name: undefined`**. OpenCode's `Npm.add()` then falls back to the arborist tree / staged `package.json` to learn the installed name (see 9.2).

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

### 3.3 ignoreScripts — Suppressing Lifecycle Scripts

**What it does:** Prevents npm/arborist from executing lifecycle scripts during install.

**When enabled:**
- No `preinstall`, `install`, `postinstall`
- No `prepare` (for npm registry packages)
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
  ignoreScripts: true,  // ← Suppresses lifecycle scripts
})
```

#### 3.3.1 The Git Dependency Exception — Why `ignoreScripts` Doesn't Fully Work

**Critical limitation:** For `github:user/repo` specs, `ignoreScripts: true` does **not** suppress the `prepare` script.

**Why:**

1. arborist passes `ignoreScripts: true` to pacote when calling `pacote.extract()`
2. pacote's `GitFetcher` clones the git repo and checks if **any** of these script names exist in `package.json`:
   - `postinstall`, **`build`**, `preinstall`, `install`, `prepack`, `prepare`
3. If **any** are found, `GitFetcher.#prepareDir` spawns an **npm subprocess**:
   ```bash
   npm install --force --include=dev --cache=... --no-save --no-audit
   ```
4. This subprocess does **not** receive `--ignore-scripts` — it runs with scripts **enabled**
5. `npm install` on a local directory runs the package's `prepare` script as part of its standard lifecycle
6. After the subprocess completes, pacote's `DirFetcher` runs the `prepare` script again, but this is skipped because `ignoreScripts: true` is checked at that stage

**Result:** The `prepare` script **executes via the npm subprocess**, regardless of `ignoreScripts: true` in arborist.

**Source references (pacote v21.5.0):**
- `lib/git.js:164-171` — script existence check (includes `build` in the list)
- `lib/git.js:193` — npm subprocess invocation without `--ignore-scripts`
- `lib/fetcher.js:105-121` — `npmCliConfig` construction (no `--ignore-scripts` added)
- `lib/dir.js:35-36` — `DirFetcher.#prepareDir` checks `ignoreScripts` (but runs after subprocess)

**OpenCode behavior:** OpenCode **always** uses `ignoreScripts: true` (`repos/opencode/packages/util/src/npm.ts`, `reify()`), but for `github:` specs:

- If the package has `prepare`, `build`, or other scripts → npm subprocess runs → `prepare` executes
- The `dist/` directory is generated during install **only if** the subprocess succeeds and the `prepare` script builds it
- If `dist/` is in `.gitignore` and not pre-committed, the build output from `prepare` is included

**Workarounds for git-hosted plugins:**

1. **Rename ALL lifecycle scripts** so the `GitFetcher` trigger condition is false:
   - Rename `prepare` → `xprepare` or `Xprepare`
   - Rename `build` → `xbuild` (critical — `build` is in the check list!)
   - Rename `install`, `postinstall`, `preinstall`, `prepack` if present
   - When **all** are renamed, the npm subprocess is **never invoked**
   
2. **Commit pre-built `dist/` to the repository** (add to git, remove from `.gitignore`)
   - Git clone includes committed files
   - Even if scripts don't run, `dist/` is present
   
3. **Publish to npm** instead (use `npm:` or bare package name spec)
   - npm registry tarballs bypass the git-specific subprocess
   - `ignoreScripts: true` fully suppresses scripts for registry packages

**Example fix (package.json):**

```json
{
  "scripts": {
    "Xprepare": "bun run build",     // ← Renamed from "prepare"
    "Xbuild": "bun scripts/build.ts", // ← Renamed from "build"
    "Xtest": "bun test"
  }
}
```

With all scripts renamed, the `GitFetcher` condition at `lib/git.js:164-171` evaluates to false → npm subprocess never runs → no scripts execute.

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

### 5.3 Git Dependency Two-Phase Build Process

When you do `npm install github:user/repo`, pacote uses a **two-phase process** to prepare the package. Understanding this flow is critical for debugging `github:` install issues.

#### Phase 1: GitFetcher.#prepareDir — npm Subprocess (Script-Triggered)

**Source:** `pacote v21.5.0 lib/git.js:160-197`

1. Pacote clones the git repository
2. Reads `package.json` from the cloned repo
3. **Checks if ANY of these script names exist:**
   ```javascript
   scripts.postinstall ||
   scripts.build ||          // ← NOTE: 'build' is NOT a lifecycle script
   scripts.preinstall ||
   scripts.install ||
   scripts.prepack ||
   scripts.prepare
   ```
4. **If ANY script exists** → spawns an npm subprocess:
   ```bash
   npm install --force \
     --cache=<cache-dir> \
     --prefer-offline=false \
     --no-progress \
     --no-save \
     --no-audit \
     --include=dev \
     --include=peer \
     --include=optional \
     --no-package-lock-only \
     --no-dry-run
   ```
   **Critical:** `--ignore-scripts` is **NOT** included in this command, even if arborist was called with `ignoreScripts: true`.

5. This subprocess runs in the cloned git directory
6. `npm install` on a local directory triggers the **standard npm lifecycle:**
   - Installs `dependencies` and `devDependencies` from `package.json`
   - Runs `preinstall` (if present)
   - Runs `install` (if present)
   - Runs `postinstall` (if present)
   - Runs `prepare` (if present) — **this is where builds happen**
7. `devDependencies` (like `typescript`, `@types/*`, build tools) are now installed in `node_modules/`
8. The `prepare` script (e.g., `"prepare": "tsc && bun build"`) executes and generates `dist/`

**Why the `build` script name matters:**

The `build` script is **not** a lifecycle script — npm install does not auto-execute it. Its presence in the check list (step 3) only determines **whether to run the subprocess at all**. If you have:

```json
{
  "scripts": {
    "build": "tsc",
    "prepare": "npm run build"
  }
}
```

The subprocess runs because `build` exists in the check → npm install triggers `prepare` → `prepare` calls `npm run build`.

If you rename **all** scripts:

```json
{
  "scripts": {
    "Xbuild": "tsc",
    "Xprepare": "npm run Xbuild"
  }
}
```

None of `postinstall`, `build`, `preinstall`, `install`, `prepack`, `prepare` exist → check is false → **subprocess never runs**.

#### Phase 2: DirFetcher.#prepareDir — Direct Execution (ignoreScripts-Aware)

**Source:** `pacote v21.5.0 lib/dir.js:30-55`

After the npm subprocess completes (or is skipped), pacote creates a `DirFetcher` and calls its `tarballFromResolved()` method.

`DirFetcher.#prepareDir`:

1. Reads `package.json` from the directory
2. **Checks `if (this.opts.ignoreScripts) return`** — respects `ignoreScripts: true`
3. If not suppressed: runs the `prepare` script using `@npmcli/run-script`:
   ```typescript
   await runScript({
     pkg: mani,
     event: 'prepare',
     path: this.resolved,
     stdio: 'pipe',
   })
   ```

**Key insight:** By this point, `prepare` has **already run** via the npm subprocess in Phase 1. Phase 2's `prepare` execution is skipped when `ignoreScripts: true`, but the damage is done — the subprocess already executed it.

#### Why ignoreScripts Doesn't Work for Git Specs

- **arborist** passes `ignoreScripts: true` to `pacote.extract()`
- **pacote** receives `opts.ignoreScripts = true`
- **DirFetcher** checks `ignoreScripts` and skips `prepare` in Phase 2
- **GitFetcher** does **not** check `ignoreScripts` before spawning the npm subprocess in Phase 1
- **npm subprocess** runs without `--ignore-scripts` → executes `prepare` as part of its standard lifecycle

**Result:** `prepare` runs via Phase 1 subprocess, regardless of `ignoreScripts: true`.

#### Comparison: Registry vs Git

| Step                         | npm registry spec                  | `github:` spec                                    |
|------------------------------|------------------------------------|---------------------------------------------------|
| Fetch source                 | Download published tarball         | Clone git repository                              |
| devDependencies              | Not included in tarball            | Cloned (`.gitignore` respected)                   |
| Phase 1 (GitFetcher)         | N/A (no git clone)                 | Check for scripts → spawn npm subprocess          |
| npm subprocess               | N/A                                | Runs `npm install` (no `--ignore-scripts`)        |
| `prepare` via subprocess     | N/A                                | **Executes** (regardless of `ignoreScripts`)     |
| Phase 2 (DirFetcher)         | Direct tarball extract             | Runs after Phase 1 subprocess                     |
| `prepare` via DirFetcher     | Skipped (tarball pre-built)        | Skipped if `ignoreScripts: true`                  |
| Final result                 | Pre-built `dist/` from tarball     | `dist/` from Phase 1 subprocess (if built) or committed files |

#### Inspection Commands

```bash
# Show what npm subprocess would be called (git.js:193)
# For a package with scripts.prepare or scripts.build:
npm install --force \
  --include=dev \
  --no-save \
  --no-audit \
  --no-progress

# This is the command pacote runs (with added --cache=... etc.)
```

**This is why:**
- `github:` specs can build from source even with `ignoreScripts: true` in arborist
- Published npm tarballs bypass Phase 1 entirely (no subprocess, no git clone)
- Renaming scripts to avoid the Phase 1 trigger is the only way to prevent builds for git specs

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

OpenCode loads npm config via `@npmcli/config` (`repos/opencode/packages/util/src/npm-config.ts`,
`NpmConfig.load(dir)` returns `config.flat`) and spreads it into the arborist options in
`Npm.reify()` (`packages/util/src/npm.ts`), then sets `path`, `ignoreScripts: true`, `audit: false`
and `savePrefix: ""` on top.

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
const tuiDir = '/home/user/.cache/opencode/npm/git-plugin-0123456789ab/<generation>/node_modules/@user/plugin/dist';
try {
  const r = import.meta.resolve('@opentui/solid', tuiDir);
  console.log('resolved:', r);
} catch(e) {
  console.log('failed:', e.message);
}
"
# Output: failed: Cannot find module '@opentui/solid' from '<path>'
# Note: import.meta.resolve does NOT use Bun runtime plugins — it's a static resolver.
# @opentui/solid is not in node_modules/ tree, and Bun can't find it via ancestor lookup.
```

**Why opencode's built-in TUI works:**

OpenCode calls `ensureRuntimePluginSupport()` (see 9.6.1), which registers Bun runtime plugins that provide virtual in-memory modules for `@opentui/*` and `solid-js`. `import.meta.resolve` does not use these runtime plugins.

### 7.4 import.meta.resolve in OpenCode

The V1 `resolveEntryPoint()` helper described here no longer exists in `packages/util/src/npm.ts`. Entry resolution for plugins is done by the plugin host; this section is intentionally left without OpenCode specifics because they were not re-verified. For observable behavior, when registering plugins, [read the plugin CLI guide](../plugins/oclitellmac/docs/opencode-plugin-cli.md).

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

OpenCode v2 uses arborist directly, not the npm CLI. The implementation is
`repos/opencode/packages/util/src/npm.ts` (`Npm` service: `add`, `resolve`, `check`,
`update`, `which`). For the user-facing commands (`opencode plugin add/list/check/update/remove`),
config files, and spec formats, when using or registering plugins, [read the plugin CLI guide](../plugins/oclitellmac/docs/opencode-plugin-cli.md).

### 9.1 Cache Path Derivation

The cache root is `<global.cache>/npm/<key>/` (`Npm` service `directory()`), where
`global.cache` is the OpenCode cache directory (`~/.cache/opencode` on Linux, from `Global`
in `packages/util/src/global.ts`). The `<key>` is derived from the spec by `npm-package-arg`:

| Spec type | `<key>` |
|---|---|
| Registry (`version`, `range`, `tag`) | `<name>@<spec>`, e.g. `opencode-forge@latest`, `opencode-forge@1.0.0` (`latest` when no spec given) |
| Git (`github:`, `user/repo`, `git+https://...`) | `git-<slug>-<12 hex of sha256(spec)>` |
| Other (directory, alias, ...) | Not installable: `add` is not meaningful, `check`/`update` fail |

On Windows, illegal characters (`<>:"|?*` and control characters) in the key are replaced
with `_` (`sanitize()`).

Each install is published as a numbered generation directory (`<key>/<timestamp>/node_modules/<name>`).
The two newest generations are kept; older ones are removed after 7 days (staging
directories after 1 hour) during `update`.

### 9.2 Npm.add() — Install Flow

1. Parse the spec with `npm-package-arg`; compute the cache directory.
2. Take a file lock (`npm-install:<dir>`). If a generation already contains the package
   and this is not an update, return it.
3. Reify into a `.staging-*` directory with arborist: npm config from `@npmcli/config`
   (see 6.3), `ignoreScripts: true`, `audit: false`, `save: true`, `saveType: "prod"`.
4. Resolve the installed package name from the arborist tree (`edgesOut`), falling back to
   the spec's name or the staged `package.json` dependencies. This matters for git specs,
   where `npa` returns no `name`.
5. Rename the staging directory to the next generation and return
   `{ directory, name, version?, revision? }`. For git specs the revision is the commit
   SHA read from `package-lock.json`.

`resolve(pkg)` returns the newest installed generation without installing. `check(pkg)`
compares the installed revision with the latest one via `pacote` (`manifest`/`resolve`)
and returns whether an update is available (immutable specs, i.e. exact versions and
commit SHAs, always return `false`). `update(pkg)` re-reifies with `preferOnline` and
`noGitRevCache`. `which(pkg, bin)` returns a binary path from `node_modules/.bin`.

Plugin entry resolution (which file is loaded, `exports` handling, local directories)
is not part of `Npm`; it lives in the plugin host. For the observable behavior, when
developing or registering plugins, [read the plugin CLI guide](../plugins/oclitellmac/docs/opencode-plugin-cli.md).

### 9.6 TUI Plugin Loading — Bun Runtime Plugin Mechanism

OpenCode's TUI provides `@opentui/*` and `solid-js` to plugins through **Bun runtime
plugins**, so plugins do not install their own copies.

#### 9.6.1 ensureRuntimePluginSupport — Virtual Module Registration

`packages/tui/src/plugin/runtime-plugin-support.bun.ts` calls `ensureRuntimePluginSupport()`
from `@opentui/solid/runtime-plugin-support/configure`, with `@opencode/plugin/tui`
(`Plugin`, `PluginContextProvider`, `usePlugin`) passed as an `additional` module. Bare
imports of the registered modules inside plugin code are redirected to the copies bundled
in the OpenCode binary instead of being looked up in the plugin's `node_modules/`.
Details of which modules are registered come from `@opentui/solid`
(`scripts/runtime-plugin-support-configure.ts`, `defaultRuntimeModules`, verified for
`@opentui/solid@0.2.6` in V1-era notes; not re-verified for the version used by V2).

#### 9.6.2 Known Issue: Colon in Path Breaks Plugin Loading (V1 observation)

In OpenCode v1, plugins installed via `github:` specs lived under a cache path containing
`:` (`~/.cache/opencode/packages/github:user/repo/`), and plugins whose full filesystem
path contained `:` failed to load (`Cannot find module '@opentui/solid'`). Standalone Bun
handled such paths correctly, so the cause was in OpenCode's loading code.

In V2 the git cache key no longer contains `:` (see 9.1), so the `github:` cache-path
trigger does not apply. Whether a `:` in a local plugin directory path still breaks
loading in V2 has **not been verified**; avoid `:` in local plugin paths until confirmed.

---

## 10. Spec Type Reference Table

Cache dirs are relative to `~/.cache/opencode/npm/` (Linux); see 9.1.

| Spec | npa type | `name` field | Cache key | arborist behavior | `prepare` runs? | `dist/` available? |
|---|---|---|---|---|---|---|
| `opencode-forge` | `range` | `"opencode-forge"` | `opencode-forge@latest` | Fetches latest from npm registry | No¹ | Yes (published tarball) |
| `opencode-forge@1.0.0` | `version` | `"opencode-forge"` | `opencode-forge@1.0.0` | Fetches v1.0.0 from npm registry | No¹ | Yes (published tarball) |
| `@maggu2810/opencode-forge` | `range` | `"@maggu2810/opencode-forge"` | `@maggu2810/opencode-forge@latest` | Fetches latest (scoped) | No¹ | Yes (published tarball) |
| `github:maggu2810/opencode-forge` | `git` | `undefined` | `git-opencode-forge-<hash>` | Clones git repo, npm subprocess | **Yes²** | Only if committed OR built by subprocess |
| `maggu2810/opencode-forge` | `git` | `undefined` | `git-opencode-forge-<hash>` | Same as `github:` | **Yes²** | Only if committed OR built by subprocess |
| `npm:opencode-forge` | `alias` | `undefined` | Not installable by `Npm` (rejected: only `version`/`range`/`tag`/`git`) | — | — | — |
| `/absolute/path`, `./relative/path`, `file://...` | `directory` | `undefined` | Not cached | No arborist install | N/A | Depends on local filesystem |

**Footnotes:**

¹ OpenCode uses `ignoreScripts: true`. For npm registry specs, this fully suppresses `prepare`. Tarball is pre-built.

² **Git specs are the exception:** OpenCode uses `ignoreScripts: true`, but pacote's `GitFetcher` spawns an npm subprocess **without** `--ignore-scripts`. If the package has `prepare`, `build`, or other lifecycle scripts, the subprocess runs `npm install` which executes `prepare` as part of the standard lifecycle. See Section 3.3.1 and Section 5.3 for details.

For which specs `opencode plugin add` accepts and how local paths are handled, when registering plugins, [read the plugin CLI guide](../plugins/oclitellmac/docs/opencode-plugin-cli.md).

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
# List all cached packages (one directory per cache key)
ls ~/.cache/opencode/npm/

# Inspect a cache key: numbered generation directories
ls -la ~/.cache/opencode/npm/opencode-forge@latest/

# Inspect an installed package in the newest generation
ls ~/.cache/opencode/npm/opencode-forge@latest/<generation>/node_modules/opencode-forge/
```

### 11.9 Test Module Resolution (Bun)

```bash
# Test if a module resolves from a given directory
bun -e "
const fromDir = '/home/user/.cache/opencode/npm/opencode-forge@latest/<generation>/node_modules/opencode-forge';
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
  '/home/user/.cache/opencode/npm/git-plugin-0123456789ab/<generation>/node_modules/@user/plugin/dist',
  '/home/user/.cache/opencode/npm/git-plugin-0123456789ab/<generation>/node_modules/@user/plugin',
  '/home/user/.cache/opencode/npm/git-plugin-0123456789ab/<generation>/node_modules',
  '/home/user/.cache/opencode/npm/git-plugin-0123456789ab/<generation>',
  '/home/user/.cache/opencode/npm',
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

- `packages/util/src/npm.ts` — `Npm` service: cache key/directory, `reify()` arborist wrapper with `ignoreScripts: true`, `add`/`resolve`/`check`/`update`/`which`
- `packages/util/src/npm-config.ts` — `@npmcli/config` loading and registry resolution
- `packages/tui/src/plugin/runtime-plugin-support.bun.ts` — `ensureRuntimePluginSupport()` call
- `packages/cli/src/commands/handlers/plugin/` — `opencode plugin` subcommand handlers

**Documentation links:**

- npm lifecycle scripts: `man npm-scripts` or https://docs.npmjs.com/cli/v10/using-npm/scripts
- arborist API: https://github.com/npm/arborist
- npm-package-arg: https://github.com/npm/npm-package-arg
- pacote: https://github.com/npm/pacote
- Bun module resolution: https://bun.sh/docs/runtime/modules

---

## 13. Quick Reference: Key Takeaways

**npm registry vs git repository installs:**

| Source         | Fetch method           | `prepare` runs?           | `dist/` included?                     |
|----------------|------------------------|---------------------------|---------------------------------------|
| npm registry   | Published tarball      | No (ignoreScripts works)  | Yes (from `files` in package.json)    |
| git repository | Clone + npm subprocess | **Yes** (subprocess)¹     | Only if committed OR built by subprocess |

¹ **Critical:** OpenCode uses `ignoreScripts: true`, but for `github:` specs, pacote's `GitFetcher` spawns an npm subprocess **without** `--ignore-scripts`. The `prepare` script executes via this subprocess, regardless of arborist's `ignoreScripts` setting.

**Why `github:` installs run scripts despite `ignoreScripts: true`:**

1. Arborist calls `pacote.extract(spec, path, { ignoreScripts: true })`
2. Pacote's `GitFetcher` clones the git repo
3. `GitFetcher.#prepareDir` checks if **any** of `postinstall`, `build`, `preinstall`, `install`, `prepack`, `prepare` exist in `scripts`
4. If **any** exist → spawns: `npm install --force --include=dev` (no `--ignore-scripts` flag)
5. npm subprocess runs `prepare` script as part of standard lifecycle
6. `DirFetcher.#prepareDir` would run `prepare` again, but skips due to `ignoreScripts: true` (already ran via subprocess)

**The actual workarounds:**

1. **Rename ALL lifecycle scripts** to avoid the `GitFetcher` trigger:
   ```json
   {
     "scripts": {
       "Xprepare": "bun run build",  // ← Renamed (not 'prepare')
       "Xbuild": "bun scripts/build.ts", // ← Renamed (not 'build')
       "Xpostinstall": "echo done"   // ← Renamed (not 'postinstall')
     }
   }
   ```
   When **all** of `postinstall`, `build`, `preinstall`, `install`, `prepack`, `prepare` are absent → npm subprocess is **never invoked** → no scripts run.

2. **Commit pre-built `dist/` to the repository** (remove from `.gitignore`):
   - Git clone includes committed files
   - Even if npm subprocess runs and fails, `dist/` is already present

3. **Publish to npm registry** (use `npm:opencode-forge` or bare name spec):
   - Registry tarballs bypass the git-specific subprocess entirely
   - `ignoreScripts: true` fully suppresses scripts for registry packages

**Why the `build` script name matters:**

The `build` script is **not** a lifecycle script (npm install does not auto-execute it). Its presence in the `GitFetcher.#prepareDir` check list determines whether to spawn the npm subprocess. If `build` exists but `prepare` does not, the subprocess still runs (installing devDeps), but no build happens. Typically, `build` and `prepare` work together:

```json
{
  "scripts": {
    "build": "tsc && bun build",
    "prepare": "npm run build"
  }
}
```

Renaming only `prepare` → `Xprepare` is insufficient if `build` still exists — the subprocess runs, but `prepare` doesn't trigger the build. Renaming **both** ensures the subprocess never runs.

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

# Install without scripts (works for registry, NOT for github: specs)
npm install --ignore-scripts <package>

# Inspect cache
ls ~/.cache/opencode/npm/

# Test resolution
bun -e "try { console.log(import.meta.resolve('@opentui/solid', '/path')) } catch(e) { console.log('failed') }"

# Verify which scripts would trigger npm subprocess (git specs only)
# Check if package.json has any of: postinstall, build, preinstall, install, prepack, prepare
cat package.json | jq '.scripts | keys[] | select(. == "postinstall" or . == "build" or . == "preinstall" or . == "install" or . == "prepack" or . == "prepare")'
```

**Source code references for the git subprocess issue:**

- `pacote v21.5.0 lib/git.js:164-171` — script existence check
- `pacote v21.5.0 lib/git.js:193` — npm subprocess spawn (no `--ignore-scripts`)
- `pacote v21.5.0 lib/fetcher.js:105-121` — `npmCliConfig` construction
- `pacote v21.5.0 lib/dir.js:35-36` — `DirFetcher` checks `ignoreScripts` (Phase 2)
- `arborist v9.4.0 lib/arborist/reify.js:704` — `pacote.extract()` call with `ignoreScripts: true`

---

**End of document.**
