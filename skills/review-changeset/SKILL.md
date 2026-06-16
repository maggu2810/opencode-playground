---
name: review-changeset
description: Review a git changeset against the project coding standard and
  conventions. Use when asked to review changes, check code quality, audit a
  commit or diff, or verify code meets the coding standard.
---

# Changeset Review

Check a git changeset against the project coding standard, conventions, and
available formatting/linting tools. Always work through the phases below in
order. Never skip a phase.

---

## Phase 0 — Coding Standard Discovery

**Do not embed or assume any coding standard.** Determine it from context first.

1. Scan the already-loaded context (AGENTS.md, `.opencode/rules/`, any docs
   already read this session) for a coding standard or conventions reference.
2. If the user's message contains a file path, URL, or description of a
   standard, use that.
3. If a reference is found by either of the above: read the referenced
   document(s), then confirm to the user:
   > "I will apply `<reference>` as the coding standard."
4. If nothing is found: use the `question` tool to ask:
   > "No coding standard reference was found in the project context.
   > Please provide a file path, URL, or description of the standard to apply."
   Wait for the user's answer before continuing.

---

## Phase 1 — Base Ref Selection

**If the user's message already contains a git ref** (commit SHA, branch name,
or tag) use it directly as `<base>` and skip to Phase 2.

**Otherwise**, build an interactive selector:

1. Run: `git log --oneline -20`
2. Prepend one synthetic entry for uncommitted changes.
3. Append one sentinel entry `[Load next 20]`.
4. Present the full list using the `question` tool (single-select):

   ```
   HEAD        uncommitted working-tree changes (staged + unstaged)
   a1b2c3d  (HEAD -> main, origin/main) fix: correct buffer overflow
   b2c3d4e  feat: add retry logic
   ...
   [Load next 20]
   ```

5. If the user picks `[Load next 20]`:
   - Increment the skip offset by 20 (first page: `--skip=20`, second: `--skip=40`, …).
   - Run: `git log --oneline --skip=<offset> -20`
   - Present a new list with the same `[Load next 20]` option appended.
     Omit `[Load next 20]` when `git log` returns fewer than 20 entries
     (history exhausted).
   - Repeat until the user selects a ref.

The selected entry's SHA, or the literal string `HEAD`, becomes `<base>`.

---

## Phase 2 — Build the Diff

Run the appropriate diff command based on `<base>`:

| `<base>` | Command |
|---|---|
| `HEAD` | `git diff HEAD` |
| any SHA | `git diff <sha>` |

Also run `git diff --name-only <base>` to obtain the changed file list.

Classify each changed file:

| Category | Extensions / Names |
|---|---|
| C/C++ | `.c` `.cpp` `.cc` `.cxx` `.h` `.hpp` `.hh` |
| CMake | `CMakeLists.txt` `*.cmake` |
| Other | everything else |

C/C++ files are candidates for clang-format and clang-tidy.
CMake files are candidates for cmake-formatter.
All files are candidates for LLM review.

---

## Phase 3 — Tool Detection and Execution

Attempt to run each tool below. For every tool that cannot run, record
`{tool, reason}` in a skip list — do not abort. All skips appear verbatim in
the Phase 5 report.

### clang-format

- **Detect:** `.clang-format` exists at repo root AND `clang-format` binary is
  reachable (`which clang-format`).
- **Run:** `clang-format --dry-run --Werror <changed-cpp-files>`
  (one invocation with all changed C/C++ files as arguments)
- **Skip reasons:** `.clang-format` absent · `clang-format` binary not found ·
  no C/C++ files changed

### clang-tidy

- **Detect:** `.clang-tidy` exists at repo root AND `clang-tidy` binary is
  reachable AND at least one `compile_commands.json` is found anywhere under
  the repo root (search with `find . -name compile_commands.json -not -path '*/\.*'`).
- **Run:** `clang-tidy -p <dir-containing-compile_commands.json> <changed-cpp-files>`
  If multiple compile DBs are found, prefer the one in a directory named
  `build`, then take the first match.
- **Skip reasons:** `.clang-tidy` absent · `clang-tidy` binary not found ·
  no `compile_commands.json` found · no C/C++ files changed

### cmake-formatter

- **Detect:** `./cmake-formatter` script exists at the repo root.
- **Run:** `./cmake-formatter --check --diff`
  This runs against all CMake files in the repo (by design). After capturing
  output, filter it to retain only sections that reference files appearing in
  the changeset file list from Phase 2.
- **Skip reasons:** `./cmake-formatter` script absent · execution error
  (capture stderr as the reason) · no CMake files changed

---

## Phase 4 — LLM Review

For each changed file, read the diff hunks and evaluate the changes against
the coding standard loaded in Phase 0.

Guidelines:

- Focus on violations detectable from the diff alone.
- Read unchanged surrounding context only when necessary to judge a violation
  (e.g. to see a class declaration for a naming violation on a member).
- For each finding, note: file, line, category, description, the specific
  section of the standard it violates, and a concrete suggested fix.
- Do not flag style issues already covered by clang-format or clang-tidy
  findings — avoid duplicates.

---

## Phase 5 — Report and Export

### Direct output (always shown in chat)

Produce the following structured report:

```
## Changeset Review
Base: <base>  →  HEAD   |   Date: YYYY-MM-DD
Files reviewed: N   |   Errors: K   |   Warnings: L   |   Skipped tools: M

────────────────────────────────────────────
### Findings

#### <path/to/file.cpp>
  [ERROR]   line 42   Naming › variables     `MyVar` must be snake_case
                      Ref: <standard-ref> §3.2   Suggestion: rename to `my_var`
  [WARNING] line 78   Formatting             Missing blank line after closing brace
                      Ref: .clang-format   Auto-fixable: clang-format

#### <CMakeLists.txt>
  [WARNING] line 12   CMake format           Indentation inconsistency
                      Ref: cmake-formatter   Auto-fixable: ./cmake-formatter

────────────────────────────────────────────
### Clean files
<file1>, <file2>, …   (or "None" if every file has findings)

────────────────────────────────────────────
### Skipped tools
  clang-tidy    no compile_commands.json found in any build directory
  …

(Omit this section entirely if no tools were skipped.)

────────────────────────────────────────────
### Verdict:  PASS | PASS WITH WARNINGS | FAIL
              (<K> errors · <L> warnings)
```

Verdict rules:
- **PASS** — zero errors, zero warnings
- **PASS WITH WARNINGS** — zero errors, one or more warnings
- **FAIL** — one or more errors

### Markdown export (optional)

After showing the direct report, ask with the `question` tool:

> "Save this review as a Markdown file?"  (Yes / No)

If **No**: done.

If **Yes**: ask a second `question`:

> "Which format?"

| Option | Description |
|---|---|
| **A — Per-file** | One `##` section per changed file, findings as a table inside. Mirrors the direct output. Good for file-by-file PR review. |
| **B — Per-category** | Top-level sections `## Naming`, `## Formatting`, `## CMake Format`, etc. Each section is a table with columns `File \| Line \| Description`. Good for seeing the full scope of one issue type across the changeset. |
| **C — Checklist** | Each finding as `- [ ] \`file:line\` — description` grouped by file under `##` headers. Paste-ready for a PR description or issue tracker. |

Write the file to:

```
<repo-root>/review-<first-7-chars-of-base-sha>-<YYYY-MM-DD>.md
```

When `<base>` is `HEAD`, use the literal string `head` in the filename:

```
<repo-root>/review-head-<YYYY-MM-DD>.md
```

---

## Error Handling Summary

| Situation | Action |
|---|---|
| Coding standard not in context and not provided | Ask via `question` tool; wait; do not proceed without an answer |
| Any tool binary missing | Record skip with reason; continue |
| Tool execution returns non-zero | Record skip with stderr as reason; continue |
| `git diff` produces no output | Report "No changes detected" and stop |
| All files are "Other" type | Skip all three tools; note in Skipped tools section |
