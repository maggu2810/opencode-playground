# opencode-litellm Plugin Fields Documentation

## Overview

The `opencode-litellm` plugin auto-discovers models from a LiteLLM proxy and makes them available in OpenCode without manual configuration.

**API Endpoints Used:**
- `GET /v1/models` - Lists available model IDs
- `GET /v1/model/info` - (Not used by plugin) Returns detailed model metadata including costs, context limits, capabilities

**LiteLLM Model Hub:**
- `GET /public/model_hub` - Returns list of public model groups with metadata
- `GET /public/model_hub/info` - Returns hub metadata (docs title, version, useful links)

---

## 1. Provider Fields Comparison

| Field Path | OpenCode Uses For | Plugin Sets | Value |
|------------|-------------------|-------------|-------|
| `provider.litellm` | Provider key | ✓ | Dynamic key "litellm" |
| `npm` | AI SDK package selection | ✓ | `"@ai-sdk/openai-compatible"` |
| `name` | Display name in UI (/connect) | ✓ | `"LiteLLM"` |
| `options.baseURL` | API endpoint for requests | ✓ | `${rootURL}/v1` |
| `options.apiKey` | Authentication header | ✓ (if stored) | From auth.json |
| `options.enterpriseUrl` | Enterprise OAuth flow | ✗ | - |
| `options.setCacheKey` | Enable request caching | ✗ | - |
| `options.timeout` | Request timeout (default: 300000ms) | ✗ | - |
| `options.chunkTimeout` | Chunked response timeout | ✗ | - |
| `options.*` | Provider-specific options | ✗ | - |
| `env` | Environment variable names to check for API key | ✗ | - |
| `whitelist` | Allowed model IDs filter | ✗ | - |
| `blacklist` | Disallowed model IDs filter | ✗ | - |
| `models` | Available models map | ✓ (partial) | Record with id/name only |

### Provider Summary

| Status | Count |
|--------|-------|
| ✓ Set by plugin | 4 |
| ✗ Missing from plugin | 9 |
| Total OpenCode provider fields | 13 |

---

## 2. Model Fields Comparison

| Field Path | OpenCode Uses For | Plugin Sets | Value |
|------------|-------------------|-------------|-------|
| `models.*.id` | Unique model identifier | ✓ | LiteLLM model ID |
| `models.*.name` | Display name in model picker | ✓ | LiteLLM model ID |
| `models.*.family` | Model family grouping | ✗ | - |
| `models.*.release_date` | Release date info | ✗ | - |
| `models.*.attachment` | File attachment support | ✗ | - |
| `models.*.reasoning` | Reasoning/thinking support | ✗ | - |
| `models.*.temperature` | Temperature parameter support | ✗ | - |
| `models.*.tool_call` | Tool calling support | ✗ | - |
| `models.*.interleaved` | Interleaved reasoning content | ✗ | - |
| `models.*.cost.input` | Input cost calculation | ✗ | - |
| `models.*.cost.output` | Output cost calculation | ✗ | - |
| `models.*.cost.cache_read` | Cache read cost | ✗ | - |
| `models.*.cost.cache_write` | Cache write cost | ✗ | - |
| `models.*.cost.context_over_200k` | Extended context cost | ✗ | - |
| `models.*.limit.context` | Maximum context window size | ✗ | - |
| `models.*.limit.input` | Maximum input tokens | ✗ | - |
| `models.*.limit.output` | Maximum output tokens | ✗ | - |
| `models.*.modalities.input[]` | Supported input types (text/audio/image/video/pdf) | ✗ | - |
| `models.*.modalities.output[]` | Supported output types (text/audio/image/video/pdf) | ✗ | - |
| `models.*.status` | Model availability (alpha/beta/deprecated/active) | ✗ | - |
| `models.*.options.*` | Provider-specific model options | ✗ | - |
| `models.*.headers.*` | Custom request headers | ✗ | - |
| `models.*.provider.npm` | Override AI SDK package | ✗ | - |
| `models.*.provider.api` | Override API endpoint | ✗ | - |
| `models.*.variants.*` | Variant-specific configurations | ✗ | - |

### Model Summary

| Status | Count |
|--------|-------|
| ✓ Set by plugin | 2 |
| ✗ Missing from plugin | 23 |
| Total OpenCode model fields | 25 |

---

## 3. LiteLLM API → OpenCode Field Mapping

### 3.1 LiteLLM Endpoints

| Endpoint | Used by Plugin | Description |
|----------|----------------|-------------|
| `GET /v1/models` | ✓ Yes | Returns model list (id, object, created, owned_by) |
| `GET /v1/model/info` | ✗ No | Returns detailed metadata (costs, limits, capabilities) |
| `GET /public/model_hub` | ✗ No | Public model hub with model group metadata |
| `GET /public/model_hub/info` | ✗ No | Hub metadata (docs title, version, useful links) |

### 3.2 GET /v1/models Response Fields

| LiteLLM Field | OpenCode Mapping | Plugin Uses |
|---------------|------------------|-------------|
| `data[].id` | `models.*.id` | ✓ Yes |
| `data[].object` | - | ✗ No |
| `data[].created` | - | ✗ No |
| `data[].owned_by` | - | ✗ No |

### 3.3 GET /v1/model/info Response Fields

The `/v1/model/info` endpoint returns `model_info` for each model:

| LiteLLM Field | OpenCode Mapping | Description |
|---------------|------------------|-------------|
| `model_name` | `models.*.name` | Display name |
| `key` | `models.*.id` | Model identifier |
| `max_tokens` | `models.*.limit.output` | Max output tokens |
| `max_input_tokens` | `models.*.limit.context` | Max context (when input==context) |
| `max_output_tokens` | `models.*.limit.output` | Max output tokens |
| `input_cost_per_token` | `models.*.cost.input` | Cost per input token |
| `output_cost_per_token` | `models.*.cost.output` | Cost per output token |
| `cache_read_input_token_cost` | `models.*.cost.cache_read` | Cache read cost |
| `cache_creation_input_token_cost` | `models.*.cost.cache_write` | Cache write cost |
| `input_cost_per_token_above_128k_tokens` | `models.*.cost.context_over_200k.input` | Extended context input cost |
| `output_cost_per_token_above_128k_tokens` | `models.*.cost.context_over_200k.output` | Extended context output cost |
| `litellm_provider` | - | Source provider (informational) |
| `mode` | - | "chat" or "completion" (informational) |
| `supports_system_messages` | `models.*.options.supports_system_messages` | System message support |
| `supports_vision` | `models.*.capabilities.input.image` | Vision/image input |
| `supports_function_calling` | `models.*.capabilities.toolcall` | Tool calling |
| `supports_prompt_caching` | - | Cache support indicator |
| `supports_audio_input` | `models.*.capabilities.input.audio` | Audio input |
| `supports_audio_output` | `models.*.capabilities.output.audio` | Audio output |
| `supports_pdf_input` | `models.*.capabilities.input.pdf` | PDF input |
| `supports_reasoning` | `models.*.capabilities.reasoning` | Reasoning support |

### 3.4 GET /public/model_hub Response Fields

The `/public/model_hub` endpoint returns `ModelGroupInfoProxy` with aggregated model group metadata:

| LiteLLM Field | OpenCode Mapping | Description |
|---------------|------------------|-------------|
| `model_group` | `models.*.id` | Model group name (e.g., "gpt-4") |
| `providers` | - | List of provider names supporting this model |
| `max_input_tokens` | `models.*.limit.context` | Maximum context window |
| `max_output_tokens` | `models.*.limit.output` | Maximum output tokens |
| `input_cost_per_token` | `models.*.cost.input` | Cost per input token |
| `output_cost_per_token` | `models.*.cost.output` | Cost per output token |
| `input_cost_per_pixel` | - | Image input cost per pixel |
| `mode` | - | "chat", "embedding", "completion", etc. |
| `tpm` | - | Tokens per minute limit |
| `rpm` | - | Requests per minute limit |
| `supports_parallel_function_calling` | `models.*.capabilities.toolcall` | Parallel tool calling |
| `supports_vision` | `models.*.capabilities.input.image` | Vision/image input |
| `supports_web_search` | - | Web search capability |
| `supports_url_context` | - | URL context capability |
| `supports_reasoning` | `models.*.capabilities.reasoning` | Reasoning support |
| `supports_function_calling` | `models.*.capabilities.toolcall` | Tool/function calling |
| `supported_openai_params` | - | List of supported OpenAI params |
| `is_public_model_group` | - | Whether model is in public hub |
| `health_status` | - | "healthy", "unhealthy", "unknown" |
| `health_response_time` | - | Response time in milliseconds |
| `health_checked_at` | - | ISO timestamp of last health check |

### 3.5 GET /public/model_hub/info Response Fields

| LiteLLM Field | Description |
|---------------|-------------|
| `docs_title` | Title for the model hub documentation |
| `custom_docs_description` | Custom description for docs |
| `litellm_version` | LiteLLM proxy version |
| `useful_links` | Dictionary of helpful links (display name → URL or {url, index}) |

### 3.6 LiteLLM → OpenCode Field Mapping Table

| OpenCode Field | LiteLLM Source Field | Endpoint |
|----------------|---------------------|----------|
| `models.*.id` | `key` or `id` or `model_group` | `/v1/models`, `/v1/model/info`, `/public/model_hub` |
| `models.*.name` | `model_name` or `model_group` | `/v1/model/info`, `/public/model_hub` |
| `models.*.limit.output` | `max_tokens`, `max_output_tokens` | `/v1/model/info`, `/public/model_hub` |
| `models.*.limit.context` | `max_input_tokens` | `/v1/model/info`, `/public/model_hub` |
| `models.*.limit.input` | `max_input_tokens` | `/v1/model/info`, `/public/model_hub` |
| `models.*.cost.input` | `input_cost_per_token` | `/v1/model/info`, `/public/model_hub` |
| `models.*.cost.output` | `output_cost_per_token` | `/v1/model/info`, `/public/model_hub` |
| `models.*.cost.cache_read` | `cache_read_input_token_cost` | `/v1/model/info` |
| `models.*.cost.cache_write` | `cache_creation_input_token_cost` | `/v1/model/info` |
| `models.*.cost.context_over_200k.input` | `input_cost_per_token_above_128k_tokens` | `/v1/model/info` |
| `models.*.cost.context_over_200k.output` | `output_cost_per_token_above_128k_tokens` | `/v1/model/info` |
| `models.*.capabilities.input.image` | `supports_vision` | `/v1/model/info`, `/public/model_hub` |
| `models.*.capabilities.input.audio` | `supports_audio_input` | `/v1/model/info` |
| `models.*.capabilities.input.pdf` | `supports_pdf_input` | `/v1/model/info` |
| `models.*.capabilities.toolcall` | `supports_function_calling`, `supports_parallel_function_calling` | `/v1/model/info`, `/public/model_hub` |
| `models.*.capabilities.reasoning` | `supports_reasoning` | `/v1/model/info`, `/public/model_hub` |

---

## 4. SDK Type References

### Provider Type (Runtime)
Source: `@opencode-ai/sdk` → `packages/sdk/js/src/v2/gen/types.gen.ts`

```typescript
export type Provider = {
  id: string                          // Required
  name: string                        // Required
  source: "env" | "config" | "custom" | "api"  // Required
  env: Array<string>                  // Required
  key?: string                        // Optional
  options: { [key: string]: unknown } // Required
  models: { [key: string]: Model }    // Required
}
```

### ProviderConfig (User Config)
Source: `@opencode-ai/sdk` → `packages/sdk/js/src/v2/gen/types.gen.ts`

```typescript
export type ProviderConfig = {
  api?: string
  name?: string
  env?: Array<string>
  id?: string
  npm?: string
  whitelist?: Array<string>
  blacklist?: Array<string>
  options?: {
    apiKey?: string
    baseURL?: string
    enterpriseUrl?: string
    setCacheKey?: boolean
    timeout?: number | false
    chunkTimeout?: number
    [key: string]: unknown
  }
  models?: { [key: string]: ModelConfig }
}
```

### Model Type (Runtime)
Source: `@opencode-ai/sdk` → `packages/sdk/js/src/v2/gen/types.gen.ts`

```typescript
export type Model = {
  id: string
  providerID: string
  api: { id: string; url: string; npm: string }
  name: string
  family?: string
  capabilities: {
    temperature: boolean
    reasoning: boolean
    attachment: boolean
    toolcall: boolean
    input: { text: boolean; audio: boolean; image: boolean; video: boolean; pdf: boolean }
    output: { text: boolean; audio: boolean; image: boolean; video: boolean; pdf: boolean }
    interleaved: boolean | { field: "reasoning_content" | "reasoning_details" }
  }
  cost: {
    input: number
    output: number
    cache: { read: number; write: number }
    experimentalOver200K?: { input: number; output: number; cache: { read: number; write: number } }
  }
  limit: { context: number; input?: number; output: number }
  status: "alpha" | "beta" | "deprecated" | "active"
  options: { [key: string]: unknown }
  headers: { [key: string]: string }
  release_date: string
  variants?: { [key: string]: { [key: string]: unknown } }
}
```

### ModelConfig (User Config)
Source: `@opencode-ai/sdk` → `packages/sdk/js/src/v2/gen/types.gen.ts`

```typescript
models?: {
  [key: string]: {
    id?: string
    name?: string
    family?: string
    release_date?: string
    attachment?: boolean
    reasoning?: boolean
    temperature?: boolean
    tool_call?: boolean
    interleaved?: true | { field: "reasoning_content" | "reasoning_details" }
    cost?: {
      input: number
      output: number
      cache_read?: number
      cache_write?: number
      context_over_200k?: { input: number; output: number; cache: { read: number; write: number } }
    }
    limit?: {
      context: number
      input?: number
      output: number
    }
    modalities?: {
      input: Array<"text" | "audio" | "image" | "video" | "pdf">
      output: Array<"text" | "audio" | "image" | "video" | "pdf">
    }
    experimental?: boolean
    status?: "alpha" | "beta" | "deprecated"
    provider?: { npm?: string; api?: string }
    options?: { [key: string]: unknown }
    headers?: { [key: string]: string }
    variants?: { [key: string]: { disabled?: boolean; [key: string]: unknown } }
  }
}
```

### LiteLLM ModelGroupInfo Type
Source: `litellm/types/router.py`

```python
class ModelGroupInfo(BaseModel):
    model_group: str
    providers: List[str]
    max_input_tokens: Optional[float] = None
    max_output_tokens: Optional[float] = None
    input_cost_per_token: Optional[float] = None
    output_cost_per_token: Optional[float] = None
    input_cost_per_pixel: Optional[float] = None
    mode: Optional[Literal["chat", "embedding", "completion", "image_generation",
                           "audio_transcription", "rerank", "moderations"]] = "chat"
    tpm: Optional[int] = None
    rpm: Optional[int] = None
    supports_parallel_function_calling: bool = False
    supports_vision: bool = False
    supports_web_search: bool = False
    supports_url_context: bool = False
    supports_reasoning: bool = False
    supports_function_calling: bool = False
    supported_openai_params: Optional[List[str]] = []

class ModelGroupInfoProxy(ModelGroupInfo):
    is_public_model_group: bool = False
    health_status: Optional[str] = None
    health_response_time: Optional[float] = None
    health_checked_at: Optional[str] = None
```

---

## 5. Plugin Hooks Reference

### auth Hook
The plugin registers an `auth` hook with:
- `provider: "litellm"` - Targets the litellm provider
- `loader` - Reads stored credentials from auth.json
- `methods` - Single "api" type method with baseURL prompt

### chat.params Hook
Injects `litellm_session_id` via `providerOptions.litellm` for LiteLLM admin UI session grouping.

### config Hook
- Reads auth from auth.json (key, metadata.baseURL)
- Falls back to opencode.json for baseURL
- Injects runtime provider with placeholder model
- Calls `GET /v1/models` to discover actual models

---

## 6. File Paths

| Path | Purpose |
|------|---------|
| `~/.config/opencode/opencode.json` | OpenCode config (provider definitions) |
| `~/.local/share/opencode/auth.json` | OpenCode auth store (API keys, metadata) |

---

## 7. Recommended LiteLLM Endpoints for Full Field Coverage

Based on available LiteLLM endpoints and OpenCode model fields, here's the recommended approach:

### Best Option: `/v1/model/info`
- Provides comprehensive model metadata including costs, limits, capabilities
- Use `GET /v1/model/info?model_info_fields=key,mode,max_tokens,...` (LiteLLM v1.74.3+)
- Single request per proxy startup

### Alternative: `/public/model_hub`
- Aggregated data per model group
- Includes health check status
- Less granular than `/v1/model/info` but public access (no auth required in some configs)

### Recommended Data Sources by OpenCode Field

| OpenCode Field | Recommended Source | LiteLLM Field |
|----------------|-------------------|---------------|
| `models.*.id` | `/v1/model/info` | `key` |
| `models.*.name` | `/v1/model/info` | `model_name` |
| `models.*.cost.input` | `/v1/model/info` or `/public/model_hub` | `input_cost_per_token` |
| `models.*.cost.output` | `/v1/model/info` or `/public/model_hub` | `output_cost_per_token` |
| `models.*.cost.cache_read` | `/v1/model/info` | `cache_read_input_token_cost` |
| `models.*.cost.cache_write` | `/v1/model/info` | `cache_creation_input_token_cost` |
| `models.*.limit.context` | `/v1/model/info` or `/public/model_hub` | `max_input_tokens` |
| `models.*.limit.output` | `/v1/model/info` or `/public/model_hub` | `max_output_tokens` or `max_tokens` |
| `models.*.capabilities.input.image` | `/v1/model/info` or `/public/model_hub` | `supports_vision` |
| `models.*.capabilities.toolcall` | `/v1/model/info` or `/public/model_hub` | `supports_function_calling` |
| `models.*.capabilities.reasoning` | `/v1/model/info` or `/public/model_hub` | `supports_reasoning` |
| `models.*.capabilities.input.audio` | `/v1/model/info` | `supports_audio_input` |
| `models.*.capabilities.input.pdf` | `/v1/model/info` | `supports_pdf_input` |

---

## Summary: Plugin vs Full Field Coverage

| Category | Fields Set | Fields Missing | Coverage |
|----------|-----------|----------------|----------|
| Provider | 4 | 9 | 31% |
| Model | 2 | 23 | 8% |
| **Total** | **6** | **32** | **16%** |

The plugin only extracts `id` and `name` from LiteLLM. To achieve full field coverage, use LiteLLM's `/v1/model/info` endpoint which provides costs, limits, and capability information.

---

*Documentation generated for opencode-litellm plugin analysis.*
*LiteLLM API reference: https://docs.litellm.ai/docs/proxy/model_management*
*LiteLLM Model Hub: https://docs.litellm.ai/docs/proxy/ai_hub*