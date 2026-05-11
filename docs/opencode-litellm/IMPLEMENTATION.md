# OpenCode × LiteLLM — Implementation Guide (Agent-Focused)

This document provides implementation guidance for AI agents working on the `config-generator` Python tool and `oclitellmac-server` TypeScript plugin.

---

## Quick Reference

### File Locations
```
tools/config-generator/src/
├── generate.py         # CLI orchestration (236 lines)
├── fetch.py           # HTTP client (60 lines)
├── categorize.py      # Category detection (75 lines)
├── map.py             # Field mapping (178 lines)
├── build.py           # Model builder (47 lines)
├── filter.py          # Blacklist generation (38 lines)
└── render.py          # JSONC output (117 lines)

plugins/oclitellmac-server/src/
├── index.ts           # Plugin entry (186 lines)
├── config.ts          # Zod schemas (60 lines)
├── fetch.ts           # HTTP client (140 lines)
├── categorize.ts      # Category detection (100 lines)
├── map.ts             # Field mapping (198 lines)
├── build.ts           # Model builder (52 lines)
├── filter.ts          # Blacklist generation (58 lines)
├── transform.ts       # Pipeline orchestration (44 lines)
├── budget.ts          # Budget tracking (86 lines)
└── state.ts           # File-based state (85 lines)
```

### Running Tests
```bash
# Python (imports only - no pytest suite yet)
cd tools/config-generator
python -c "from src.generate import main; print('OK')"

# TypeScript (type checking)
cd plugins/oclitellmac-server
npx tsc --noEmit --skipLibCheck
```

---

## Module Consistency Rules

**CRITICAL**: When updating field mappings, category detection, or blacklist logic, you MUST update BOTH Python and TypeScript implementations to maintain consistency.

### Adding a New Category

**Step 1**: Update category definitions (BOTH)

**Python** (`src/categorize.py`):
```python
NON_CHAT_CATEGORIES: frozenset[str] = frozenset({
    "embedding",
    "audio_speech",
    # ... existing categories
    "new_category",  # ADD HERE
})

CATEGORY_LABEL: dict[str, str] = {
    # ... existing labels
    "new_category": "Human-readable label",  # ADD HERE
}

def _mode_to_category(mode: str) -> str | None:
    mapping: dict[str, str] = {
        # ... existing mappings
        "new_mode": "new_category",  # ADD HERE if API provides mode
    }
    return mapping.get(mode)

def categorize_model(name: str, mode: str = "") -> str:
    # ... existing logic
    if "new-pattern" in n:  # ADD name heuristic if needed
        return "new_category"
    return "chat"
```

**TypeScript** (`src/categorize.ts`):
```typescript
export const NON_CHAT_CATEGORIES = new Set([
  "embedding",
  // ... existing categories
  "new_category",  // ADD HERE
] as const);

export type Category =
  | "chat"
  // ... existing categories
  | "new_category";  // ADD HERE

export const CATEGORY_LABEL: Record<string, string> = {
  // ... existing labels
  new_category: "Human-readable label",  // ADD HERE
};

function modeToCategory(mode: string): Category | null {
  const mapping: Record<string, Category> = {
    // ... existing mappings
    new_mode: "new_category",  // ADD HERE if API provides mode
  };
  return mapping[mode] ?? null;
}

export function categorizeModel(name: string, mode: string = ""): Category {
  // ... existing logic
  if (n.includes("new-pattern")) {  // ADD name heuristic if needed
    return "new_category";
  }
  return "chat";
}
```

**Step 2**: Update config schema (TypeScript only)

**TypeScript** (`src/config.ts`):
```typescript
const CategorySchema = z.enum([
  "embedding",
  // ... existing categories
  "new_category",  // ADD HERE
])
```

**Step 3**: Update CLI flags (Python only)

**Python** (`src/generate.py`):
```python
cat_group.add_argument(
    "--enable-new-category", action="store_true",
    help="Enable new category models",
)

# In main():
if args.enable_new_category: enabled_categories.add("new_category")
```

**Step 4**: Update documentation (ALL)
- `docs/opencode-litellm/plugin-fields.md` §4 (category table)
- `plugins/oclitellmac-server/README.md` (category filtering section)
- `plugins/oclitellmac-server/config-example.json` (category reference)
- `tools/config-generator/README.md` (category filtering table)

### Adding a New Field Mapping

**Example**: Adding `supports_streaming` flag

**Step 1**: Update map module (BOTH)

**Python** (`src/map.py`):
```python
def map_flags(hub: dict[str, Any], info: dict[str, Any]) -> dict[str, bool]:
    # ... existing flags
    streaming = bool(
        hub.get("supports_streaming") or info.get("supports_streaming")
    )
    return {
        "tool_call": tool_call,
        # ... existing flags
        "streaming": streaming,  # ADD HERE
    }
```

**TypeScript** (`src/map.ts`):
```typescript
export function mapFlags(
  hub: AnyRecord,
  info: AnyRecord,
): Record<string, boolean> {
  // ... existing flags
  const streaming = Boolean(hub.supports_streaming || info.supports_streaming);
  return {
    tool_call: toolCall,
    // ... existing flags
    streaming: streaming,  // ADD HERE
  };
}
```

**Step 2**: Update build module (BOTH)

**Python** (`src/build.py`):
```python
def build_model_entry(...) -> dict[str, Any]:
    # ... existing code
    flags = map_flags(hub, info)
    for key, value in flags.items():
        if value:
            model[key] = value  # streaming flag auto-included if true
```

**TypeScript** (`src/build.ts`):
```typescript
export function buildModelEntry(...): AnyRecord {
  // ... existing code
  const flags = mapFlags(hub, info);
  for (const [key, value] of Object.entries(flags)) {
    if (value) {
      model[key] = value;  // streaming flag auto-included if true
    }
  }
}
```

**Step 3**: Update documentation
- `docs/opencode-litellm/plugin-fields.md` §2a (ModelConfig fields table)
- Add runtime effect to §6 if applicable

---

## Common Tasks

### Task: Verify Consistency Between Python and TypeScript

```bash
# 1. Run Python tool (requires LiteLLM endpoint)
cd tools/config-generator
python -m src.generate \
  --base-url https://litellm.example.com \
  --bearer YOUR_TOKEN \
  --output /tmp/python-output.jsonc

# 2. Check TypeScript plugin cached data
cat ~/.local/state/oclitellmac/providers/YOUR_PROVIDER_KEY.json | jq '.models'

# 3. Compare model configs (should be structurally identical)
# - Same model IDs
# - Same capability flags
# - Same cost/limit values
# - Same modality arrays
```

### Task: Add Support for New LiteLLM Field

**Example**: LiteLLM adds `supports_batch_api` field

1. **Check OpenCode schema compatibility**:
   ```bash
   # Search OpenCode source for batch-related fields
   cd repos/opencode
   git grep -i "batch" packages/opencode/src/config/provider.ts
   ```

2. **If field exists in OpenCode schema**:
   - Add to `map_flags()` (both implementations)
   - Field auto-included in build stage (existing logic handles it)

3. **If field doesn't exist in OpenCode schema**:
   - Document in `plugin-fields.md` as "no OpenCode equivalent"
   - Consider alternative mapping (e.g., store in `options` bag)

4. **Test with real LiteLLM endpoint**:
   ```bash
   curl -H "Authorization: Bearer TOKEN" \
     https://litellm.example.com/v1/model/info | jq '.[0].model_info'
   ```

### Task: Debug Category Misclassification

**Example**: `whisper-large-v3` classified as "chat" instead of "transcription"

1. **Check LiteLLM API response**:
   ```bash
   curl https://litellm.example.com/public/model_hub | jq '.[] | select(.model_group=="whisper-large-v3")'
   ```

2. **Check if `mode` field is set**:
   ```json
   {
     "model_group": "whisper-large-v3",
     "mode": "audio_transcription",  // Should map to "transcription"
     ...
   }
   ```

3. **If `mode` is missing/wrong**:
   - Add name heuristic to `categorize_model()` (BOTH implementations)
   - Example: `if "whisper" in name.lower(): return "transcription"`

4. **Verify fix**:
   ```bash
   # Python
   python -c "from src.categorize import categorize_model; print(categorize_model('whisper-large-v3', ''))"
   # Output: transcription
   ```

### Task: Update Blacklist Logic

**Example**: Always enable embedding models (don't blacklist)

1. **Remove from `NON_CHAT_CATEGORIES`** (BOTH):
   ```python
   NON_CHAT_CATEGORIES: frozenset[str] = frozenset({
       # "embedding",  # REMOVE THIS LINE
       "audio_speech",
       ...
   })
   ```

2. **Verify blacklist no longer includes embeddings**:
   ```bash
   python -m src.generate --base-url ... | grep -A5 '"blacklist"'
   # Should not list embedding models
   ```

---

## Testing Checklist

Before committing changes:

- [ ] **Python imports work**: `python -c "from src.generate import main"`
- [ ] **TypeScript type-checks**: `npx tsc --noEmit --skipLibCheck`
- [ ] **Python CLI help works**: `python -m src.generate --help`
- [ ] **Category detection is consistent** (same inputs → same outputs)
- [ ] **Field mapping is consistent** (same LiteLLM data → same ModelConfig)
- [ ] **Blacklist generation is consistent** (same categories → same blacklist)
- [ ] **Documentation updated** (`plugin-fields.md`, READMEs, config examples)

---

## Code Style Guidelines

### Python
- Use type hints: `def func(arg: str) -> dict[str, Any]:`
- Use `|` for union types: `str | None` (not `Optional[str]`)
- Use `frozenset` for immutable sets
- Use `_get_first()` helper for field priority logic
- Docstrings for all public functions

### TypeScript
- Use `const` for immutable bindings
- Use explicit return types: `function func(): ReturnType`
- Use `Record<string, any>` for flexible objects (alias as `AnyRecord`)
- Use `?.` for optional chaining: `hub.field ?? fallback`
- JSDoc comments for exported functions

### Naming Conventions
- **Files**: `snake_case.py`, `kebab-case.ts`
- **Functions**: `snake_case()` (Python), `camelCase()` (TypeScript)
- **Types**: `PascalCase` (both)
- **Constants**: `UPPER_SNAKE_CASE` (both)

---

## Debugging Tips

### Python: Print LiteLLM API responses
```python
# Add to src/fetch.py temporarily
import json
data = response.json()
print(json.dumps(data, indent=2))  # Inspect raw response
return data
```

### TypeScript: Enable detailed logging
```typescript
// Add to src/index.ts
log(`[DEBUG] Hub entries: ${JSON.stringify(hubEntries, null, 2)}`)
log(`[DEBUG] Categories: ${JSON.stringify(Object.fromEntries(categories), null, 2)}`)
```

### Check cached data (TypeScript plugin)
```bash
# Provider/model cache
cat ~/.local/state/oclitellmac/providers/PROVIDER_KEY.json | jq .

# Budget data
cat ~/.local/state/oclitellmac/key-info/PROVIDER_KEY.json | jq .
```

### Compare outputs
```bash
# Python tool output
python -m src.generate --base-url ... | jq '.provider.litellm.models.gpt-4'

# TypeScript plugin cache
jq '.models.gpt-4' ~/.local/state/oclitellmac/providers/PROVIDER_KEY.json

# Should be identical (modulo formatting)
```

---

## Error Messages Reference

### `ImportError: attempted relative import with no known parent package`
**Cause**: Running `python src/generate.py` instead of `python -m src.generate`  
**Fix**: Always use module invocation: `python -m src.generate`

### `ValidationError: Invalid discriminator value.`
**Cause**: Zod schema mismatch in `config.ts`  
**Fix**: Check `enabledCategories` array contains only valid category strings

### `TypeError: 'NoneType' object is not subscriptable`
**Cause**: LiteLLM endpoint returned unexpected response structure  
**Fix**: Add defensive checks in `fetch.py` / `fetch.ts`

### `Error: ENOENT: no such file or directory, open '~/.config/oclitellmac/server.json'`
**Cause**: Config file not created  
**Fix**: Create config file from `config-example.json`

---

## Common Pitfalls

### ❌ Modifying only one implementation
**Impact**: Python and TypeScript produce different model configs  
**Prevention**: Always update BOTH when changing category/mapping logic

### ❌ Forgetting to update CLI flags (Python)
**Impact**: New categories can't be enabled via command line  
**Prevention**: Check `main()` function when adding categories

### ❌ Forgetting to update config schema (TypeScript)
**Impact**: New categories fail Zod validation  
**Prevention**: Check `config.ts` `CategorySchema` enum

### ❌ Hardcoding field values
**Impact**: Loses flexibility for different LiteLLM configurations  
**Prevention**: Use `getFirst()` / `??` for field priority logic

### ❌ Not testing with real LiteLLM endpoint
**Impact**: Untested edge cases in production  
**Prevention**: Always test with actual LiteLLM proxy data

---

## Architecture Decision Log

### Why separate `transform.ts` and `render.py`?

**Reason**: Different output targets
- Python: JSONC string (file output)
- TypeScript: Runtime object mutation (config hook)

### Why use `Map` in TypeScript but `dict` in Python?

**Reason**: Idiomatic in each language
- Python: `dict` is built-in, fast, familiar
- TypeScript: `Map` preserves insertion order, better type safety

### Why omit false/empty values in `build_model_entry()`?

**Reason**: Keep configs minimal and readable
- User sees only relevant fields
- Reduces visual clutter in model picker
- OpenCode uses defaults for missing fields

### Why is `chat` never blacklisted?

**Reason**: OpenCode is primarily a code assistant tool
- Chat models are the core use case
- Non-chat models (embedding, TTS) add clutter
- Users can opt-in to non-chat categories if needed

---

## Future Maintenance

### When OpenCode updates its schema

1. **Check `repos/opencode/packages/opencode/src/config/provider.ts`**:
   ```bash
   cd repos/opencode
   git pull origin dev
   git diff HEAD~1 packages/opencode/src/config/provider.ts
   ```

2. **Update field mappings** if new fields added

3. **Update `docs/opencode-litellm/plugin-fields.md`** with new schema version

4. **Test both implementations** with new OpenCode version

### When LiteLLM updates its API

1. **Check LiteLLM changelog** for new fields/endpoints

2. **Update `fetch.py` / `fetch.ts`** if endpoints change

3. **Add new field mappings** if useful fields added

4. **Update documentation** with new API behavior

---

*Last updated: May 2026*  
*For questions: Check `docs/opencode-litellm/plugin-fields.md` (field reference) and `ARCHITECTURE.md` (design overview)*
