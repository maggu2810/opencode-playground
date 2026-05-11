# LiteLLM to OpenCode Config Generator

Generate `opencode.jsonc` configuration from a LiteLLM proxy's model endpoints.

## Features

- 🔍 **Model Discovery**: Fetches `/public/model_hub` (no auth) and `/v1/model/info` (auth required)
- 🗺️ **Field Mapping**: Maps LiteLLM fields to OpenCode provider/model format
- 🎯 **Smart Filtering**: Blacklists non-chat models by default (embedding, TTS, image gen, etc.)
- 🔧 **LiteLLM Compatibility**: Sets `litellmProxy: true` option for automatic `_noop` tool injection
- 📦 **Modular Architecture**: Shared pipeline with `oclitellmac-server` TypeScript plugin

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Basic (public models only)

```bash
python -m src.generate --base-url https://litellm.example.com
```

### With auth (full model details)

```bash
python -m src.generate \
  --base-url https://litellm.example.com \
  --bearer your-bearer-token \
  --output opencode.jsonc
```

### With custom provider name

```bash
python -m src.generate \
  --base-url https://litellm.example.com \
  --provider-name "My LiteLLM" \
  --provider-key "my-litellm" \
  --output opencode.jsonc
```

## Options

| Flag | Description | Default |
|------|-------------|---------|
| `--base-url` | LiteLLM proxy base URL (required) | - |
| `--bearer` | Bearer token for `/v1/model/info` endpoint | - |
| `--output` | Output file path | stdout |
| `--provider-name` | Display name in OpenCode UI | "LiteLLM" |
| `--provider-key` | Provider key in config | "litellm" |
| `--timeout` | Request timeout in seconds | 30 |

### Category Filtering (Non-Chat Models)

By default, non-chat models (embedding, TTS, image generation, etc.) are added to the provider's `blacklist` array to keep the model picker clean. Enable specific categories with these flags:

| Flag | Category | Examples |
|------|----------|----------|
| `--enable-embedding` | Text embedding models | `text-embedding-ada-002`, `text-embedding-3-large` |
| `--enable-audio-speech` | Text-to-speech (TTS) | `tts-1`, `tts-1-hd` |
| `--enable-transcription` | Speech-to-text (STT) | `whisper-1` |
| `--enable-image-generation` | Image generation | `dall-e-3`, `stable-diffusion-xl` |
| `--enable-video-generation` | Video generation | Model-specific |
| `--enable-ocr` | Document analysis / OCR | Model-specific |
| `--enable-ranking` | Reranking models | Model-specific |
| `--enable-all` | Enable all non-chat models | All of the above |

**Note**: Chat models are always enabled regardless of flags.

## Output Format

```jsonc
{
  "providers": {
    "litellm": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "LiteLLM",
      "options": {
        "baseURL": "https://litellm.example.com/v1",
        "apiKey": "",
        "litellmProxy": true
      },
      "models": {
        "gpt-4": {
          "id": "gpt-4",
          "name": "gpt-4",
          "capabilities": {...},
          "cost": {...},
          "limit": {...},
          "modalities": {...}
        }
      }
    }
  }
}
```

## Manual Configuration

After generating the config:

1. Add the output to your `opencode.jsonc` (merge into `providers` section)
2. Fill in the `apiKey` value or set it via environment variable
3. Run `opencode connect` to complete setup

## Requirements

- Python 3.10+
- httpx >= 0.25.0

## Architecture

The tool uses a modular pipeline architecture:

```
Fetch → Categorize → Map → Build → Filter → Render
```

Each stage is implemented as a separate module in `src/`:

- **`fetch.py`**: HTTP client for LiteLLM endpoints (`/public/model_hub`, `/v1/model/info`)
- **`categorize.py`**: Model category detection (chat, embedding, TTS, etc.)
- **`map.py`**: Field mapping (LiteLLM → OpenCode `ModelConfig`)
- **`build.py`**: Model entry construction
- **`filter.py`**: Blacklist generation for non-chat models
- **`render.py`**: JSONC output formatting
- **`generate.py`**: CLI and orchestration

This architecture is shared with the `oclitellmac-server` TypeScript plugin (see comparison below).

## Comparison: Python Tool vs TypeScript Plugin

| Aspect | config-generator (Python) | oclitellmac-server (TypeScript) |
|--------|---------------------------|--------------------------------|
| **Type** | Static config generator | Runtime plugin (config hook) |
| **Configuration** | CLI flags | `~/.config/oclitellmac/server.json` |
| **Output** | Writes `opencode.jsonc` file | Injects into OpenCode config at runtime |
| **Endpoints** | One per invocation | Multiple per plugin |
| **Caching** | None | Automatic with fallback |
| **Budget Tracking** | None | Continuous (60s polling + per-message) |
| **Restart Required** | No (manual re-run) | Yes (for config changes) |
| **Use Case** | One-time setup, version control | Multi-tenant, dynamic environments |

### When to Use the Python Tool

✅ **Use the Python tool when**:
- You want to version-control your OpenCode config
- You prefer explicit, reviewable configuration files
- You need to generate configs for multiple environments (CI/CD)
- You want to manually review/edit model configurations before use
- You're setting up OpenCode for the first time

### When to Use the TypeScript Plugin

✅ **Use the plugin when**:
- You manage multiple LiteLLM endpoints that change frequently
- You want automatic budget tracking and TUI display
- You prefer zero-config provider setup (no `opencode.json` editing)
- You need runtime fallback when endpoints are unreachable
- You want per-endpoint category filtering

### Can I Use Both?

Yes! They're complementary:
- Use the Python tool to generate initial configs for review
- Use the plugin for runtime providers that change frequently
- Both produce identical model configurations (shared pipeline logic)