---
name: agents-md-setup
description: Use when the user wants to set up, create, or improve AGENTS.md, .agents/docs/, or docs/ in their project. Use when asked to initialize agent instructions, reduce token costs, fix file references, or audit AGENTS.md health.
---

# AGENTS.md Setup

Templates are bundled next to this skill file. Read them when needed:
- AGENTS.md template: [read here](template-AGENTS.md)
- Conventions template: [read here](template-agents-file-conventions.md)
- Markdown style guide template: [read here](template-markdown-style-guide.md)

## Directory model

Two entry points, two doc directories:

| Entry point | Audience | Linked doc directory |
|---|---|---|
| `AGENTS.md` | AI agents | `.agents/docs/` |
| `README.md` | Humans | `docs/` |

Placement rule for every `.md` file other than `AGENTS.md` and `README.md`:

- **Human-reachable** (reachable from `README.md` by following any chain of local
  markdown links) → belongs in `docs/`
- **Agent-reachable only** (reachable from `AGENTS.md` but not from `README.md`) →
  belongs in `.agents/docs/`
- **Reachable from both** → belongs in `docs/`

A file does not need to be directly linked from `README.md` to be human-reachable.
`README.md → A.md → B.md` makes `B.md` human-reachable through `A.md`.

## Step 1 — Assess the project

Check all of the following before taking any action:
- Does `AGENTS.md` exist in the project root?
- Does `README.md` exist in the project root?
- Does `.agents/docs/agents-file-conventions.md` exist?
- Does `.agents/docs/markdown-style-guide.md` exist?
- List all `.md` files under `docs/` and `.agents/docs/`

## Step 2 — New project (no AGENTS.md)

- Create `AGENTS.md` from the AGENTS.md template
- Create `.agents/docs/agents-file-conventions.md` from the conventions template
- Create `.agents/docs/markdown-style-guide.md` from the markdown style guide template

Do not create any files under `docs/` — that is the human's responsibility.

## Step 3 — Existing AGENTS.md, missing agent docs

For each missing file in `.agents/docs/`:
- Create it from the corresponding template
- Check if `AGENTS.md` already links to it with a trigger condition
- If the link is missing, add it following the pattern:
  `When [relevant context], [read here](.agents/docs/filename.md)`

## Step 4 — Both AGENTS.md and agent docs exist

For each existing file in `.agents/docs/`:
- Diff it against the corresponding template
- If differences exist, present them clearly to the user and ask:
  1. Keep existing
  2. Replace with template
  3. Merge manually (show the user both versions side by side)

Always check `AGENTS.md` links to all `.agents/docs/` files with a trigger condition.
Add any missing links.

## Step 5 — Health checks (always run after Steps 2-4)

Run these checks on `AGENTS.md`, `README.md`, all files in `docs/`, and all files
in `.agents/docs/` every time:

1. **Stale references** — find any `[read here](path/X.md)` or similar where the
   target file does not actually exist. Warn the user for each one.

2. **Missing trigger conditions** — find any file reference link that is not
   preceded by a trigger condition on the same line. Example of the problem:
   `[read here](.agents/docs/architecture.md)`
   Example of correct form:
   `When working on architecture or system design, [read here](.agents/docs/architecture.md)`
   Suggest a trigger condition for each bare link found.

3. **Old @ref syntax** — scan `AGENTS.md` and all files in `docs/` and `.agents/docs/`
   for any occurrence of the pattern `@filename` or `Read @` used as a file reference.
   Suggest replacing with `[descriptive text](path)` per the markdown style guide.

4. **Size warning** — if `AGENTS.md` exceeds 100 lines, warn the user and identify
   any inline section larger than 50 lines as a candidate for extraction to
   `.agents/docs/`.

5. **Reachability and placement check** — determine whether each doc file is
   human-reachable (from `README.md`) or agent-reachable (from `AGENTS.md`) using
   the following grep-based graph traversal. No file content needs to be fully read
   — only link targets need to be extracted.

   **Algorithm:**
   a. List all `.md` files under `docs/` and `.agents/docs/`.
   b. For every `.md` file in the project (including `AGENTS.md` and `README.md`),
      grep for local markdown link targets: pattern `\]\(([^)]+\.md)\)`.
      Build an adjacency map: file → list of files it links to.
   c. From `README.md`, follow the adjacency map transitively (BFS/DFS) to build
      the **human-reachable set**.
   d. From `AGENTS.md`, follow the adjacency map transitively to build the
      **agent-reachable set**.
   e. Apply placement rules to each doc file:

   | Location | Human-reachable | Agent-reachable | Verdict |
   |---|---|---|---|
   | `docs/` | yes | any | Correct |
   | `docs/` | no | yes | Suggest moving to `.agents/docs/` |
   | `docs/` | no | no | Warn: orphaned (referenced by nothing) |
   | `.agents/docs/` | no | yes | Correct |
   | `.agents/docs/` | yes | any | Suggest moving to `docs/` |
   | `.agents/docs/` | no | no | Warn: orphaned (referenced by nothing) |

   Report all misplaced and orphaned files to the user with the suggested action.

6. **Duplication detection** — scan all files in `docs/` and `.agents/docs/` for
   section headings that appear in more than one file. Flag each duplicate heading
   as a candidate for consolidation: extract to the most appropriate single file
   and replace the duplicate with a link.
