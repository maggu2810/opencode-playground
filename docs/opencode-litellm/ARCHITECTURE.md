# OpenCode × LiteLLM — Shared Architecture

This document describes the shared pipeline architecture used by both the `config-generator` Python tool and the `oclitellmac-server` TypeScript plugin.

---

## Design Philosophy

Both implementations follow the same modular pipeline design to ensure:
1. **Consistency**: Identical model configurations regardless of implementation
2. **Maintainability**: Changes to one implementation can be mirrored in the other
3. **Testability**: Each stage can be tested independently
4. **Clarity**: Pipeline stages have clear, single responsibilities

---

## Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                       INPUT: LiteLLM Proxy                      │
│                    /public/model_hub + /v1/model/info           │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
                    ┌─────────┐
                    │  FETCH  │  HTTP client, endpoint abstraction
                    └────┬────┘
                         │ hubEntries[], infoMap{}
                         ▼
                  ┌─────────────┐
                  │ CATEGORIZE  │  Determine model type (chat, embedding, etc.)
                  └──────┬──────┘
                         │ categories: Map<modelId, Category>
                         ▼
                    ┌─────────┐
                    │   MAP   │  Field mapping (LiteLLM → OpenCode)
                    └────┬────┘
                         │ flags, modalities, cost, limit
                         ▼
                   ┌──────────┐
                   │  BUILD   │  Construct ModelConfig objects
                   └─────┬────┘
                         │ models: Record<modelId, ModelConfig>
                         ▼
                   ┌──────────┐
                   │  FILTER  │  Generate blacklist for non-chat models
                   └─────┬────┘
                         │ blacklist: [modelId, category][]
                         ▼
              ┌────────────────────────┐
              │  TRANSFORM / RENDER    │  Output stage (differs by impl)
              └────────┬───────────────┘
                       │
        ┌──────────────┴───────────────┐
        │                              │
        ▼                              ▼
  ┌──────────┐                  ┌──────────┐
  │  Python  │                  │TypeScript│
  │  JSONC   │                  │  Inject  │
  │  Output  │                  │  Config  │
  └──────────┘                  └──────────┘
```

---

## Stage 1: FETCH

**Purpose**: Retrieve model data from LiteLLM proxy endpoints

### Python (`src/fetch.py`)
```python
def fetch_model_hub(base_url: str, timeout: float) -> list[dict[str, Any]]
def fetch_model_info(base_url: str, bearer: str, timeout: float) -> dict[str, dict[str, Any]]
```

### TypeScript (`src/fetch.ts`)
```typescript
class LiteLLMClient {
  async fetchModelHub(): Promise<ModelHubEntry[]>
  async fetchModelInfo(): Promise<Record<string, ModelInfoEntry["model_info"]>>
}
```

### Endpoints Used

| Endpoint | Auth | Response | Purpose |
|----------|------|----------|---------|
| `/public/model_hub` | None | `ModelHubEntry[]` | Basic model list (always queried) |
| `/v1/model/info` | Bearer | `{"data": [{"key", "model_info": {...}}]}` | Detailed capabilities/costs (optional) |

### Field Priority

When both endpoints provide the same field:
1. **Prefer `/v1/model/info`** (more detailed, requires auth)
2. **Fallback to `/public/model_hub`** (basic info, no auth)

---

## Stage 2: CATEGORIZE

**Purpose**: Classify models by type (chat, embedding, TTS, image gen, etc.)

### Python (`src/categorize.py`)
```python
def categorize_model(name: str, mode: str = "") -> str
```

### TypeScript (`src/categorize.ts`)
```typescript
function categorizeModel(name: string, mode: string = ""): Category
```

### Detection Logic

```
1. Check API `mode` field (most reliable source)
   mode="embedding" → "embedding"
   mode="audio_speech" → "audio_speech"
   mode="audio_transcription" → "transcription"
   mode="image_generation" → "image_generation"
   mode="rerank" → "ranking"
   ... etc.

2. Fallback to name heuristics (when mode absent/unknown)
   name.includes("embedding") → "embedding"
   name.includes("tts") || name.includes("chirp") → "audio_speech"
   name.includes("whisper") → "transcription"
   name.includes("dall-e") → "image_generation"
   ... etc.

3. Default to "chat" (conservative fallback)
```

### Categories

| Category | Description | Examples |
|----------|-------------|----------|
| `chat` | Chat completion models | `gpt-4`, `claude-3-opus`, `llama-3-70b` |
| `embedding` | Text embedding models | `text-embedding-ada-002`, `text-embedding-3-large` |
| `audio_speech` | Text-to-speech (TTS) | `tts-1`, `tts-1-hd` |
| `transcription` | Speech-to-text (STT) | `whisper-1` |
| `image_generation` | Image generation | `dall-e-3`, `stable-diffusion-xl` |
| `video_generation` | Video generation | Model-specific |
| `ocr` | Document analysis / OCR | Model-specific |
| `ranking` | Reranking models | Model-specific |
| `router` | Model routing / moderation | Model-specific |

---

## Stage 3: MAP

**Purpose**: Transform LiteLLM fields to OpenCode `ModelConfig` structure

### Python (`src/map.py`)
```python
def map_flags(hub: dict, info: dict) -> dict[str, bool]
def map_modalities(hub: dict, info: dict) -> dict[str, list[str]]
def map_cost(hub: dict, info: dict) -> dict[str, Any] | None
def map_limit(hub: dict, info: dict) -> dict[str, Any] | None
```

### TypeScript (`src/map.ts`)
```typescript
function mapFlags(hub: AnyRecord, info: AnyRecord): Record<string, boolean>
function mapModalities(hub: AnyRecord, info: AnyRecord): { input: string[]; output: string[] }
function mapCost(hub: AnyRecord, info: AnyRecord): AnyRecord | null
function mapLimit(hub: AnyRecord, info: AnyRecord): AnyRecord | null
```

### Field Mappings

#### Capability Flags
| OpenCode Field | LiteLLM Source (hub or info) | Fallback |
|----------------|------------------------------|----------|
| `tool_call` | `supports_function_calling` OR `supports_parallel_function_calling` | `false` |
| `attachment` | `supports_vision` | `false` |
| `reasoning` | `supports_reasoning` | `false` |
| `temperature` | - | `true` (all chat models) |

#### Modalities
| Modality | LiteLLM Source | Notes |
|----------|----------------|-------|
| `modalities.input: ["text"]` | - | Always present |
| `modalities.input: ["image"]` | `supports_vision` | Hub or info |
| `modalities.input: ["audio"]` | `supports_audio_input` | Info only |
| `modalities.input: ["pdf"]` | `supports_pdf_input` | Info only |
| `modalities.output: ["text"]` | - | Always present |
| `modalities.output: ["audio"]` | `supports_audio_output` | Info only |

#### Cost Structure
```typescript
{
  input: number,                    // Required (input_cost_per_token)
  output: number,                   // Required (output_cost_per_token)
  cache_read?: number,              // Optional (cache_read_input_token_cost)
  cache_write?: number,             // Optional (cache_creation_input_token_cost)
  context_over_200k?: {             // Optional (above_128k / above_200k fields)
    input: number,
    output: number
  }
}
```

#### Token Limits
```typescript
{
  context: number,    // max_input_tokens
  input: number,      // max_input_tokens (same as context)
  output: number      // max_output_tokens or max_tokens
}
```

---

## Stage 4: BUILD

**Purpose**: Construct complete `ModelConfig` objects for each model

### Python (`src/build.py`)
```python
def build_model_entry(hub: dict, info: dict, category: str) -> dict[str, Any]
```

### TypeScript (`src/build.ts`)
```typescript
function buildModelEntry(hub: AnyRecord, info: AnyRecord, category: Category): AnyRecord
```

### Output Structure

```typescript
{
  id: string,                          // model_group
  name: string,                        // model_group (display name)
  tool_call?: true,                    // Only if true
  attachment?: true,                   // Only if true
  reasoning?: true,                    // Only if true
  temperature: true,                   // Always present
  modalities: {                        // Always present
    input: string[],
    output: string[]
  },
  cost?: { ... },                      // Only if input/output available
  limit?: { ... }                      // Only if context/output available
}
```

**Design Note**: False/empty values are omitted to keep configs minimal and readable.

---

## Stage 5: FILTER

**Purpose**: Generate blacklist for non-chat models based on enabled categories

### Python (`src/filter.py`)
```python
def build_blacklist(
  categories: dict[str, str],
  enabled_categories: set[str]
) -> list[tuple[str, str]]
```

### TypeScript (`src/filter.ts`)
```typescript
function buildBlacklist(
  categories: Map<string, Category>,
  enabledCategories: Set<Category>
): Array<[string, Category]>
```

### Filtering Rules

```
For each model:
  IF category IN NON_CHAT_CATEGORIES:
    IF category NOT IN enabledCategories:
      ADD to blacklist
  ELSE:
    NEVER blacklist (chat models always enabled)
```

### Blacklist Format

Returned as `[modelId, category]` pairs, grouped by category:

```python
[
  ("text-embedding-ada-002", "embedding"),
  ("text-embedding-3-large", "embedding"),
  ("dall-e-3", "image_generation"),
  ...
]
```

Stable ordering ensures consistent output across runs.

---

## Stage 6: TRANSFORM / RENDER

**Purpose**: Final output stage (differs between implementations)

### Python (`src/render.py`) - Static JSONC Output

```python
def render_jsonc(
  base_url: str,
  models_by_id: dict[str, dict],
  categories: dict[str, str],
  enabled_categories: set[str],
  provider_name: str,
  provider_key: str
) -> str
```

**Output**:
```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "litellm": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "LiteLLM",
      "options": {
        "baseURL": "https://litellm.example.com/v1",
        "litellmProxy": true
      },
      "blacklist": [
        // embedding model — not used by opencode
        "text-embedding-ada-002",
        // image generation model — not used by opencode
        "dall-e-3"
      ],
      "models": { ... }
    }
  }
}
```

### TypeScript (`src/transform.ts`) - Runtime Config Injection

```typescript
function transformModels(
  hubEntries: ModelHubEntry[],
  infoMap: Record<string, any>
): {
  models: Record<string, any>,
  categories: Map<string, Category>
}
```

**Then in `index.ts`**:
```typescript
const { models, categories } = transformModels(hubEntries, infoMap)
const blacklist = buildBlacklist(categories, enabledCategories)

opcodeConfig.provider[providerKey] = {
  npm: "@ai-sdk/openai-compatible",
  name: providerName,
  key: apiKey,
  options: { baseURL, apiKey, litellmProxy: true },
  blacklist: blacklist.map(([id]) => id),
  models
}
```

---

## Consistency Guarantees

Both implementations produce **identical results** for:

✅ **Category Detection**
- Same `mode` → category mappings
- Same name heuristics
- Same "chat" fallback

✅ **Field Mappings**
- Same capability flag logic
- Same modality detection
- Same cost/limit extraction
- Same field priority (info > hub)

✅ **Blacklist Generation**
- Same filtering rules
- Same stable ordering

✅ **Model Configurations**
- Same field structure
- Same omission rules (false/empty values)
- Same default values

### Verification

To verify consistency, compare outputs:

```bash
# Python tool
python -m src.generate --base-url https://litellm.example.com --output python-output.jsonc

# TypeScript plugin (check cached data)
cat ~/.local/state/oclitellmac/providers/litellm-example.json

# Compare model configs (should be identical)
```

---

## Extension Points

To add a new field mapping:

1. **Update `map.py` / `map.ts`**:
   ```python
   def map_new_field(hub: dict, info: dict) -> Any:
       return get_first((info, "new_field"), (hub, "new_field"))
   ```

2. **Update `build.py` / `build.ts`**:
   ```python
   new_field = map_new_field(hub, info)
   if new_field is not None:
       model["new_field"] = new_field
   ```

3. **Update both implementations** to maintain consistency

4. **Add tests** (Python: pytest, TypeScript: bun:test)

---

## Performance Characteristics

### Fetch Stage
- **Time**: 1-3s per endpoint (network latency)
- **Optimization**: Parallel fetching of `/public/model_hub` and `/v1/model/info`

### Categorize + Map + Build
- **Time**: <50ms for 100 models
- **Complexity**: O(n) where n = number of models

### Filter
- **Time**: <10ms for 100 models
- **Complexity**: O(n log n) due to sorting

### Total Pipeline
- **Python**: ~2-4s (network + processing)
- **TypeScript**: ~2-4s (network + processing) + caching layer

---

## Error Handling

### Network Errors
- Timeout after 30s (configurable)
- Python: Logs warning, returns empty list
- TypeScript: Falls back to cached data (if enabled)

### Missing Fields
- Cost/limit omitted if required fields missing
- Modalities fall back to `["text"]` defaults
- Capability flags default to `false`

### Invalid Categories
- Unknown `mode` values fall back to name heuristics
- Unrecognized names default to "chat" (safe fallback)

---

## Future Enhancements

### Potential Additions
1. **Video Input Modality**: When LiteLLM adds `supports_video_input`
2. **PDF Output Modality**: When models support PDF generation
3. **Custom Category Definitions**: User-defined category mappings
4. **Field Validation**: JSON Schema validation for output
5. **Incremental Updates**: Delta-based config updates

### Compatibility Notes
- Backward compatible with existing configs
- New fields are optional (omitted when unavailable)
- Category system is extensible (new categories can be added)

---

*Last updated: May 2026*  
*Verified against: Python `src/*.py` and TypeScript `src/*.ts` (modular architecture)*
