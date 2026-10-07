# LiteLLM Integration — Third-Party Source Map

Single source of truth for the exact commit of every third-party repository
referenced by the LiteLLM integration docs (`field-coverage-comparison.md`,
`implementation-guide.md`, `shared-pipeline-architecture.md`) and by the
`oclitellmac` plugin / `config-generator` tool implementations.

Do not copy these commit SHAs, tags, or dates into any other file. Link to
this file instead — see the
[markdown style guide](../../.agents/docs/markdown-style-guide.md) for the
single-source-of-truth convention.

## Reference commits

| Repo (submodule path) | Commit | Tag / Version | Date |
|---|---|---|---|
| `repos/opencode` | [`a1053508`](https://github.com/anomalyco/opencode/commit/a105350812f05f914c768e468559dbd6bd508d8e) | `v1.18.13` | 2026-08-04 |
| `repos/opencode-litellm@BlakeHastings` | [`311b9c36`](https://github.com/BlakeHastings/opencode-litellm/commit/311b9c36c793c268bfbf8f2700822ce5632e688b) | `master` (PR #2 merge) | 2026-04-23 |
| `repos/opencode-litellm@yuseferi` | [`f7a20e06`](https://github.com/yuseferi/opencode-litellm/commit/f7a20e06a086032b2d0c931981cd52959481d995) | `v0.8.0` | 2026-08-04 |

`oclitellmac` (`plugins/oclitellmac/`) v0.6.0 and later target the **opencode v2**
plugin API (see the v2 port section below); v0.5.x targeted opencode ≥ v1.18.13. Behavior documented for older opencode releases
(e.g. the removed `litellmProxy` option, see below) does not apply.

## Files inspected per repo

Use these paths as the starting point when re-diffing after a future
submodule bump.

### `repos/opencode` (`a1053508`, `v1.18.13`)

- `packages/core/src/v1/config/provider.ts` — `ModelConfig` / `ProviderConfig` schema (the shape written into `opencode.json` / injected by the `config` hook). Relocated here from the pre-rewrite `packages/opencode/src/config/provider.ts`; same field shape.
- `packages/core/src/config/provider.ts` — newer Effect-based v2 provider schema (not yet the config-file format; used internally / by the v2 plugin API).
- `packages/opencode/src/provider/provider.ts` — provider/model database merge logic, header/chunk timeout handling.
- `packages/opencode/src/provider/transform.ts` — request transforms gated by model config fields (`reasoning`, `interleaved`, `limit.output`, etc.).
- `packages/opencode/src/session/llm.ts` — request preparation, tool injection.
- `packages/opencode/src/session/session.ts` — cost calculation (`cost.input`/`output` treated as USD per **million** tokens, divided by `1_000_000`).
- `packages/opencode/src/plugin/index.ts` — classic (v1) plugin hook dispatch, including the `config` hook still used by `oclitellmac`.
- `packages/plugin/src/index.ts` — classic plugin `Hooks` type definitions.
- `packages/plugin/src/v2/effect/` and `packages/plugin/src/v2/promise/` — earlier layout of the Effect-based plugin API. The `oclitellmac` v2 port targets the layout listed in the v2 port section below.

### `repos/opencode-litellm@BlakeHastings` (`311b9c36`)

- `src/index.ts` — single-provider plugin using `config` + `auth` + `chat.params` hooks.

### `repos/opencode-litellm@yuseferi` (`f7a20e06`, `v0.8.0`)

- `src/plugin/index.ts` — `provider.models` (v2) hook, multi-provider support (`8d446d1`).
- `src/plugin/build-model.ts` — model entry construction, including reasoning-effort `variants` (`34db713`).
- `src/plugin/discover.ts` — model + model-info discovery.
- `src/utils/litellm-api.ts` — LiteLLM API client, `supports_reasoning_efforts` derivation.
- `src/types/index.ts` — `LiteLLMModel` / `LiteLLMModelInfo` types, including `input_cost_per_token` / `output_cost_per_token` cost fields (`907b496`).

## `oclitellmac` v2 port (`repos/opencode`)

The v2 server and TUI plugins were ported against `repos/opencode` at
[`e7a34f09`](https://github.com/anomalyco/opencode/commit/e7a34f09bfd9134dfade5a8ddb843f7030bc9a69)
(`v2.0.24`, 2026-10-06). The v1 table above still pins what the field-mapping
docs and `config-generator` were verified against.

Files inspected:

- `packages/core/src/plugin/module.ts` — server plugin module shape (`{ id, setup }`).
- `packages/plugin/src/promise/` — Promise plugin API (`ctx.provider.transform`, `ctx.session.hook`).
- `packages/tui/src/plugin/context.tsx` and `packages/plugin/src/tui/` — TUI plugin shape and context (`ctx.ui.slot`, `ctx.theme`).
- `packages/schema/src/provider.ts` and `packages/schema/src/model.ts` — `Provider.Info` / `Model.Info`.
- `packages/core/src/model.ts` and `packages/core/src/model-resolver.ts` — package resolution (`model.package ?? provider.package`), settings merge, timeouts.
- `packages/ai/src/providers/openai-compatible.ts` and `anthropic-compatible.ts` — native provider packages and their settings.
- `packages/ai/src/cache-policy.ts` — prompt-cache breakpoints are only placed on Anthropic-style routes.
- `packages/ai/src/protocols/anthropic-messages.ts` and `packages/core/src/variant.ts` — Anthropic request shape, thinking and effort variants.
- `packages/cli/src/config/` — `cli.json` (replaces `tui.json`) and service config.

## Notable upstream changes since the previous source pin

Previous pin: `repos/opencode` at `b2baddcd3` (`latest-1872-gb2baddcd3`);
`repos/opencode-litellm@yuseferi` at `9d40f3a8` (`v0.3.1`).

- **opencode**: `litellmProxy` provider option and the `_noop` tool-injection
  workaround were removed entirely (`7f7eb2e7f`, "remove LiteLLM workarounds
  ported upstream, requires LiteLLM v1.85.0-rc.2+"). The underlying
  tool-call-history validation issue was fixed natively in LiteLLM itself.
  `oclitellmac` no longer sets this option (see
  [field-coverage-comparison.md §1a](field-coverage-comparison.md)).
- **opencode**: model schema gained `status: "active"` (`00c324829`),
  `options.headerTimeout` (`f965db9e1`), widened `interleaved` field values
  (`ab701d20e`, `a1ab489e6`), and optional (independently settable)
  `modalities.input` / `modalities.output` (`0bfa55b62`).
- **opencode**: the config/provider schema relocated from
  `packages/opencode/src/config/provider.ts` to
  `packages/core/src/v1/config/provider.ts` as part of a broader
  Effect-based core rewrite; the classic `config` plugin hook and the
  `opencode.json` schema shape are unaffected.
- **yuseferi**: fixed a cost-unit bug — LiteLLM's `/v1/model/info` reports
  `input_cost_per_token` / `output_cost_per_token` in USD per single token,
  but OpenCode's `cost.input` / `cost.output` config fields are USD per
  **million** tokens. yuseferi's fix (`907b496`) multiplies by `1_000_000`
  before writing the `cost` block. `oclitellmac` and `config-generator` had
  the same bug; both are fixed to match (see
  [field-coverage-comparison.md §2a](field-coverage-comparison.md)).
- **yuseferi**: added reasoning-effort `variants` derived from LiteLLM's
  `supports_<level>_reasoning_effort` flags (`34db713`). `oclitellmac` and
  `config-generator` now populate `variants` the same way.
- **yuseferi**: added multi-provider support, matching multiple
  differently-named LiteLLM providers in one config (`8d446d1`) — already
  covered by `oclitellmac`'s multi-endpoint design; no change needed.
