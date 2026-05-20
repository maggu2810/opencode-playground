---
name: agents-md-setup
description: Use when the user wants to set up, create, or improve AGENTS.md, docs/agents-file-conventions.md, or docs/markdown-style-guide.md in their project. Use when asked to initialize agent instructions, reduce token costs, fix file references, or audit AGENTS.md health.
---

# AGENTS.md Setup

Templates are bundled next to this skill file. Read them when needed:
- AGENTS.md template: [read here](template-AGENTS.md)
- Conventions template: [read here](template-agents-file-conventions.md)
- Markdown style guide template: [read here](template-markdown-style-guide.md)

## Step 1 — Assess the project

Check all of the following before taking any action:
- Does `AGENTS.md` exist in the project root?
- Does `docs/agents-file-conventions.md` exist?
- Does `docs/markdown-style-guide.md` exist?

## Step 2 — New project (no AGENTS.md)

- Create `AGENTS.md` from the AGENTS.md template
- Create `docs/agents-file-conventions.md` from the conventions template
- Create `docs/markdown-style-guide.md` from the markdown style guide template

## Step 3 — Existing AGENTS.md, missing docs files

For each missing file in `docs/`:
- Create it from the corresponding template
- Check if `AGENTS.md` already links to it with a trigger condition
- If the link is missing, add it following the pattern:
  `When [relevant context], [read here](docs/filename.md)`

## Step 4 — Both AGENTS.md and docs files exist

For each existing file in `docs/`:
- Diff it against the corresponding template
- If differences exist, present them clearly to the user and ask:
  1. Keep existing
  2. Replace with template
  3. Merge manually (show the user both versions side by side)

Always check `AGENTS.md` links to all docs files with a trigger condition.
Add any missing links.

## Step 5 — Health checks (always run after Steps 2-4)

Run these checks on `AGENTS.md` and all files in `docs/` every time:

1. **Stale references** — find any `[read here](docs/X.md)` or similar where
   `docs/X.md` does not actually exist. Warn the user for each one.

2. **Missing trigger conditions** — find any file reference link that is not
   preceded by a trigger condition on the same line. Example of the problem:
   `[read here](docs/architecture.md)`
   Example of correct form:
   `When working on architecture or system design, [read here](docs/architecture.md)`
   Suggest a trigger condition for each bare link found.

3. **Old @ref syntax** — scan `AGENTS.md` and all files in `docs/` for any
   occurrence of the pattern `@filename` or `Read @` used as a file reference.
   Suggest replacing with `[descriptive text](path)` per the markdown style guide.

4. **Size warning** — if `AGENTS.md` exceeds 100 lines, warn the user and
   identify any inline section larger than 50 lines as a candidate for
   extraction to `docs/`.

5. **Undocumented docs files** — list any `.md` file found in `docs/` that has
   no corresponding reference in `AGENTS.md`. Ask the user if a reference
   should be added.

6. **Duplication detection** — scan all files in `docs/` for section headings
   that appear in more than one file. Flag each duplicate heading as a
   candidate for consolidation: extract to the most appropriate single file
   and replace the duplicate with a link.
