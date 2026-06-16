---
name: review-changeset
description: Review a git changeset against the project coding standard and
  conventions. Use when asked to review changes, check code quality, audit a
  commit or diff, or verify code meets the coding standard.
---

# Changeset Review

Check a git changeset or the full working tree against the project coding
standard, conventions, and available formatting/linting tools. Always work
through the phases below in order. Never skip a phase.

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

## Phase 1 — Mode and Scope Selection

**If the user's message already contains a git ref** (commit SHA, branch name,
or tag) use it directly as `<base>`, set mode to **diff**, and skip to Phase 2.

**Otherwise**, present the following selector using the `question` tool
(single-select):

```
HEAD            uncommitted working-tree changes (staged + unstaged)
[Full scan]     check entire working tree — choose a directory scope next
────────────────────────────────────────────────────────────────────────
a1b2c3d  (HEAD -> main, origin/main) fix: correct buffer overflow
b2c3d4e  feat: add retry logic
c3d4e5f  chore: update dependencies
...
[Load next 20]
```

`HEAD` and `[Full scan]` are always pinned at the top, separated from the
commit list by a divider. The commit list is produced by `git log --oneline -20`.

---

### Branch A — Diff mode (`HEAD` or a commit selected)

Set `<base>` to the selected SHA, or the literal string `HEAD` if that entry
was chosen. Set mode to **diff**. Proceed to Phase 2.

**Paging:** if the user picks `[Load next 20]`, increment the skip offset by 20
and re-run `git log --oneline --skip=<offset> -20`. Present a fresh selector
with the same pinned entries at the top. Omit `[Load next 20]` when the log
returns fewer than 20 entries (history exhausted). Repeat until the user
selects a ref.

---

### Branch B — Full scan mode (`[Full scan]` selected)

Set mode to **full-scan**. Navigate to a directory scope as follows.

#### Directory tree navigation

Run `tree -d -L 1` from the repo root. If `tree` is not installed, fall back to
`find . -mindepth 1 -maxdepth 1 -type d`. Present a `question` list:

```
.                              (entire repository)
────────────────────────────────────────────────────────────────────────
./cloud-connector              [has subdirectories]
./knbase                       [has subdirectories]
./knlog
./tests
────────────────────────────────────────────────────────────────────────
[Go deeper from a subdirectory]
[Show one more level  (currently L1)]
```

Determine whether a directory has subdirectories by running
`find <dir> -mindepth 1 -maxdepth 1 -type d` for each listed entry and marking
it `[has subdirectories]` if the output is non-empty.

#### Entry behaviour

| Entry | Behaviour when selected |
|---|---|
| `.` (entire repository) | Use immediately as `<scope>` |
| Leaf directory (no marker) | Use immediately as `<scope>` |
| Non-leaf `[has subdirectories]` | Follow-up question: "Use `<dir>` as scope, or explore inside it?" |
| `[Go deeper from a subdirectory]` | Follow-up question listing only the non-leaf dirs: "Which directory to zoom into?" Re-run `tree -d -L 1` rooted at the chosen dir and present a new navigation list. |
| `[Show one more level (currently LN)]` | Re-run `tree -d -L (N+1)` from the same root. Update the label to `currently L(N+1)`. |

#### Non-leaf "Use or explore?" follow-up

When a non-leaf directory is selected:

```
You selected ./cloud-connector/src  [has subdirectories]
→ Use this as the scan scope (scans all subdirectories recursively)?
→ Explore inside it first
```

- **Use as scope** → `<scope>` is confirmed, proceed to Phase 2.
- **Explore inside** → re-run `tree -d -L 1` rooted at the selected dir,
  present a new navigation list with the same sentinel entries.

#### Scope confirmed

The scan always covers `<scope>` **fully and recursively** — there is no depth
limit on the scan itself.

---

## Phase 2 — Build the File Set

### Diff mode

Run the diff command for `<base>`:

| `<base>` | Command |
|---|---|
| `HEAD` | `git diff HEAD` |
| any SHA | `git diff <sha>` |

Also run `git diff --name-only <base>` to obtain the changed file list.

If `git diff` produces no output, report "No changes detected" and stop.

### Full-scan mode

Collect files under `<scope>` recursively:

```bash
find <scope> -type f \( \
  -name "*.cpp" -o -name "*.c" -o -name "*.cc" -o -name "*.cxx" \
  -o -name "*.h" -o -name "*.hpp" -o -name "*.hh" \
  -o -name "CMakeLists.txt" -o -name "*.cmake" \
\)
```

### File classification (both modes)

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
- **Run (diff mode):** `clang-format --dry-run --Werror <changed-cpp-files>`
- **Run (full-scan mode):** `clang-format --dry-run --Werror <all-cpp-files-in-scope>`
- **Skip reasons:** `.clang-format` absent · `clang-format` binary not found ·
  no C/C++ files in scope

### clang-tidy

- **Detect:** `.clang-tidy` exists at repo root AND `clang-tidy` binary is
  reachable AND at least one `compile_commands.json` is found anywhere under
  the repo root (`find . -name compile_commands.json -not -path '*/\.*'`).
  If multiple compile DBs are found, prefer the one in a directory named
  `build`, then take the first match.
- **Full-scan upfront warning:** before running, count the C/C++ files in scope.
  If more than 20, ask:
  > "Full scan found `<N>` C/C++ files. Running clang-tidy on all of them may
  > take several minutes. Continue with clang-tidy, or skip it for this run?"
  If the user skips, record `"clang-tidy: skipped by user (large full scan)"`.
- **Run (diff mode):** `clang-tidy -p <build-dir> <changed-cpp-files>`
- **Run (full-scan mode):** `clang-tidy -p <build-dir> <all-cpp-files-in-scope>`
- **Skip reasons:** `.clang-tidy` absent · `clang-tidy` binary not found ·
  no `compile_commands.json` found · no C/C++ files in scope ·
  skipped by user (large full scan)

### cmake-formatter

- **Detect:** `./cmake-formatter` script exists at the repo root.
- **Run:** `./cmake-formatter --check --diff`
  This runs against all CMake files in the repo by design. After capturing
  output, filter it to retain only sections that reference files appearing in
  the current file set (diff mode: changed CMake files; full-scan mode: CMake
  files under `<scope>`).
- **Skip reasons:** `./cmake-formatter` script absent · execution error
  (capture stderr as the reason) · no CMake files in scope

---

## Phase 4 — LLM Review

For each file in the current file set, read the content (diff mode: diff hunks;
full-scan mode: full file content) and evaluate it against the coding standard
loaded in Phase 0.

Guidelines:

- Focus on violations detectable from the available content.
- In diff mode, read unchanged surrounding context only when necessary to judge
  a violation (e.g. to see a class declaration for a naming violation on a
  member).
- In full-scan mode, process files one at a time and accumulate findings rather
  than loading all files at once.
- For each finding, record: file, line, category, description, the specific
  section of the standard it violates, and a concrete suggested fix.
- Do not flag style issues already covered by clang-format or clang-tidy
  findings — avoid duplicates.

---

## Phase 5 — Report and Export

### Direct output (always shown in chat)

```
## Changeset Review
Mode: Diff   Base: <base>  →  HEAD   |   Date: YYYY-MM-DD
Files reviewed: N   |   Errors: K   |   Warnings: L   |   Skipped tools: M

  (or for full-scan:)

## Changeset Review
Mode: Full scan   Scope: <scope>   |   Date: YYYY-MM-DD
Files reviewed: N   |   Errors: K   |   Warnings: L   |   Skipped tools: M

────────────────────────────────────────────────────────────────────────
### Findings

#### <path/to/file.cpp>
  [ERROR]   line 42   Naming › variables     `MyVar` must be snake_case
                      Ref: <standard-ref> §3.2   Suggestion: rename to `my_var`
  [WARNING] line 78   Formatting             Missing blank line after closing brace
                      Ref: .clang-format   Auto-fixable: clang-format

#### <CMakeLists.txt>
  [WARNING] line 12   CMake format           Indentation inconsistency
                      Ref: cmake-formatter   Auto-fixable: ./cmake-formatter

────────────────────────────────────────────────────────────────────────
### Clean files
<file1>, <file2>, …   (or "None" if every file has findings)

────────────────────────────────────────────────────────────────────────
### Skipped tools
  clang-tidy    no compile_commands.json found in any build directory

(Omit this section entirely if no tools were skipped.)

────────────────────────────────────────────────────────────────────────
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
| **A — Per-file** | One `##` section per file, findings as a table inside. Mirrors the direct output. Good for file-by-file PR review. |
| **B — Per-category** | Top-level sections `## Naming`, `## Formatting`, `## CMake Format`, etc. Each is a table with columns `File \| Line \| Description`. Good for seeing the full scope of one issue type across all files. |
| **C — Checklist** | Each finding as `- [ ] \`file:line\` — description` grouped by file under `##` headers. Paste-ready for a PR description or issue tracker. |

Write the file to `<repo-root>/` using this naming scheme:

| Mode | Filename |
|---|---|
| Diff, base = `HEAD` | `review-head-<YYYY-MM-DD>.md` |
| Diff, base = SHA | `review-<sha7>-<YYYY-MM-DD>.md` |
| Full scan, scope = `.` | `review-fullscan-root-<YYYY-MM-DD>.md` |
| Full scan, scope = `./some/dir` | `review-fullscan-<dir-slug>-<YYYY-MM-DD>.md` (strip leading `./`, replace `/` with `-`) |

---

## Error Handling Summary

| Situation | Action |
|---|---|
| Coding standard not in context and not provided | Ask via `question` tool; wait; do not proceed without an answer |
| Any tool binary missing | Record skip with reason; continue |
| Tool execution returns non-zero | Record skip with stderr as reason; continue |
| `git diff` produces no output (diff mode) | Report "No changes detected" and stop |
| `find` returns no files (full-scan mode) | Report "No reviewable files found in `<scope>`" and stop |
| All files are "Other" type | Skip all three tools; note in Skipped tools section |
