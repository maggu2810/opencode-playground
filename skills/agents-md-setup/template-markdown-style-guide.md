# Markdown Style Guide

## Philosophy

Markdown files in this project are written for two audiences: humans reading
in a browser or editor, and AI agents reading raw text in a context window.
Conventions should serve both equally.

## Single Source of Truth

Every piece of information lives in exactly one file. All other files that
need it link to it — they never copy it.

### Rules

1. **No copy-paste between files** — if the same content appears in two files,
   extract it to the most appropriate file and link from the other.

2. **Link, don't repeat** — when file B needs content from file A, reference
   it with a trigger condition and a markdown link. Do not reproduce the
   content inline.

3. **Canonical home rule** — before writing a new section, ask: does this
   content belong here, or does it belong in an existing focused file that
   should be linked to instead?

4. **AI generation guidance** — when generating or expanding documentation,
   scan existing `docs/` files first. Link to relevant existing content rather
   than regenerating similar content inline. Duplication created by AI is
   harder for humans to detect and keep in sync than duplication written
   manually.

### Why this matters

Duplicated content drifts. When one copy is updated, the other is typically
not. This is especially problematic in AI-assisted projects where multiple
sessions may each update a different copy without awareness of the other.
A single source of truth means there is only one place to update, and only
one place that can become stale.

## File References

Always use markdown link syntax for file references. Never use bare `@ref` syntax.

### Rule

```markdown
When [trigger condition], [descriptive text](path/to/file.md)
```

### Good examples

```markdown
When working on architecture or system design, [read here](docs/architecture.md)

When creating or editing any markdown file in this project, [read here](docs/markdown-style-guide.md)
```

### Bad examples

```markdown
Read @docs/architecture.md

For architecture see @docs/architecture.md

[read here](docs/architecture.md)
← missing trigger condition; the agent has no signal for when to load this
```

### Rules for the trigger condition
- Always on the same line as the link
- Start with `When ...` or `For ...`
- Be specific enough that the agent loads the file only when relevant
- Do not repeat the filename in the trigger text if the link text is already clear

### Rules for the link text
- `[read here]` is the default for instruction-style references
- Use descriptive text if it adds clarity beyond what the trigger already says
- Never use the raw filename as link text — the path already contains that information

## Code Blocks

Always use fenced triple-backtick code blocks. Never use indented code blocks.

```bash
# correct
echo "hello"
```

Do not use four-space indentation as a code block substitute.

## Further Reading

When working on AGENTS.md structure or cost optimization, [read here](.agents/docs/agents-file-conventions.md)
