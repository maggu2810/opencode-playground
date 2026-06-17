# [PROJECT NAME]

<!-- PLACEHOLDER: Replace with 2-3 sentences describing what this project does
     and its primary purpose. Include the main language/stack.
     Example:
     This service provides X for Y users. It is built with Go and exposes a
     REST API consumed by the Z frontend. Authentication is handled via JWT. -->

Read [project README](README.md) at the start of every session.
Its instructions are binding — follow them as if they were written in this file.

## Critical Constants

<!-- PLACEHOLDER: Add key URLs, paths, auth methods, or environment values the
     AI needs to complete tasks without asking. Remove this section if none apply.
     Example:
     - API base URL: https://api.example.com/v1
     - Config path: ~/.config/projectname/
     - Auth method: Bearer token via PROJECTNAME_API_KEY env var -->

## File Reading Instructions

When working on AGENTS.md structure or cost optimization, [read here](.agents/docs/agents-file-conventions.md)

When creating or editing any markdown file in this project, [read here](.agents/docs/markdown-style-guide.md)

<!-- PLACEHOLDER: Add references below as you create .agents/docs/ or docs/ files.
     Agent-only docs go in .agents/docs/; docs also useful to humans go in docs/.
     One instruction per doc, triggered by relevant task context.
     Examples:

     When working on architecture or system design, [read here](.agents/docs/architecture.md)

     When working on API endpoints or request/response schemas, [read here](.agents/docs/api-reference.md)

     When running or writing tests, [read here](.agents/docs/testing-guide.md)

     When understanding design decisions or rationale, [read here](.agents/docs/design-decisions.md)

     When navigating the codebase or understanding module responsibilities, [read here](.agents/docs/file-map.md) -->

When spawning subagents, include the full content of AGENTS.md in the
subagent prompt so the subagent performs the same README.md and doc
reference hops independently.
