# LiteLLM to OpenCode Config Generator

Generate `opencode.jsonc` configuration from a LiteLLM proxy's model endpoints.

## Features

- Fetches `/public/model_hub` (no auth required) for model discovery
- Fetches `/v1/model/info` (auth required) for detailed cost/limit information
- Maps LiteLLM fields to OpenCode provider/model format
- Sets `litellmProxy: true` option for OpenCode compatibility

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
| `--bearer` | Bearer token for authenticated endpoints | - |
| `--output` | Output file path | stdout |
| `--provider-name` | Display name in OpenCode UI | "LiteLLM" |
| `--provider-key` | Provider key in config | "litellm" |
| `--timeout` | Request timeout in seconds | 30 |

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