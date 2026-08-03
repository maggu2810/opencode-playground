# AGENTS.md File Conventions

## Philosophy

Keep AGENTS.md files as minimal as possible to reduce per-message token costs in OpenCode AI conversations.

## Solution

Use markdown links to reference detailed documentation on-demand:

    When working on [feature X], [read here](.agents/docs/[relevant-doc].md)

The AI will:
1. Read the minimal AGENTS.md (always loaded)
2. See the instruction
3. Call the Read tool on `.agents/docs/[relevant-doc].md` when needed
4. Load detailed context only when relevant to the current task

## Structure

### Root AGENTS.md (~80-100 lines)
- Project purpose (2-3 sentences)
- Critical constants only (API endpoints, cache paths)
- File reference instructions for everything else

### Plugin AGENTS.md (~40-60 lines each)
- Plugin purpose (2 sentences)
- Plugin type (server/TUI)
- File reference instructions to plugin docs

### Two doc directories

**`.agents/docs/`** — agent-only documentation
- Content that is only useful to AI agents
- Detailed implementation information, file maps, design decisions
- Anything an agent needs but a human would not navigate to directly

**`docs/`** — human-facing documentation
- Content that humans read in a browser or editor
- User guides, API references, tutorials, changelogs
- Also used when content is relevant to both humans and agents

**Placement rule:** if a human would benefit from reading a file, put it in `docs/`.
If only an agent needs it, put it in `.agents/docs/`. When in doubt, prefer `docs/`.

A file belongs in `docs/` if it is reachable from `README.md` by following any chain
of local markdown links (transitively). It does not need to be directly linked from
`README.md` — `README.md → A.md → B.md` makes `B.md` human-reachable.

## README structure

Many projects publish `docs/` to both GitHub and Confluence (e.g. via
[markdown-to-confluence](https://pypi.org/project/markdown-to-confluence/)).
This means `docs/README.md` is not just a docs index — it is also a
Confluence page, often carrying `<!-- confluence-page-id -->` and
`<!-- confluence-space-key -->` metadata comments. Keep the root `README.md`
and `docs/README.md` in separate roles:

**Root `README.md`** — the GitHub project landing page
- A short, generic overview (2-3 sentences)
- A link to `docs/README.md` for the full documentation
- Repository-specific content that must NOT be synced to Confluence:
  submodule/installation instructions, contribution workflow, sync
  instructions, licensing, etc.

**`docs/README.md`** — the canonical documentation hub
- The full table of contents / index for everything under `docs/`
- Synced to Confluence as the space's root page
- Contains only content relevant to the published documentation, not
  repository mechanics

### AGENTS.md must not duplicate docs/README.md routing

AGENTS.md's "File Reading Instructions" section is reserved for `.agents/docs/`
(agent-only) references. Routing into `docs/` content belongs in `docs/README.md`
only — AGENTS.md's hardened README reference already leads to `docs/README.md`,
whether directly (when `<readme-path>` is `docs/README.md`) or via the root
`README.md`, which links onward to it. A duplicate routing table in AGENTS.md's
"File Reading Instructions" section would therefore be redundant and would
drift out of sync as docs are added or renamed.

## Pattern

### Good Example

    ## File Reading Instructions

    When working on config generation or provider setup, [read here](.agents/docs/architecture.md)

    When working with API endpoints or understanding request/response schemas, [read here](.agents/docs/api-reference.md)

    For understanding design decisions (no Azure AD, Result types, etc.), [read here](.agents/docs/design-decisions.md)

### Anti-pattern

    ## Architecture

    [500 lines of implementation details here]

    ## API Reference

    [300 lines of endpoint documentation here]

## Anti-patterns to Avoid

1. **Don't duplicate content** between AGENTS.md and `.agents/docs/`
   - Extract once, reference from AGENTS.md

2. **Don't include implementation details in AGENTS.md**
   - "How to implement X" belongs in `.agents/docs/`
   - AGENTS.md should only point to the right doc

3. **Don't create catch-all documentation files**
   - Split by concern: architecture.md, api-reference.md, testing.md
   - Easier for AI to find relevant information

4. **Don't forget to update references**
   - When adding new docs, add corresponding instruction
   - Keep AGENTS.md in sync with `.agents/docs/` structure

5. **Don't put agent-only docs in `docs/`**
   - If a human has no reason to read a file, it belongs in `.agents/docs/`
   - Files in `docs/` should always be reachable from `README.md`

## Maintenance

### Adding New Agent Documentation
1. Decide: is this file useful to humans? If yes → `docs/`. If no → `.agents/docs/`.
2. Create a focused doc (e.g., `.agents/docs/caching-strategy.md`)
3. Add one-line reference in AGENTS.md:

       When working on caching or performance optimization, [read here](.agents/docs/caching-strategy.md)

### Refactoring Existing Content
1. Identify large sections in AGENTS.md (>50 lines)
2. Extract to a focused doc in `.agents/docs/` (or `docs/` if human-relevant)
3. Replace with one-line reference
4. Verify AI can find content when needed

### Verifying Effectiveness
Monitor token usage in OpenCode:
- Check token count per message (shown in UI after compaction)
- Target: 3-8k baseline, 8-15k when working on specific features
- If consistently >15k, audit AGENTS.md for unnecessary inline content
