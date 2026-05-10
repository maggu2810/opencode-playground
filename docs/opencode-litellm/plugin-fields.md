# OpenCode × LiteLLM — Field Coverage Reference

Verified against the OpenCode source tree (`repos/opencode/`, branch `dev`).
Three implementations are compared:

| Label | What it is |
|---|---|
| **BlakeHastings** | `repos/opencode-litellm@BlakeHastings/src/index.ts` — v1 plugin API, `config` + `auth` + `chat.params` hooks |
| **yuseferi** | `repos/opencode-litellm@yuseferi/src/plugin/` — v2 plugin API, `provider.models` hook |
| **playground-gen** | `tools/config-generator/src/generate.py` — generates static `opencode.jsonc` for one configurable provider |

---

## 1. Provider-level fields

Source of truth: `packages/opencode/src/config/provider.ts` (`Info` schema, L71–108).

| Field | OpenCode uses it for | BlakeHastings | yuseferi | playground-gen |
|---|---|---|---|---|
| `npm` | Selects the AI SDK adapter package | `"@ai-sdk/openai-compatible"` | `"@ai-sdk/openai-compatible"` (chat) / `"@ai-sdk/openai"` (responses) | `"@ai-sdk/openai-compatible"` |
| `name` | Display name in UI | `"LiteLLM"` | not set¹ | configurable via `--provider-name` |
| `options.baseURL` | API endpoint for all requests | `${rootURL}/v1` | read from provider config or env | `${base_url}/v1` |
| `options.apiKey` | Bearer token sent with every request | injected at runtime from auth store | read from provider config or `LITELLM_API_KEY` env | **omitted** — user sets it |
| `options.litellmProxy` | Enables stub-tool injection for LiteLLM compatibility (`llm.ts` L203–206) | **not set** | **not set** | `true` |
| `options.timeout` | Request timeout (default 300 000 ms) | **not set** | **not set** | **not set** |
| `options.chunkTimeout` | SSE chunk timeout | **not set** | **not set** | **not set** |
| `options.setCacheKey` | Enable `promptCacheKey` per-session | **not set** | **not set** | **not set** |
| `options.transport` | yuseferi routing policy (`auto`/`chat`/`responses`) | n/a | read from provider config | n/a |
| `options.responsesApiModels` | yuseferi explicit allowlist for Responses API | n/a | read from provider config | n/a |
| `options.chatApiModels` | yuseferi explicit denylist for Responses API | n/a | read from provider config | n/a |
| `api` | Override API URL entirely | **not set** | **not set** | **not set** |
| `id` | Provider identifier override | **not set** | **not set** | **not set** |
| `env` | Env var names OpenCode checks for the API key | **not set** | **not set** | **not set** |
| `whitelist` | Restrict visible models to a named subset | **not set** | **not set** | **not set** |
| `blacklist` | Hide specific models from the model picker | **not set** | **not set** | set — non-chat model IDs by default; see §4 |
| `models` | Per-model config overrides | set (see §2) | set dynamically via `provider.models` hook | set statically in JSONC |

¹ yuseferi's `LiteLLMPlugin` and `LiteLLMResponsesPlugin` use the `provider.models` hook — the provider shell (`npm`, `name`, `options.*`) must be declared by the user in their own `opencode.json`. The plugin only populates the `models` map.

### LiteLLM detection: `litellmProxy` vs provider-ID heuristic

`llm.ts` (L203–206) treats a request as coming from a LiteLLM proxy when **any** of these is true:

```
item.options?.["litellmProxy"] === true
input.model.providerID.toLowerCase().includes("litellm")
input.model.api.id.toLowerCase().includes("litellm")
```

BlakeHastings and yuseferi rely on the `providerID` heuristic (`"litellm"` / `"litellm-responses"`) instead of setting the flag. playground-gen uses the explicit `litellmProxy: true` option, which works with **any** provider key name.

---

## 2. Model-level fields

Two distinct schemas exist and must not be confused:

| Schema | Location | Used by |
|---|---|---|
| **`ModelConfig`** (user config) | `config/provider.ts` `Model` schema (L5–69) | Written into `opencode.jsonc` / injected by `config` hook. OpenCode merges this over the runtime model. |
| **`ModelsDev.Model`** (runtime / models.dev) | `provider/models.ts` `Model` schema (L27–78) | The full runtime model object. Populated from `models.dev` API, then overridden by `ModelConfig`. |
| **`Provider.Model`** (V2 plugin return type) | `@opencode-ai/sdk/v2` `Model` type | Returned by `provider.models` hook. This **is** the runtime model — it must be complete. |

The yuseferi plugin builds `Provider.Model` objects directly (see `build-model.ts`). The other two write `ModelConfig` objects into the config file which OpenCode merges on top of models.dev data.

### 2a. `ModelConfig` fields (config file / config hook)

Source: `config/provider.ts` L5–69.

| Field | Runtime effect | BlakeHastings | yuseferi¹ | playground-gen |
|---|---|---|---|---|
| `id` | Model identifier sent to the API | **not set** | set to LiteLLM model id | set to `model_group` |
| `name` | Display name in model picker | set to LiteLLM model id | set via `formatModelName()` | set to `model_group` |
| `family` | Model family grouping | **not set** | **not set** | **not set** |
| `release_date` | Used by `transform.ts` for reasoning-effort date gating | **not set** | `""` (hardcoded) | **not set** |
| `tool_call` | `transform.ts`: controls whether tools are offered | **not set** | set (`supports_function_calling`) | set when truthy |
| `attachment` | `transform.ts` `unsupportedParts`: gates image/file pass-through | **not set** | set (`supports_vision`) | set when truthy |
| `reasoning` | `transform.ts` `variants()`: enables reasoning-effort variants; `options()`: enables thinking config | **not set** | `false` (hardcoded) | set when truthy |
| `temperature` | `llm.ts` L171: gates whether temperature is sent to the API | **not set** | `true` (hardcoded) | `true` always |
| `interleaved` | `transform.ts` `normalizeMessages()` L306–337: routes reasoning text to provider-specific field | **not set** | **not set** | **not set** |
| `cost.input` | Cost display; token-spend tracking | **not set** | `0` (hardcoded) | set from hub or model/info |
| `cost.output` | Cost display; token-spend tracking | **not set** | `0` (hardcoded) | set from hub or model/info |
| `cost.cache_read` | Cache read cost display | **not set** | **not set** | set from `/v1/model/info` if `--bearer` |
| `cost.cache_write` | Cache write cost display | **not set** | **not set** | set from `/v1/model/info` if `--bearer` |
| `cost.context_over_200k.input` | Extended-context tier cost display | **not set** | **not set** | set from model/info (`above_128k`) or hub (`above_200k`) |
| `cost.context_over_200k.output` | Extended-context tier cost display | **not set** | **not set** | set from model/info (`above_128k`) or hub (`above_200k`) |
| `limit.context` | Context window; compaction trigger | **not set** | set (`max_input_tokens ?? 0`) | set from hub or model/info |
| `limit.input` | Input token limit | **not set** | set (`max_input_tokens`) | set (same as context) |
| `limit.output` | `transform.ts` `maxOutputTokens()` L1281: caps output tokens per request; `variants()` L858–866: Anthropic thinking budget | **not set** | set (`max_output_tokens ?? 0`) | set from hub or model/info |
| `modalities.input` | `transform.ts` `unsupportedParts()` L393–428: substitutes error text for unsupported file types | **not set** | **not set**² | set (`text` always; `image`/`audio`/`pdf` from capability flags) |
| `modalities.output` | (informational) | **not set** | **not set**² | set (`text` always; `audio` from model/info) |
| `experimental` | (reserved for future use) | **not set** | **not set** | **not set** |
| `status` | UI badge (alpha/beta/deprecated) | **not set** | **not set** | **not set** |
| `options` | Per-model provider options bag | **not set** | `{}` (hardcoded) | **not set** |
| `headers` | Per-model custom HTTP headers | **not set** | `{}` (hardcoded) | **not set** |
| `variants` | Reasoning-effort variants (low/medium/high/…) | **not set** | **not set** | **not set** |
| `provider.npm` | Override AI SDK package per model | **not set** | **not set** | **not set** |
| `provider.api` | Override API URL per model | **not set** | **not set** | **not set** |

¹ yuseferi writes `Provider.Model` (the V2 runtime type) — not `ModelConfig`. The fields listed above are the `Provider.Model` equivalents. yuseferi's `capabilities` sub-object is in the **runtime** shape, not the config-file shape, and OpenCode accepts it because the plugin returns it via the `provider.models` hook directly into the runtime model registry.

² yuseferi uses `capabilities.input` / `capabilities.output` (the V2 runtime struct) instead of the `modalities` config key. Both express the same intent but through different code paths.

### 2b. `Provider.Model` / V2 runtime capabilities (yuseferi only)

`build-model.ts` populates the runtime `capabilities` struct directly:

| Capability field | Source | Value |
|---|---|---|
| `capabilities.temperature` | hardcoded | `true` |
| `capabilities.reasoning` | hardcoded | `false` — **always disabled** regardless of model |
| `capabilities.attachment` | `supports_vision \|\| type === 'audio'` | boolean |
| `capabilities.toolcall` | `supports_function_calling` | boolean |
| `capabilities.input.text` | hardcoded | `true` |
| `capabilities.input.audio` | `type === 'audio'` (name heuristic) | boolean |
| `capabilities.input.image` | `supports_vision` | boolean |
| `capabilities.input.video` | hardcoded | `false` |
| `capabilities.input.pdf` | hardcoded | `false` — always, no LiteLLM source used |
| `capabilities.output.text` | `type !== 'image'` | boolean |
| `capabilities.output.audio` | hardcoded | `false` |
| `capabilities.output.image` | `type === 'image'` | boolean |
| `capabilities.output.video` | hardcoded | `false` |
| `capabilities.output.pdf` | hardcoded | `false` |
| `capabilities.interleaved` | hardcoded | `false` — **schema-invalid for `ModelConfig`**; valid for V2 runtime type |
| `cost.input` / `cost.output` | hardcoded | `0` |
| `cost.cache.read` / `cost.cache.write` | hardcoded | `0` |
| `limit.context` | `max_input_tokens ?? 0` from `/v1/models` | number |
| `limit.input` | `max_input_tokens` | number \| undefined |
| `limit.output` | `max_output_tokens ?? 0` from `/v1/models` | number |
| `status` | hardcoded | `"active"` |

---

## 3. LiteLLM API endpoints used

| Endpoint | Auth | Response shape | BlakeHastings | yuseferi | playground-gen |
|---|---|---|---|---|---|
| `GET /v1/models` | optional Bearer | `{"data": [{"id": "…", …}]}` | ✓ primary source | ✓ primary source | — |
| `GET /public/model_hub` | none | plain JSON array of `ModelGroupInfoProxy` | — | — | ✓ primary source |
| `GET /v1/model/info` | Bearer required | `{"data": [{"key":"…","model_info":{…}}]}` | — | — | ✓ optional (`--bearer`) |
| `GET /public/model_hub/info` | none | hub metadata | — | — | — |

### Fields from `GET /v1/models` — used by BlakeHastings and yuseferi

| LiteLLM field | BlakeHastings maps to | yuseferi maps to |
|---|---|---|
| `data[].id` | `models.<id>.id` + `models.<id>.name` | `Model.id` + `Model.name` (via `formatModelName`) |
| `data[].mode` | — | `categorizeModel()` → `capabilities.*` modality |
| `data[].max_input_tokens` | — | `limit.context` + `limit.input` |
| `data[].max_output_tokens` | — | `limit.output` |
| `data[].supports_function_calling` | — | `capabilities.toolcall` |
| `data[].supports_vision` | — | `capabilities.attachment` + `capabilities.input.image` |
| `data[].litellm_provider` | — | `extractModelOwner()` (display only) |

### Fields from `GET /public/model_hub` — used by playground-gen

| LiteLLM field | playground-gen maps to |
|---|---|
| `model_group` | model key + `id` + `name` |
| `mode` | category detection → blacklist membership |
| `max_input_tokens` | `limit.context` + `limit.input` |
| `max_output_tokens` | `limit.output` |
| `input_cost_per_token` | `cost.input` |
| `output_cost_per_token` | `cost.output` |
| `cache_read_input_token_cost` | `cost.cache_read` (fallback if model/info absent) |
| `cache_creation_input_token_cost` | `cost.cache_write` (fallback if model/info absent) |
| `input_cost_per_token_above_200k_tokens` | `cost.context_over_200k.input` |
| `output_cost_per_token_above_200k_tokens` | `cost.context_over_200k.output` |
| `supports_function_calling` | `tool_call` |
| `supports_parallel_function_calling` | `tool_call` (OR'd with above) |
| `supports_vision` | `attachment` + `modalities.input: ["image"]` |
| `supports_reasoning` | `reasoning` |
| `supports_web_search` | — |
| `supports_url_context` | — |
| `health_status` | — |
| `tpm` / `rpm` | — |
| `providers` | — |

### Fields from `GET /v1/model/info` — used by playground-gen only (requires `--bearer`)

Each item in `data[]` has a nested `model_info` sub-object. All fields below live **inside `model_info`**, not at the top level of the array item.

| LiteLLM field (inside `model_info`) | playground-gen maps to |
|---|---|
| `max_input_tokens` | `limit.context` + `limit.input` (preferred over hub) |
| `max_output_tokens` | `limit.output` (preferred over hub) |
| `max_tokens` | `limit.output` (fallback alias) |
| `input_cost_per_token` | `cost.input` (preferred over hub) |
| `output_cost_per_token` | `cost.output` (preferred over hub) |
| `cache_read_input_token_cost` | `cost.cache_read` |
| `cache_creation_input_token_cost` | `cost.cache_write` |
| `input_cost_per_token_above_128k_tokens` | `cost.context_over_200k.input` |
| `output_cost_per_token_above_128k_tokens` | `cost.context_over_200k.output` |
| `supports_vision` | `attachment` + `modalities.input: ["image"]` (confirms hub value) |
| `supports_function_calling` | `tool_call` (confirms hub value) |
| `supports_reasoning` | `reasoning` (confirms hub value) |
| `supports_audio_input` | `modalities.input: ["audio"]` — **only available from this endpoint** |
| `supports_audio_output` | `modalities.output: ["audio"]` — **only available from this endpoint** |
| `supports_pdf_input` | `modalities.input: ["pdf"]` — **only available from this endpoint** |
| `supports_prompt_caching` | — |
| `supports_system_messages` | — |
| `litellm_provider` | — |
| `mode` | — |

---

## 4. Non-chat model handling

Non-chat models (embedding, TTS, image generation, etc.) clutter the model picker
and are not useful for code-assistance chat. Each implementation handles them
differently:

| Behaviour | BlakeHastings | yuseferi | playground-gen |
|---|---|---|---|
| Detects non-chat models | no | yes — `categorizeModel()` on `mode` + id heuristics | yes — `_mode_to_category()` on `mode` field, name heuristics as fallback |
| Strategy for non-chat models | no filtering — all models active | no filtering — all models active (embedding/image/audio included) | provider-level `blacklist` array |
| All model data preserved | yes | yes | yes — all models in `models` block with full metadata |
| Granularity of opt-in | n/a | n/a | per-category CLI flags: `--enable-embedding`, `--enable-audio-speech`, `--enable-transcription`, `--enable-image-generation`, `--enable-video-generation`, `--enable-ocr`, `--enable-ranking`, `--enable-all` |

### How the playground-gen blacklist works

All models — chat and non-chat — are written as active entries in the `"models"`
block with full cost, limit, and capability metadata. Non-chat models whose
category is not opted-in are additionally listed in the provider-level
`"blacklist"` array, which causes OpenCode to hide them from the model picker
(`provider.ts` L1373–1377) while leaving their data intact for reference.

Each category group in the blacklist is preceded by a JSONC comment explaining
why those models are hidden:

```jsonc
"blacklist": [
  // embedding model — not used by opencode
  "text-embedding-ada-002",
  "text-embedding-3-large",
  // image generation model — not used by opencode
  "dall-e-3"
],
```

To enable a category, pass `--enable-<category>` when generating the config —
those model IDs are then omitted from the blacklist. `--enable-all` suppresses
the `blacklist` key entirely. The user can also manually remove IDs from the
blacklist in the generated file without regenerating it.

---

## 5. Auth and provider-setup flow

| Aspect | BlakeHastings | yuseferi | playground-gen |
|---|---|---|---|
| Auth mechanism | Full `/connect litellm` UI: `auth` hook with `loader` + `authorize` method. Stores API key + `baseURL` in `~/.local/share/opencode/auth.json`. | Reads `options.apiKey` from provider config or `LITELLM_API_KEY` / `LITELLM_MASTER_KEY` env. No `/connect` flow. | `--bearer TOKEN` arg for `/v1/model/info`. API key not written to config. |
| Provider discovery | Reads `auth.json`, falls back to `opencode.json`. Default: `http://localhost:4000`. | Reads `options.baseURL` from provider config, then auto-detects `localhost:4000`, `:8000`, `:8080`. | `--base-url` required argument. |
| Config written at runtime | `config` hook writes `provider.litellm` into `opencode.json` on every startup. | `provider.models` hook returns model map; user must declare provider shell in `opencode.json`. | Static `opencode.jsonc` file; must re-run script to update. |
| Multiple providers | Single `litellm` provider. | `litellm` + optional `litellm-responses` for OpenAI reasoning-tier routing. | Single provider; key and name configurable. |
| Session ID tagging | Yes — `chat.params` hook injects `litellm_session_id` into `providerOptions.litellm`. | No (noted as roadmap item). | n/a |

---

## 6. Runtime effects of model fields

Exact locations in the OpenCode source where each field is read and what effect it has.

| Field | File + line | Effect |
|---|---|---|
| `capabilities.temperature` | `llm.ts` L171–173 | If `false`, temperature is never sent; agent/model temperature settings are ignored |
| `capabilities.reasoning` | `transform.ts` `variants()` L630; `options()` L1102 | If `false`, no reasoning-effort variants are generated; no `thinkingConfig` injected for Google |
| `capabilities.attachment` | `transform.ts` `unsupportedParts()` L418 | If `false`, image/file parts in user messages are replaced with an error-text message |
| `capabilities.input.*` | `transform.ts` `unsupportedParts()` L418 | Per-modality gate: `image`, `audio`, `video`, `pdf` checked individually against attached file MIME type |
| `capabilities.interleaved` | `transform.ts` `normalizeMessages()` L306–337 | If `{ field: "reasoning_content" \| "reasoning_details" }`, reasoning text is extracted from assistant messages and injected as a provider option under that field name |
| `capabilities.toolcall` | (not gated in source — tools are always offered) | Informs OpenCode UI; not used as a request gate |
| `limit.output` | `transform.ts` `maxOutputTokens()` L1281 | `min(limit.output, 32 000)` caps `maxOutputTokens` on every request |
| `limit.output` | `transform.ts` `variants()` L858–866 | Anthropic `thinking.budgetTokens` = `min(31 999, limit.output − 1)` |
| `limit.output` | `transform.ts` `options()` L1120 | Kimi-k2 on Anthropic SDK: `thinking.budgetTokens` = `min(16 000, floor(limit.output / 2 − 1))` |
| `release_date` | `transform.ts` `openaiReasoningEfforts()` L583–584 | Date-gates whether `none` and `xhigh` reasoning effort tiers are offered for OpenAI models |
| `api.npm` | `transform.ts` throughout | Selects provider-specific message transforms, caching strategy, providerOptions key name |
| `api.id` | `transform.ts` throughout | Selects model-specific transforms (Claude tool-call ID scrubbing, Deepseek reasoning injection, etc.) |
| `options` (per-model) | `llm.ts` L141 | Merged into request options; can override provider-level options per model |
| `headers` (per-model) | `llm.ts` L387 | Merged into HTTP headers on every request to this model |
| `variants` (per-model) | `llm.ts` L130–133 | Selected by user's variant choice at session start; merged into request options |
| `modalities.input` | `transform.ts` `unsupportedParts()` L418 | Same gate as `capabilities.input.*` — only one of the two schemas is present depending on whether the model came from config or models.dev |

---

## 7. Coverage summary

### Provider fields

| Field | Any source sets it? | Gap |
|---|---|---|
| `npm` | all three | — |
| `name` | BlakeHastings, playground-gen | yuseferi requires user to set it |
| `options.baseURL` | all three | — |
| `options.apiKey` | BlakeHastings (runtime injection), yuseferi (runtime read) | playground-gen intentionally omits — user provides |
| `options.litellmProxy` | playground-gen | BlakeHastings/yuseferi rely on providerID heuristic instead |
| `options.timeout` / `chunkTimeout` | none | all three implementations |
| `env` | none | all three implementations |
| `whitelist` | none | all three implementations |
| `blacklist` | playground-gen (non-chat filtering) | BlakeHastings, yuseferi |

### Model fields

| Field | BlakeHastings | yuseferi | playground-gen | Remaining gap |
|---|---|---|---|---|
| `id` | — | ✓ | ✓ | BlakeHastings |
| `name` | ✓ | ✓ | ✓ | — |
| `tool_call` / `toolcall` | — | ✓ | ✓ | BlakeHastings |
| `attachment` | — | ✓ | ✓ | BlakeHastings |
| `reasoning` | — | ✗ hardcoded `false` | ✓ | BlakeHastings, yuseferi |
| `temperature` | — | ✓ | ✓ | BlakeHastings |
| `interleaved` | — | — | — | all three |
| `cost.input` / `cost.output` | — | ✗ hardcoded `0` | ✓ | BlakeHastings, yuseferi |
| `cost.cache_read` / `cost.cache_write` | — | — | ✓ (with `--bearer`) | BlakeHastings, yuseferi |
| `cost.context_over_200k` | — | — | ✓ (with `--bearer`) | BlakeHastings, yuseferi |
| `limit.context` | — | ✓ | ✓ | BlakeHastings |
| `limit.output` | — | ✓ | ✓ | BlakeHastings |
| `modalities.input` / `output` | — | ✓ (via V2 capabilities) | ✓ | BlakeHastings |
| `release_date` | — | ✗ empty string | — | all three (affects reasoning variant date gating) |
| `status` | — | ✓ (`"active"`) | — | BlakeHastings, playground-gen |
| `family` | — | — | — | all three |
| `variants` | — | — | — | all three (auto-generated by OpenCode from `reasoning` + `api.npm`) |
| `headers` | — | ✗ empty object | — | BlakeHastings, playground-gen |

---

*Sources verified directly from: `packages/opencode/src/config/provider.ts`, `src/provider/models.ts`, `src/provider/transform.ts`, `src/session/llm.ts` (OpenCode `dev` branch, `repos/opencode/`); `repos/opencode-litellm@BlakeHastings/src/index.ts`; `repos/opencode-litellm@yuseferi/src/plugin/build-model.ts`, `discover.ts`, `index.ts`, `utils/`; `tools/config-generator/src/generate.py`.*
